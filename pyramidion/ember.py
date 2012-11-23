

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
