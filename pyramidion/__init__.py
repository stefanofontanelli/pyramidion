# __init__.py
# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidion and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from colanderalchemy import SQLAlchemyMapping
from deform import Button
from deform import Form
from deform import ValidationFailure
from pyramid.httpexceptions import HTTPTemporaryRedirect
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
import colander
import crudalchemy
import logging


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
                 update_schema=None, delete_schema=None, search_schema=None):

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
        self.db_session_key = db_session_key
        self.routes = {action: '{}_{}'.format(self.cls.__name__.lower(),
                                              action)
                       for action in ['create',
                                      'read',
                                      'update',
                                      'delete',
                                      'search']}

    def create(self, context, request):
        return {}

    def read(self, context, request):
        pass

    def update(self, context, request):
        pass

    def delete(self, context, request):
        pass

    def search(self, context, request):

        form = Form(self.search_schema,
                    action=request.route_url(self.routes['search']),
                    buttons=(Button(name='submit',
                                    title='Search',
                                    type='submit',
                                    value='submit'),),
                    bootstrap_form_style='form-inline')

        if 'submit' in request.POST:  # detect that the submit button was clicked

            controls = request.POST.items()  # get the form controls

            try:
                appstruct = form.validate(controls)  # call validate
            except ValidationFailure, e:  # catch the exception
                return {'form': e.render()}  # re-render the form with an exception

            # the form submission succeeded, we have the data
            return {'form': form, 'values': appstruct}

        return {'form': form, 'values': colander.null}

    def setup_routing(self, config, prefix=''):

        for action in self.routes:

            resource = self.cls.__name__.lower()
            tpl = '/{}/{}.mako'.format(resource, action)
            config.add_route(self.routes[action],
                             '{}/{}/{}'.format(prefix, resource, action))
            config.add_view(getattr(self, action),
                            route_name=self.routes[action],
                            renderer=tpl)
