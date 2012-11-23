# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is released under the MIT License
# http://www.opensource.org/licenses/mit-license.php

from .form import SQLAlchemySimpleSearchForm
from .widget import (Paginator,
                     SearchResult)
from collections import OrderedDict
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
            response = self.get_new_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            raise e
            response = self.get_new_500_response(context, request, e)

        finally:
            return response

    def get_new_response(self, context, request):
        return {'form': self.get_create_form(context, request).render()}

    def get_new_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def create(self, context, request):
        try:
            request.response.status = 201
            response = self.get_create_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_create_500_response(context, request, e)

        return response

    def get_create_response(self, context, request):

        try:
            params = self.get_create_params(context, request)

        except ValidationFailure as e:
            log.exception('Bad request.')
            request.response.status = 400
            response = self.get_create_400_response(context, request, e)

        else:
            try:
                obj = self.do_create(context, request, **params)

            except IntegrityError as e:
                log.exception('Conflict.')
                request.response.status = 409
                response = self.get_create_409_response(context, request, e)

            except Exception as e:
                log.exception('Unknown error.')
                request.response.status = 500
                response = self.get_create_500_response(context, request, e)

            else:
                request.response.status = 201
                pks = {p.key: getattr(obj, p.key)
                       for p in self.inspector.column_attrs
                       if p.columns[0] in self.inspector.primary_key}
                form = self.get_edit_form(context, request, **pks)
                response = {'form': form.render(params)}

        return response

    def get_create_400_response(self, context, request, exc):
        return {'form': exc.render()}

    def get_create_409_response(self, context, request, exc):
        form = self.get_create_form(context, request)
        values = self.get_create_params(context, request)
        return {'form': form.render(values), 'error': str(exc)}

    def get_create_500_response(self, context, request, exc):
        form = self.get_create_form(context, request)
        values = self.get_create_params(context, request)
        return {'form': form.render(values), 'error': str(exc)}

    def get_create_params(self, context, request):
        params = request.POST.items()
        form = self.get_create_form(context, request)
        return {name: value
                for name, value in form.validate(params).items()
                if not value is colander.null}

    def get_create_form(self, context, request):
        route_name = self.routes['create']
        action = request.route_url(route_name)
        save = Button(name='submit',
                      title='Save',
                      type='submit',
                      value='submit')
        style = 'form-horizontal'
        form = SQLAlchemyForm(self.cls,
                              action=action,
                              formid=route_name,
                              buttons=(save,),
                              bootstrap_form_style=style)
        session = self.session or getattr(request, self.db_session_key)
        form.populate_widgets(session)
        return form

    def do_create(self, context, request, **kwargs):
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
            response = self.get_read_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_read_500_response(context, request, e)

        finally:
            return response

    def get_read_response(self, context, request):
        try:
            params = self.get_read_params(context, request)
            obj = self.do_read(context, request, **params)

        except KeyError as e:
            log.exception('Bad request.')
            request.response.status = 400
            return self.get_read_400_response(context, request, e)

        except NoResultFound as e:
            log.exception('No result found.')
            request.response.status = 404
            return self.get_read_404_response(context, request, e)

        else:
            form = self.get_edit_form(context, request, **params)
            values = form.schema.dictify(obj)
            response = {'form': form.render(values)}

        return response

    def get_read_400_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_read_404_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_read_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_read_params(self, context, request):
        return request.matchdict

    def do_read(self, context, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        return self.cls.read(session=session, **kwargs)

    def edit(self, context, request):
        try:
            response = self.get_edit_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_edit_500_response(context, request, e)

        finally:
            return response

    def get_edit_response(self, context, request):
        params = self.get_edit_params(context, request)
        try:
            obj = self.do_edit(context, request, **params)

        except KeyError as e:
            log.exception('Bad request.')
            request.response.status = 400
            return self.get_edit_400_response(context, request, e)

        except NoResultFound as e:
            log.exception('No result found.')
            request.response.status = 404
            return self.get_edit_404_response(context, request, e)

        else:
            form = self.get_update_form(request, **params)
            values = form.schema.dictify(obj)
            response = {'form': form.render(values)}

        return response

    def get_edit_400_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_edit_404_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_edit_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_edit_params(self, context, request):
        return request.matchdict

    def get_edit_form(self, context, request, **pks):
        route_name = self.routes['edit']
        edit = Button(name='submit',
                      title='Edit',
                      type='submit',
                      value='submit')
        action = request.route_url(route_name, **pks)
        form = SQLAlchemyForm(self.cls,
                              action=action,
                              formid=route_name,
                              buttons=(edit,),
                              readonly=True,
                              bootstrap_form_style='form-horizontal')
        session = self.session or getattr(request, self.db_session_key)
        form.populate_widgets(session)
        return form

    def do_edit(self, context, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        return self.cls.read(session=session, **kwargs)

    def update(self, context, request):
        try:
            response = self.get_update_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_update_500_response(context, request, e)

        finally:
            return response

    def get_update_response(self, context, request):
        pks, values = self.get_update_params(context, request)
        try:
            obj = self.do_update(context, request, pks, **values)

        except ValidationFailure as e:
            log.exception('Bad request.')
            request.response.status = 400
            response = self.get_update_400_response(context, request, e)

        except NoResultFound:
            log.exception('No result found.')
            request.response.status = 404
            response = self.get_update_404_response(context, request, e)

        else:
            # Build pks again to get right values from obj:
            # update can be changed them.
            pks = {p.key: getattr(obj, p.key)
                   for p in self.inspector.column_attrs
                   if p.columns[0] in self.inspector.primary_key}
            form = self.get_update_form(request, **pks)
            values = form.schema.dictify(obj)
            response = {'form': form.render(values)}

        return response

    def get_update_400_response(self, context, request, exc):
        return {'form': exc.render(), 'error': str(exc)}

    def get_update_404_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_update_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_update_params(self, context, request):
        pks = request.matchdict
        params = request.POST.items()
        form = self.get_update_form(request, **pks)
        values = form.validate(params)
        return pks, values

    def get_update_form(self, request, **pks):
        route_name = self.routes['update']
        save = Button(name='submit',
                      title='Save',
                      type='submit',
                      value='submit')
        form = SQLAlchemyForm(self.cls,
                              action=request.route_url(route_name, **pks),
                              formid=route_name,
                              buttons=(save,),
                              readonly=True,
                              bootstrap_form_style='form-horizontal')
        session = self.session or getattr(request, self.db_session_key)
        form.populate_widgets(session)
        return form

    def do_update(self, context, request, pks, **values):
        session = self.session or getattr(request, self.db_session_key)
        try:
            obj = self.cls.update(session, pks, **values)

        except Exception as e:
            log.exception('Error during update')
            session.rollback()
            raise e

        else:
            session.commit()

        return obj

    def remove(self, context, request):
        try:
            params = request.matchdict
            obj = self.read_obj(request, **params)
            form = self.get_remove_form(request, **params)
            values = form.schema.dictify(obj)

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

    def remove(self, context, request):
        try:
            response = self.get_remove_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_remove_500_response(context, request, e)

        finally:
            return response

    def get_remove_response(self, context, request):
        try:
            params = self.get_remove_params(context, request)
            obj = self.do_remove(context, request, **params)

        except KeyError as e:
            log.exception('Bad request.')
            request.response.status = 400
            return self.get_remove_400_response(context, request, e)

        except NoResultFound as e:
            log.exception('No result found.')
            request.response.status = 404
            return self.get_remove_404_response(context, request, e)

        else:
            form = self.get_delete_form(request, **params)
            values = form.schema.dictify(obj)
            response = {'form': form.render(values)}

        return response

    def get_remove_400_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_remove_404_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_remove_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_remove_params(self, context, request):
        return request.matchdict

    def do_remove(self, context, request, **kwargs):
        session = self.session or getattr(request, self.db_session_key)
        return self.cls.read(session=session, **kwargs)

    def delete(self, context, request):
        try:
            response = self.get_delete_response(context, request)

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_delete_500_response(context, request, e)

        finally:
            return response

    def get_delete_response(self, context, request):
        try:
            pks = self.get_delete_params(context, request)
            obj = self.do_delete(context, request, **pks)

        except KeyError as e:
            log.exception('Bad request.')
            request.response.status = 400
            response = self.get_delete_400_response(context, request, e)

        except NoResultFound:
            log.exception('No result found.')
            request.response.status = 404
            response = self.get_delete_404_response(context, request, e)

        else:
            response = {}

        return response

    def get_delete_400_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_delete_404_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_delete_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_delete_params(self, context, request):
        return request.matchdict

    def get_delete_form(self, request, **pks):
        route_name = self.routes['delete']
        btn = Button(name='submit',
                     title='Delete',
                     type='submit',
                     value='submit')
        form = SQLAlchemyForm(self.cls,
                              action=request.route_url(route_name, **pks),
                              formid=route_name,
                              buttons=(btn,),
                              readonly=True,
                              bootstrap_form_style='form-horizontal')
        session = self.session or getattr(request, self.db_session_key)
        form.populate_widgets(session)
        return form

    def do_delete(self, context, request, **pks):
        session = self.session or getattr(request, self.db_session_key)
        try:
            self.cls.delete(session, **pks)

        except Exception as e:
            log.exception('Error during delete')
            session.rollback()
            raise e

        else:
            session.commit()

        return None

    def search(self, context, request):
        response = self.get_search_response(context, request)
        try:
            pass

        except Exception as e:
            log.exception('Unknown error.')
            request.response.status = 500
            response = self.get_search_500_response(context, request, e)

        finally:
            return response

    def get_search_response(self, context, request):
        try:
            params = self.get_search_params(request)
            values = self.validate_search_params(request, params)
            result = self.do_search(context, request, **values)

        except ValidationFailure as e:
            log.exception('Bad request.')
            request.response.status = 400
            response = self.get_search_400_response(context, request, e)

        else:
            form = self.get_search_form(request)
            response = {'form': form.render(values),
                        'result': result}

        return response

    def get_search_400_response(self, context, request, exc):
        return {'form': exc.render(), 'error': str(exc)}

    def get_search_500_response(self, context, request, exc):
        return {'form': None, 'error': str(exc)}

    def get_search_params(self, request):
        return request.params.items()

    def validate_search_params(self, request, params):
        form = self.get_search_form(request)
        return {name: value
                for name, value in form.validate(params).items()
                if not value is colander.null}

    def get_search_form(self, request):
        route_name = self.routes['search']
        action = request.route_url(route_name)
        btn = Button(name='submit',
                     title='Search',
                     type='submit',
                     value='submit')
        form = SQLAlchemySimpleSearchForm(self.cls,
                                          action=action,
                                          buttons=(btn,),
                                          formid=route_name,
                                          bootstrap_form_style='form-inline')
        session = self.session or getattr(request, self.db_session_key)
        form.populate_widgets(session)
        return form

    def do_search(self, context, request, **kwargs):
        start = kwargs.pop('start', 0)
        limit = kwargs.pop('limit', 25)
        order_by = kwargs.pop('order_by', None)
        direction = kwargs.pop('direction', 'asc')
        intersect = kwargs.pop('intersect', True)

        if order_by:
            order_by = [getattr(getattr(self.cls, order_by),
                                direction)()]

        criterions = []
        for prop in self.inspector.attrs:
            name = prop.key
            attr_criterion = kwargs.pop('{}_criterion'.format(name), None)
            if not attr_criterion:
                continue

            value = attr_criterion[name]
            if value == colander.null:
                continue

            comparator = attr_criterion['comparator']
            print name, comparator, value
            criterion = getattr(getattr(self.cls, name), comparator)(value)
            criterions.append(criterion)

        session = self.session or getattr(request, self.db_session_key)
        items = self.cls.search(session,
                                *criterions,
                                order_by=order_by,
                                start=start,
                                limit=limit,
                                intersect=intersect)
        cols = self.get_search_columns()
        total = self.cls.search(session,
                                *criterions,
                                raw_query=True).count()
        paginator = Paginator(total=total, start=start, limit=limit)
        return SearchResult(results=items,
                            cols=cols,
                            paginator=paginator)

    def get_search_columns(self):
        col = OrderedDict()
        for p in self.inspector.attrs:
            col[p.key] = p.key

        return col

    def setup_routing(self, config, prefix=''):

        for action in self.routes:
            resource = self.cls.__name__.lower()
            path = '{}/{}/{}'.format(prefix, resource, action)
            if action in ('read', 'edit', 'update', 'remove', 'delete'):
                pks = ['{' + p.key + '}'
                       for p in self.inspector.column_attrs
                       if p.columns[0] in self.inspector.primary_key]
                path = '{}/{}'.format(path, '/'.join(pks))

            config.add_route(self.routes[action], path)

            tpl = '/{}.mako'.format(action)
            config.add_view(getattr(self, action),
                            route_name=self.routes[action],
                            renderer=tpl,
                            permission=action)
