# tests.py
# Copyright (C) 2012 the Pyramidal authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidal and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from pyramid import testing
from pyramidal import Base as Handler
import logging
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.schema
import unittest


log = logging.getLogger(__name__)
Base = sqlalchemy.ext.declarative.declarative_base()


class Account(Base):
    __tablename__ = 'accounts'
    email = sqlalchemy.Column(sqlalchemy.Unicode(256), primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Unicode(128), nullable=False)
    surname = sqlalchemy.Column(sqlalchemy.Unicode(128), nullable=False)
    gender = sqlalchemy.Column(sqlalchemy.Enum(u'M', u'F'), nullable=True)
    contact = sqlalchemy.orm.relationship('Contact',
                                          uselist=False,
                                          back_populates='account')


class Contact(Base):
    __tablename__ = 'contacts'
    type_ = sqlalchemy.Column(sqlalchemy.Unicode(256), primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.Unicode(256), nullable=False)
    account_id = sqlalchemy.Column(sqlalchemy.Unicode(256),
    sqlalchemy.ForeignKey('accounts.email'),
    primary_key=True)
    account = sqlalchemy.orm.relationship('Account', back_populates='contact')


class TestsBase(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.engine = sqlalchemy.create_engine('sqlite://', echo=False)
        Base.metadata.bind = self.engine
        Base.metadata.create_all(self.engine)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.account = Handler(Account)
        self.contact = Handler(Account)

    def tearDown(self):
        testing.tearDown()
        self.session.close()

    def test_create_bad_request(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        response = self.account.create(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '400 Bad Request')

    def test_create_conflict(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        response = self.account.create(request.context, request)
        self.assertEqual(response,
                         dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname',
                              gender=None,
                              contact=None))
        self.assertEqual(request.response.status, '201 Created')
        response = self.account.create(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '409 Conflict')

    def test_update(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        old = self.account.create(request.context, request)
        request.params = dict(email='mailbox@domain.tld',
                              name='My New Name',
                              surname='My New Surname')
        new = self.account.update(request.context, request)
        self.assertNotEqual(old, new)
        self.assertEqual(new, dict(email='mailbox@domain.tld',
                                   name='My New Name',
                                   surname='My New Surname',
                                   gender=None,
                                   contact=None))
        self.assertEqual(request.response.status, '200 OK')

    def test_update_bad_request(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        self.account.create(request.context, request)
        request.params = dict(name='My Name',
                              surname='My Surname')
        response = self.account.update(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '400 Bad Request')

    def test_update_not_found(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        self.account.create(request.context, request)
        request.params = dict(email='no_mailbox@domain.tld',
                              name='My New Name',
                              surname='My New Surname')
        response = self.account.update(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '404 Not Found')

    def test_delete(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        response = self.account.create(request.context, request)
        request.params = dict(email='mailbox@domain.tld')
        response = self.account.delete(request.context, request)
        self.assertEqual(response, request.params)
        self.assertEqual(request.response.status, '200 OK')

    def test_delete_bad_request(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        response = self.account.create(request.context, request)
        request.params = dict(name='My Name')
        response = self.account.delete(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '400 Bad Request')

    def test_delete_not_found(self):
        request = testing.DummyRequest()
        request.context = testing.DummyResource()
        request.sqla_session = self.session
        request.params = dict(email='mailbox@domain.tld',
                              name='My Name',
                              surname='My Surname')
        response = self.account.create(request.context, request)
        request.params = dict(email='mailbox2@domain.tld')
        response = self.account.delete(request.context, request)
        self.assertEqual(response, {})
        self.assertEqual(request.response.status, '404 Not Found')
