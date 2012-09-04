# __init__.py
# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidion and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from colanderalchemy import SQLAlchemyMapping
import colander


__all__ = ['ReadSchema']


class ReadSchema(SQLAlchemyMapping):

    def __init__(self, cls, excludes=None, includes=None, nullables=None,
                 unknown='raise', column_comparators=['__eq__', '__le__',
                                                      '__lt__', '__ne__',
                                                      'contains', 'endswith',
                                                      'ilike', 'in_', 'like',
                                                      'match', 'startswith']):
        super(ReadSchema, self).__init__(cls, excludes,
                                         includes, nullables, unknown)
        self.column_comparators = column_comparators

    def get_schema_from_col(self, column, nullable=None):
        """ Build and return a Colander SchemaNode
            using information stored in the column.
        """

        missing = None
        if not column.nullable:
            missing = colander.required

        # Overwrite default missing value when nullable is specified.
        if nullable == False:
            missing = colander.required

        elif nullable == True:
            missing = None

        node = colander.SchemaNode(colander.Mapping(),
                                   name=column.name,
                                   missing=missing)

        value = super(ReadSchema,
                      self).get_schema_from_col(column, nullable=False)
        value.name = 'value'
        node.add(value)

        validator = colander.OneOf(self.column_comparators)
        raise Exception(dir(getattr(self._reg.cls, column.name)))
        comparator = colander.SchemaNode(colander.String(),
                                         validator=validator,
                                         name='comparator',
                                         missing=colander.required,
                                         default='__eq__')
        node.add(comparator)

        return node
