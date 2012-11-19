# Copyright (C) 2012 the DeformAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is released under the MIT License
# http://www.opensource.org/licenses/mit-license.php

from colander import (Mapping,
                      SchemaNode)
from deformalchemy import SQLAlchemyForm
from sqlalchemy import (Date,
                        DateTime,
                        Float,
                        Integer,
                        Numeric,
                        String,
                        Time)


class SQLAlchemySearchForm(SQLAlchemyForm):

    def __init__(self, class_, includes=None, excludes=None, overrides=None, **kw):
        self.class_ = class_
        self.bootstrap = 'bootstrap_form_style' in kw
        schema = SQLAlchemySchemaNode(class_,
                                      includes=includes,
                                      excludes=excludes,
                                      overrides=overrides)
        search_schema = SchemaNode(Mapping())
        self.inspector = inspect(class_)
        for prop in self.inspector.attrs:

            name = prop.key
            if name not in schema:
                continue

            node = SchemaNode(Sequence(),
                              name=name,
                              title=schema[name].title)

            try:
                getattr(self.inspector.column_attrs, name)
                factory = 'get_widget_from_column'
                comparator_factory = 'get_comparator_from_column'

            except AttributeError:
                getattr(self.inspector.relationships, name)
                factory = 'get_widget_from_relationship'
                comparator_factory = 'get_comparator_from_relationship'

            if schema[name].widget is None:
                schema[name].widget = getattr(self, factory)(prop)

            node.add(schema[name])
            schema[name].title = 'Value'
            schema[name].name = 'value'
            comparator = getattr(self, comparator_factory)(prop)
            node.add(comparator)
            search_schema.add(node)

        Form.__init__(self, schema_node, **kw)

    def get_comparator_from_column(self, prop):

        name = prop.key
        column = prop.columns[0]
        foreign_keys = column.foreign_keys
        column_type = getattr(column.type, 'impl', column.type)

        if isinstance(column_type, [Date,
                                    DateTime,
                                    Float,
                                    Integer,
                                    Numeric,
                                    Time]):
            values = [('', ''),
                      ('__lt__', '<'),
                      ('__lte__', '<='),
                      ('__eq__', '=='),
                      ('__neq__', '!='),
                      ('__gte__', '>='),
                      ('__gt__', '>')]

        elif isinstance(column_type, String):
            values = [('', ''),
                      ('like', 'like'),
                      ('ilike', 'ilike')]

        else:
            values = [('', ''),
                      ('__eq__', '=='),
                      ('__neq__', '!=')]

        if self.bootstrap:
            widget = ChosenSingleWidget(values=values)

        else:
            widget = SelectWidget(values=values)

        return SchemaNode(colander.String(),
                          name='comparator',
                          title='Comparator',
                          widget=widget)

    def get_comparator_from_relationship(self, prop):

        values = [('', ''),
                  ('__eq__', '=='),
                  ('__neq__', '!=')]

        if self.bootstrap:
            widget = ChosenSingleWidget(values=values)

        else:
            widget = SelectWidget(values=values)

        return SchemaNode(colander.String(),
                          name='comparator',
                          title='Comparator',
                          widget=widget)

    def dictify(self, obj):
        raise NotImplementedError()

    def validate(self, controls):
        values = SQLAlchemyForm.validate(self, controls)
        for name, value in values.items()
