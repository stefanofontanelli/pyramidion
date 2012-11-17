# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is released under the MIT License
# http://www.opensource.org/licenses/mit-license.php

from deform import (Button,
                    ValidationFailure)
from deformalchemy import SQLAlchemyForm
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError 
from sqlalchemy.orm.exc import NoResultFound
import colander
import logging

log = logging.getLogger(__file__)


class DeformBase(object):

    methods = ['new', 'create', 'edit', 'update',
               'remove', 'delete', 'read', 'search']

    def __init__(self, cls, session=None, db_session_key='db_session'):
        self.cls = cls
        self.session = session
        self.db_session_key = db_session_key
        self.routes = {key: '{}_{}'.format(cls.__name__.lower(), key)
                       for key in self.methods}
        self.inspector = inspect(cls)

    def new(self, context, request):
        try:
            form = self.get_new_form(request).render()

        except Exception:
            log.exception('Unknown error.')
            status = 500
            form = ''

        else:
            status = 200

        request.response.status = status
        return {'status': status, 'form': form}

    def get_new_form(self, request):
        route_name = self.routes['create']
        save = Button(name='submit',
                      title='Save',
                      type='submit',
                      value='submit')
        return SQLAlchemyForm(self.cls,
                              action=request.route_url(route_name),
                              formid=route_name,
                              buttons=(save,),
                              bootstrap_form_style='form-horizontal')

    def create(self, context, request):
        try:
            params = self.get_create_params(request)
            form = self.get_new_form(request)
            values = {name: value
                      for name, value in form.validate(params).items()
                      if not value is colander.null}
            obj = self.create_obj(request, **values)

        except ValidationFailure as e:
            log.exception('Bad request.')
            status = 400
            form = e.render()

        except IntegrityError:
            log.exception('Conflict.')
            status = 409
            form = form.render(values)

        except Exception:
            log.exception('Unknown error.')
            status = 500
            form = form.render(values)

        else:
            status = 201
            pks = {p.key: getattr(obj, p.key)
                   for p in self.inspector.column_attrs
                   if p.columns[0] in self.inspector.primary_key}
            raise HTTPFound(location=request.route_url(self.routes['read'], **pks))

        request.response.status = status
        return {'status': status, 'form': form}

    def get_create_params(self, request):
        return request.POST.items()

    def create_obj(self, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        try:
            obj = self.cls.create(session=session, **kwargs)

        except Exception as e:
            log.exception('Error during create')
            session.rollback()
            raise e

        else:
            session.commit()

        return obj

    def read(self, context, request):
        try:
            params = self.get_read_params(request)
            obj = self.read_obj(request, **params)
            form = self.get_read_form(request, **params)
            values = form.dictify(obj)

        except NoResultFound as e:
            log.exception('No result found.')
            status = 404
            form = ''

        except Exception:
            log.exception('Unknown error.')
            status = 500
            form = ''

        else:
            status = 200
            form = form.render(values)

        request.response.status = status
        return {'status': status, 'form': form}

    def get_read_params(self, request):
        return request.matchdict

    def get_read_form(self, request, **pks):
        route_name = self.routes['edit']
        edit = Button(name='submit',
                      title='Edit',
                      type='submit',
                      value='submit')
        action = request.route_url(route_name, **pks)
        return SQLAlchemyForm(self.cls,
                              action=action,
                              method='POST',
                              formid=route_name,
                              buttons=(edit,),
                              readonly=True,
                              bootstrap_form_style='form-horizontal')

    def read_obj(self, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        return self.cls.read(session=session, **kwargs)

    def edit(self, context, request):
        try:
            params = self.get_edit_params(request)
            obj = self.read_obj(request, **params)
            form = self.get_edit_form(request, **params)
            values = form.dictify(obj)

        except NoResultFound as e:
            log.exception('No result found.')
            status = 404
            form = ''

        except Exception:
            log.exception('Unknown error.')
            status = 500
            form = ''

        else:
            status = 200
            form = form.render(values)

        request.response.status = status
        return {'status': status, 'form': form}

    def get_edit_params(self, request):
        return request.matchdict

    def get_edit_form(self, request, **pks):
        route_name = self.routes['update']
        save = Button(name='submit',
                      title='Save',
                      type='submit',
                      value='submit')
        return SQLAlchemyForm(self.cls,
                              action=request.route_url(route_name, **pks),
                              formid=route_name,
                              buttons=(save,),
                              readonly=True,
                              bootstrap_form_style='form-horizontal')

    def update(self, context, request):
        try:
            pks, params = self.get_update_params(request)
            form = self.get_edit_form(request, **pks)
            values = form.validate(params)
            obj = self.update_obj(request, pks, **values)

        except ValidationFailure as e:
            log.exception('Bad request.')
            status = 400
            form = e.render()

        except NoResultFound:
            log.exception('No result found.')
            status = 404
            form = ''

        except Exception:
            log.exception('Unknown error.')
            status = 500
            form = ''

        else:
            status = 200
            pks = {p.key: getattr(obj, p.key)
                   for p in self.inspector.column_attrs
                   if p.columns[0] in self.inspector.primary_key}
            raise HTTPFound(location=request.route_url(self.routes['read'], **pks))

        request.response.status = status
        return {'status': status, 'form': form}

    def get_update_params(self, request):
        return request.matchdict, request.POST.items()

    def update_obj(self, request, pkeys, **values):
        session = self.session or getattr(request, self.db_session_key)
        try:
            obj = self.cls.update(session, pkeys, **values)

        except Exception as e:
            log.exception('Error during create')
            session.rollback()
            raise e

        else:
            session.commit()

        return obj

    def remove(self, context, request):
        pass

    def delete(self, context, request):

        response = {}

        try:
            if 'submit' in request.POST:
                self.delete_obj(request, **self.get_read_params(request))
                values = colander.null

            else:
                obj = self.read_obj(request, **self.get_read_params(request))
                values = self.delete_form.dictify(obj)

        except ValidationFailure as e:
            log.exception('Bad request.')
            status = 400
            error = e
            values = colander.null

        except NoResultFound:
            log.exception('No result found.')
            status = 404
            error = e
            values = colander.null

        except Exception:
            log.exception('Unknown error.')
            status = 500
            error = e
            values = colander.null

        else:
            status = 200
            error =  None

        finally:
            request.response.status = status
            response['status'] = status
            response['error'] = error
            response['values'] = values
            response['form'] = self.update_form

        return response

    def delete_form(self):
        return self.get_default_form(action='delete',
                                     title='Delete')

    def delete_obj(self, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        return self.cls.delete(session=session, **kwargs)

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

    def setup_routing(self, config, prefix=''):

        for action in self.routes:
            resource = self.cls.__name__.lower()
            path = '{}/{}/{}'.format(prefix, resource, action)
            if action in ('read', 'edit', 'update', 'remove', 'delete'):
                pks = ['{' + p.key + '}'
                       for p in self.inspector.column_attrs
                       if p.columns[0] in self.inspector.primary_key]
                path = '{}/{}'.format(path, '/'.join(pks))

            print action, path

            config.add_route(self.routes[action], path)

            tpl = '/{}.mako'.format(action)
            config.add_view(getattr(self, action),
                            route_name=self.routes[action],
                            renderer=tpl,
                            permission=action)
