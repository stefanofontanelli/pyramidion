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


def setup_sqlalchemy(config, settings, base):
    config.set_request_property('pyramidion.create_sqla_session',
                                name="db_session",
                                reify=True)
    init_model(config, settings, base)


def create_sqla_session(request):
    """Create and return the request's SQLAlchemy session.
    """

    session = request.registry.scoped_session()

    def destroy_sqla_session(_):
        """ Callback handler for the "finished" request event """
        log.debug("Destroy SQLAlchemy session.")
        #session.remove()
        session.close()

    request.add_finished_callback(destroy_sqla_session)
    log.debug("Create SQLAlchemy session.")
    return session


def init_model(config, settings, base):
    """Set up SQLAlchemy models.
    """
    engine = engine_from_config(settings, prefix='sqlalchemy.')
    config.registry.db_engine = engine
    config.registry.scoped_session = scoped_session(sessionmaker(bind=engine))
    base.metadata.bind = engine
    base.metadata.create_all(engine)


def setup_routing(config, prefix, classes, adapterCls):

    for cls in classes:
        setattr(config.registry,
                '{}_adapter'.format(cls.__name__.lower()),
                setup_adapter(cls, config, prefix, adapterCls))


def setup_adapter(cls, config, prefix, adapterCls):
    adapter = adapterCls(cls=cls)
    adapter.setup_routing(config, prefix)
    return adapter


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


class EmberDataBase(crudalchemy.Base):

    def __init__(self, cls, session=None, db_session_key='db_session',
                 create_schema=None, read_schema=None,
                 update_schema=None, delete_schema=None):

        super(EmberDataBase, self).__init__(cls, session,
                                                   create_schema=create_schema,
                                                   read_schema=read_schema,
                                                   update_schema=update_schema,
                                                   delete_schema=delete_schema)

        self.db_session_key = db_session_key
        self.element = getattr(cls, '__singular__', cls.__name__).lower()
        self.collection = getattr(cls, '__plural__',
                                  self.element + 's').lower()

    def create(self, context, request):

        response = {}

        try:
            session = self.session or getattr(request, self.db_session_key)
            params = self.get_create_params(request)
            obj = super(EmberDataBase, self).create(session, **params)
            session.flush()
            response[self.element] = self.create_schema.dictify(obj)

        except colander.Invalid:
            log.exception('Bad request.')
            session.rollback()
            status = 400

        except IntegrityError:
            log.exception('Conflict.')
            session.rollback()
            status = 409

        except Exception:
            log.exception('Unknown error.')
            session.rollback()
            status = 500

        else:
            log.debug('Creation succeed.')
            status = 201
            session.commit()

        finally:
            request.response.status = status

        return response

    def get_create_params(self, request):
        params = request.json_body.get(self.element, {})
        r = self.create_schema.registry
        for key in r.attrs:
            if key in r.excludes or (r.includes and key not in r.includes):
                params.pop(key)

        return params

    def read(self, context, request):

        response = {}

        try:
            session = self.session or getattr(request, self.db_session_key)
            params = self.get_read_params(request)
            obj = super(EmberDataBase, self).read(session, **params)
            response[self.element] = self.read_schema.dictify(obj)

        except colander.Invalid:
            log.exception('Bad request.')
            session.rollback()
            status = 400

        except NoResultFound:
            log.exception('Not Found.')
            session.rollback()
            status = 404

        except Exception:
            log.exception('Unknown error.')
            session.rollback()
            status = 500

        else:
            log.debug('Read succeed.')
            status = 200
            session.commit()

        finally:
            request.response.status = status

        return response

    def get_read_params(self, request):
        return self.get_params(request, self.read_schema)

    def search(self, context, request):

        response = {}

        try:
            session = self.session or getattr(request, self.db_session_key)
            params = self.get_search_params(request)
            items = [self.read_schema.dictify(o)
                     for o in super(EmberDataBase, self).search(session, **params)]
            response[self.collection] = items

        except colander.Invalid:
            log.exception('Bad request.')
            session.rollback()
            status = 400

        except Exception:
            log.exception('Unknown error.')
            session.rollback()
            status = 500

        else:
            log.debug('Search succeed.')
            status = 200
            session.commit()

        finally:
            request.response.status = status

        return response

    def get_search_params(self, request):
        params = {}
        query = request.params.get('query')
        if not query is None:
            query = json.loads(query)
            criterions = query.get('criterions', [])
            params = {}
            params['criterions'] = tuple([getattr(getattr(self.cls,
                                                          c['attr']),
                                                  c['comparator'])(c['value'])
                                          for c in criterions])

            orderby = query.get('orderby', [])
            params['order_by'] = tuple([getattr(getattr(self.cls,
                                                       c['attr']),
                                               c['order'])()
                                       for c in orderby])

        return params

    def update(self, context, request):

        # NOTE: PKs update is not supported.
        # Subclass Base to add PKs update.

        response = {}

        try:
            session = self.session or getattr(request, self.db_session_key)
            params = self.get_update_params(request)
            obj = super(EmberDataBase, self).update(session, **params)
            session.flush()
            response[self.element] = self.update_schema.dictify(obj)

        except colander.Invalid:
            log.exception('Bad request.')
            session.rollback()
            status = 400

        except NoResultFound:
            log.exception('Not Found.')
            session.rollback()
            status = 404

        except Exception:
            log.exception('Unknown error.')
            session.rollback()
            status = 500

        else:
            log.debug('Update succeed.')
            status = 200
            session.commit()

        finally:
            request.response.status = status

        return response

    def get_update_params(self, request):
        params = request.json_body.get(self.element, {})
        log.debug('Params: %s' % params)
        r = self.update_schema.registry
        for key in r.attrs:
            if key in r.excludes or (r.includes and key not in r.includes):
                params.pop(key)
        log.debug('Params: %s' % params)
        return params

    def delete(self, context, request):

        response = {}

        try:
            session = self.session or getattr(request, self.db_session_key)
            params = self.get_delete_params(request)
            super(EmberDataBase, self).delete(session, **params)
            session.flush()

        except colander.Invalid:
            log.exception('Bad request.')
            session.rollback()
            status = 400

        except NoResultFound:
            log.exception('Not Found.')
            session.rollback()
            status = 404

        except Exception:
            log.exception('Unknown error.')
            session.rollback()
            status = 500

        else:
            log.debug('Delete succeed.')
            status = 204
            session.commit()

        finally:
            request.response.status = status

        return response

    def get_delete_params(self, request):
        return self.get_params(request, self.delete_schema)

    def get_params(self, request, schema):

        params = {}
        r = schema.registry
        for key in r.attrs:
            if key in r.excludes or\
              (r.includes and key not in r.includes) or\
              (key not in request.params and key not in request.matchdict):
                continue

            if key in r.collections:
                params[key] = request.params.getall(key)

            elif key in request.matchdict:
                params[key] = request.matchdict.get(key)

            elif key in request.params:
                params[key] = request.params.get(key)

        return params

    def setup_routing(self, config, prefix=''):

        route_name = '{}_create'.format(self.element)
        renderer = 'json'
        config.add_route(route_name,
                         '{}/{}'.format(prefix, self.collection),
                         request_method='POST')
        config.add_view(self.create, route_name=route_name, renderer=renderer)

        route_name = '{}_read'.format(self.element)
        config.add_route(route_name,
                         '{}/{}/{}'.format(prefix, self.collection, '{id}'),
                         request_method='GET')
        config.add_view(self.read, route_name=route_name, renderer=renderer)

        route_name = '{}_search'.format(self.collection)
        config.add_route(route_name,
                         '{}/{}'.format(prefix, self.collection),
                         request_method='GET')
        config.add_view(self.search, route_name=route_name, renderer=renderer)

        route_name = '{}_update'.format(self.element)
        config.add_route(route_name,
                         '{}/{}/{}'.format(prefix, self.collection, '{id}'),
                         request_method='PUT')
        config.add_view(self.update, route_name=route_name, renderer=renderer)

        route_name = '{}_delete'.format(self.element)
        config.add_route(route_name,
                         '{}/{}/{}'.format(prefix, self.collection, '{id}'),
                         request_method='DELETE')
        config.add_view(self.delete, route_name=route_name, renderer=renderer)

        """ FIXME
        PUT /accounts => 405 method not allowed
        accept-header: se diverso da application/json tornare 406 not acceptable
        """
