# __init__.py
# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidion and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from .widget import SQLAChosenSingleWidget
from .widget import Paginator
from colanderalchemy import SQLAlchemyMapping
from deform import Button
from deform import Form
from deform import ValidationFailure
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
import colander
import crudalchemy
import json
import logging
import math


log = logging.getLogger(__file__)


class DeformBase(crudalchemy.Base):

    def __init__(self, cls, session=None,
                 db_session_key='db_session',
                 create_schema=None, read_schema=None,
                 update_schema=None, delete_schema=None,
                 search_schema=None, export_schema=None):

        super(DeformBase, self).__init__(cls, session,
                                         create_schema=create_schema,
                                         read_schema=read_schema,
                                         update_schema=update_schema,
                                         delete_schema=delete_schema)

        if search_schema is None:
            search_schema = SQLAlchemyMapping(cls)
            for node in search_schema:
                node.missing = colander.null

        self.search_schema = search_schema

        if export_schema is None:
            excludes = {}
            for name in self.mapping_registry.attrs:
                if name in self.mapping_registry.relationships:
                    excludes[name] = True
                else:
                    excludes[name] = False
            export_schema = SQLAlchemyMapping(cls, excludes=excludes)

        self.export_schema = export_schema

        self.db_session_key = db_session_key
        self.routes = {action: '{}_{}'.format(self.cls.__name__.lower(),
                                              action)
                       for action in ['create',
                                      'read',
                                      'update',
                                      'delete',
                                      'search']}

    def create(self, context, request,
               success_message=None, success_queue='',
               error_message=None, error_queue='',
               error_exception_tb=False):

        form = Form(self.create_schema,
                    action=request.route_url(self.routes['create']),
                    buttons=(Button(name='submit',
                                    title='Save',
                                    type='submit',
                                    value='submit'),),
                    bootstrap_form_style='form-horizontal',
                    formid=self.routes['create'])

        if 'submit' in request.POST:

            controls = request.POST.items()
            session = self.session or getattr(request, self.db_session_key)

            try:
                values = {name: value
                          for name, value in form.validate(controls).items()
                          if not value is None}
                obj = super(DeformBase, self).create(session=session,
                                                     validate=False,
                                                     **values)
                session.commit()

            except ValidationFailure as e:
                session.rollback()
                values = colander.null
                error = e

            except Exception as e:
                log.exception('Error during create')
                session.rollback()
                error = None
                if error_message:
                    m = error_message if not error_exception_tb \
                                      else "{}: {}".format(error_message, e)
                    request.session.flash(m, error_queue)

            else:
                if success_message:
                    request.session.flash(success_message, success_queue)

                location = request.route_url(self.routes['search'])
                raise HTTPFound(location=location)

        else:
            values = colander.null
            error = None

        return {'form': form, 'error': error, 'values': values}

    def read(self, context, request):
        form = Form(self.read_schema,
                    action=request.route_url(self.routes['update'],
                                             **request.matchdict),
                    buttons=(Button(name='edit',
                                    title='Edit',
                                    type='submit',
                                    value='edit'),),
                    bootstrap_form_style='form-horizontal',
                    formid=self.routes['read'])
        session = self.session or getattr(request, self.db_session_key)
        obj = super(DeformBase, self).read(session=session, **request.matchdict)
        values = self.read_schema.dictify(obj)
        return {'form': form, 'values': values}

    def update(self, context, request,
               success_message=None, success_queue='',
               error_message=None, error_queue='',
               error_exception_tb=False):

        params = {name : request.matchdict[name]
                  for name in self.mapping_registry.pkeys}

        session = self.session or getattr(request, self.db_session_key)

        for node in self.update_schema:
            try:
                node.widget.populate(session)

            except AttributeError:
                continue

        form = Form(self.update_schema,
                    action=request.route_url(self.routes['update'], **params),
                    buttons=(Button(name='submit',
                                    title='Save',
                                    type='submit',
                                    value='submit'),),
                    bootstrap_form_style='form-horizontal',
                    formid=self.routes['update'])

        if 'submit' in request.POST:

            controls = request.POST.items()

            try:
                values = {name: value
                          for name, value in form.validate(controls).items()
                          if not value is None}
                obj = super(DeformBase, self).update(session=session,
                                                     validate=False,
                                                     **values)
                session.commit()

            except ValidationFailure, e:
                session.rollback()
                values = colander.null
                error = e

            except Exception as e:
                log.exception('Error during updating')
                session.rollback()
                error = None
                if error_message:
                    m = error_message if not error_exception_tb \
                                      else "{}: {}".format(error_message, e)
                    request.session.flash(m, error_queue)

            else:
                location = request.route_url(self.routes['search'])
                if success_message:
                    request.session.flash(success_message, success_queue)

                raise HTTPFound(location=location)

        else:
            obj = super(DeformBase, self).read(session=session, **params)
            values = {name: value
                      for name, value in self.update_schema.dictify(obj).items()
                      if not value is None}
            error = None

        return {'form': form, 'error': error, 'values': values}

    def delete(self, context, request,
               success_message=None, error_message=None,
               success_queue='', error_queue='',
               error_exception_tb=False):

        params = {name : request.matchdict[name]
                  for name in self.mapping_registry.pkeys}
        form = Form(self.read_schema,
                    action=request.route_url(self.routes['delete'], **params),
                    buttons=(Button(name='submit',
                                    title='Save',
                                    type='submit',
                                    value='submit'),),
                    bootstrap_form_style='form-horizontal',
                    formid=self.routes['delete'])

        session = self.session or getattr(request, self.db_session_key)

        if 'submit' in request.POST:
            try:
                super(DeformBase, self).delete(session=session, **params)
                session.commit()

            except:
                log.exception('Error during delete')
                session.rollback()
                if error_message:
                    m = error_message if not error_exception_tb \
                                      else "{}: {}".format(error_message, e)
                    request.session.flash(m, error_queue)

            else:
                if success_message:
                    request.session.flash(success_message, success_queue)

            finally:
                location = request.route_url(self.routes['search'])
                raise HTTPFound(location=location)

        else:
            obj = super(DeformBase, self).read(session=session, **params)
            values = self.read_schema.dictify(obj)
            error = None

        return {'form': form, 'error': error, 'values': values}

    def search(self, context, request):

        session = self.session or getattr(request, self.db_session_key)

        for node in self.search_schema:
            try:
                node.widget.populate(session)

            except AttributeError:
                continue

        form = Form(self.search_schema,
                    action=request.route_url(self.routes['search']),
                    method='POST',
                    buttons=(Button(name='submit',
                                    title='Search',
                                    type='submit',
                                    value='submit'),),
                    bootstrap_form_style='form-inline')

        if 'start' in request.GET:
            start = int(request.GET['start'])

        else:
            start = 0

        if 'limit' in request.GET:
            limit = int(request.GET['limit'])

        else:
            limit = 25

        if 'submit' in request.POST:

            controls = request.POST.items()

            try:
                values = form.validate(controls)
                error = None

            except ValidationFailure, e:
                form = None
                values = colander.null
                error = e

        else:
            values = colander.null
            error = None

        if values is colander.null:
            criterions = None
        else:
            criterions = self.get_search_criterions(values)

        order_by = None

        total = super(DeformBase, self).search(session=session,
                                               criterions=criterions,
                                               raw_query=True).count()
        items = super(DeformBase, self).search(session=session,
                                               criterions=criterions,
                                               order_by=order_by,
                                               start=start,
                                               limit=limit)
        paginator = Paginator(total=total, start=start, limit=limit)
        return {
            'form': form,
            'values': values,
            'items': items,
            'error': error,
            'routes': self.routes,
            'paginator': paginator
        }

    def get_search_criterions(self, values):

        criterions = []
        for attr in values:

            if attr not in self.search_schema:
                continue

            value = values[attr]
            if not value:
                continue

            if isinstance(self.search_schema[attr].typ, colander.DateTime):
                start = datetime(value.year, value.month, value.day, 0, 0, 0)
                end = datetime(value.year, value.month, value.day,
                               59, 59, 59, 999999)
                criterion = getattr(self.cls, attr).between(start, end)

            elif isinstance(self.search_schema[attr].typ, colander.String):
                criterion = getattr(self.cls, attr).ilike(value)

            else:
                criterion = getattr(self.cls, attr) == value

            criterions.append(criterion)

        return criterions

    def export(self, context, request):
        session = self.session or getattr(request, self.db_session_key)
        criterions = self.get_search_criterions(request.params)
        items = crudalchemy.Base.search(self,
                                        session=session,
                                        criterions=criterions)
        return {'items': items}

    def setup_routing(self, config, prefix=''):

        for action in self.routes:

            resource = self.cls.__name__.lower()
            path = '{}/{}/{}'.format(prefix, resource, action)
            if action in set(['read', 'update', 'delete']):
                pkeys = '/'.join(['{%s}' % name
                                  for name in self.mapping_registry.pkeys])
                path = '{}/{}'.format(path, pkeys)

            config.add_route(self.routes[action], path)

            tpl = '/{}/{}.mako'.format(resource, action)
            config.add_view(getattr(self, action),
                            route_name=self.routes[action],
                            renderer=tpl,
                            permission=action)