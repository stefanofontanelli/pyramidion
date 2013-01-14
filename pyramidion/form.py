# Copyright (C) 2012 the DeformAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is released under the MIT License
# http://www.opensource.org/licenses/mit-license.php

from colanderalchemy import SQLAlchemySchemaNode
from deform import Form
from deform.widget import (HiddenWidget,
                           SelectWidget,
                           SequenceWidget)
from deform_bootstrap.widget import (ChosenMultipleWidget,
                                     ChosenSingleWidget)
from deformalchemy import SQLAlchemyForm
from sqlalchemy import (Boolean,
                        Date,
                        DateTime,
                        Enum,
                        Float,
                        Integer,
                        Numeric,
                        String,
                        Time,
                        inspect)
import colander


class SQLAlchemySearchSchemaNode(SQLAlchemySchemaNode):

    def __init__(self, class_, includes=None,
                 excludes=None, overrides=None, unknown='raise'):
        self.comparators = {}
        self.order_by_values = []
        SQLAlchemySchemaNode.__init__(self,
                                      class_,
                                      includes,
                                      excludes,
                                      overrides,
                                      unknown)

    def add_nodes(self, includes, excludes, overrides):
        SQLAlchemySchemaNode.add_nodes(self, includes, excludes, overrides)
        start = colander.SchemaNode(colander.Int(),
                                    name='start',
                                    title='Start',
                                    missing=0,
                                    default=0,
                                    validator=colander.Range(min=0))
        limit = colander.SchemaNode(colander.Int(),
                                    name='limit',
                                    title='Limit',
                                    missing=25,
                                    default=25,
                                    validator=colander.Range(min=1))
        values = [prop.key for prop in self.inspector.column_attrs]
        order_by = colander.SchemaNode(colander.String(),
                                       name='order_by',
                                       title='Order By',
                                       missing=values[0],
                                       default=values[0],
                                       validator=colander.OneOf(values))
        direction_values = ['asc', 'desc']
        validator = colander.OneOf(direction_values)
        direction = colander.SchemaNode(colander.String(),
                                        name='direction',
                                        title='Direction',
                                        missing='asc',
                                        default='asc',
                                        validator=validator)
        intersect = colander.SchemaNode(colander.Boolean(),
                                        name='intersect',
                                        title='Intersect Criterions',
                                        missing=True,
                                        default=True)
        self.order_by_values = values
        self.direction_values = direction_values
        self.add(start)
        self.add(limit)
        self.add(order_by)
        self.add(direction)
        self.add(intersect)

    def get_schema_from_column(self, prop, overrides):
        col_node = SQLAlchemySchemaNode.get_schema_from_column(self,
                                                               prop,
                                                               overrides)
        col_node.missing = colander.null
        col_node.default = colander.null
        name = prop.key
        column = prop.columns[0]
        column_type = getattr(column.type, 'impl', column.type)
        type_ = colander.String()
        if isinstance(column_type, (Boolean, Enum)):
            comparators = [('', ''),
                           ('__eq__', '=='),
                           ('__neq__', '!=')]
            default_comp = '__eq__'

        elif isinstance(column_type, String):
            comparators = [('', ''),
                           ('like', 'like'),
                           ('ilike', 'ilike')]
            default_comp = 'like'

        elif isinstance(column_type, (Date,
                                      DateTime,
                                      Time)):
            comparators = [('', ''),
                           ('__lt__', '<'),
                           ('__lte__', '<='),
                           ('__eq__', '=='),
                           ('__neq__', '!='),
                           ('__gte__', '>='),
                           ('__gt__', '>')]
            default_comp = '__gte__'

        elif isinstance(column_type, (Float,
                                      Integer,
                                      Numeric)):
            comparators = [('', ''),
                           ('__lt__', '<'),
                           ('__lte__', '<='),
                           ('__eq__', '=='),
                           ('__neq__', '!='),
                           ('__gte__', '>='),
                           ('__gt__', '>')]
            default_comp = '__eq__'

        else:
            raise NotImplementedError('Unknown type: %s' % column_type)

        self.comparators[name] = comparators
        validator = colander.OneOf([v[0] for v in comparators if v[0]])
        # Create right node!
        col_node.title = col_node.title.title()
        comp_node = colander.SchemaNode(colander.String(),
                                        name='comparator',
                                        title='Comparator',
                                        missing=default_comp,
                                        default=default_comp,
                                        validator=validator)
        mapping_name = '{}_criterion'.format(name)
        mapping_title = ''  # '{} Criterion'.format(title)
        return colander.SchemaNode(colander.Mapping(),
                                   col_node,
                                   comp_node,
                                   name=mapping_name,
                                   title=mapping_title)

    def get_schema_from_relationship(self, prop, overrides):
        rel_node = SQLAlchemySchemaNode.get_schema_from_relationship(self,
                                                                     prop,
                                                                     overrides)
        if rel_node == None:
          return None

        name = prop.key
        if prop.uselist:
            comparators = [('', ''),
                           ('contains', 'contains'),
                           ('notcontains', 'not contains'),
                           ('__eq__', '=='),
                           ('__neq__', '!=')]
            default_comp = '__eq__'

        else:
            comparators = [('', ''),
                           ('__eq__', '=='),
                           ('__neq__', '!=')]
            default_comp = '__eq__'

        self.comparators[name] = comparators
        validator = colander.OneOf([v[0] for v in comparators if v[0]])
        # Create the right node!
        rel_node.name = 'value'
        rel_node.title = rel_node.title.title()
        comp_node = colander.SchemaNode(colander.String(),
                                        name='comparator',
                                        title='Comparator',
                                        missing=default_comp,
                                        default=default_comp,
                                        validator=validator)
        mapping_name = '{}_criterion'.format(name)
        mapping_title = '{} Criterion'.format(title)
        return colander.SchemaNode(colander.Mapping(),
                                   rel_node,
                                   comp_node,
                                   name=mapping_name,
                                   title=mapping_title)


class MultiCriterionSearchSchemaNode(SQLAlchemySearchSchemaNode):

    def get_sequence_schema(self, prop, node):
        name = prop.key
        title = name.title()
        sequence_name = '{}_criterions'.format(name)
        sequence_title = '{} Criterions'.format(title)
        return colander.SchemaNode(colander.Sequence(),
                                   node,
                                   missing=[],
                                   default=[],
                                   name=sequence_name,
                                   title=sequence_title)

    def get_schema_from_column(self, prop, overrides):
        node = SQLAlchemySearchSchemaNode.get_schema_from_column(self,
                                                                 prop,
                                                                 overrides)
        return self.get_sequence_schema(prop, node)

    def get_schema_from_relationship(self, prop, overrides):
        node = SQLAlchemySearchSchemaNode.get_schema_from_relationship(self,
                                                                       prop,
                                                                       overrides)
        return self.get_sequence_schema(prop, node)


class SQLAlchemySearchForm(SQLAlchemyForm):

    def __init__(self, class_, includes=None, excludes=None, overrides=None, **kw):
        self.class_ = class_
        self.bootstrap = 'bootstrap_form_style' in kw
        schema = SQLAlchemySearchSchemaNode(class_,
                                            includes=includes,
                                            excludes=excludes,
                                            overrides=overrides)
        self.inspector = inspect(class_)
        for prop in self.inspector.attrs:

            name = prop.key
            map_name = '{}_criterion'.format(name)
            if map_name not in schema:
                continue

            try:
                getattr(self.inspector.column_attrs, name)
                factory = 'get_widget_from_column'

            except AttributeError:
                getattr(self.inspector.relationships, name)
                factory = 'get_widget_from_relationship'

            mapping_schema = schema[map_name]
            value_schema = mapping_schema[name]
            if value_schema.widget is None:
                widget = getattr(self, factory)(prop)
                value_schema.widget = widget

            comparator_schema = mapping_schema['comparator']
            if comparator_schema.widget is None:
                widget = self.get_comparator_widget(schema.comparators[name])
                comparator_schema.widget = widget

        # Add widgets order_by, direction, intersect.
        order_by = schema['order_by']
        values = [(v, v) for v in schema.order_by_values]
        if order_by.widget is None and self.bootstrap:
            widget = ChosenSingleWidget(values=values)

        elif order_by.widget is None:
            widget = SelectWidget(values=values)

        order_by.widget = widget

        direction = schema['direction']
        values = [(v, v) for v in schema.direction_values]
        if direction.widget is None and self.bootstrap:
            widget = ChosenSingleWidget(values=values)

        elif direction.widget is None:
            widget = SelectWidget(values=values)

        direction.widget = widget

        intersect = schema['intersect']
        values = [(1, 'AND'), (0, 'OR')]
        if intersect.widget is None and self.bootstrap:
            widget = ChosenSingleWidget(values=values)

        elif intersect.widget is None:
            widget = SelectWidget(values=values)

        intersect.widget = widget

        super(SQLAlchemyForm, self).__init__(schema, **kw)

    def get_comparator_widget(self, values, multiple=False):

        if self.bootstrap and not multiple:
            widget = ChosenSingleWidget(values=values)

        elif self.bootstrap:
            widget = ChosenMultiWidget(values=values)

        else:
            widget = SelectWidget(values=values, multiple=multiple)

        return widget

    def populate_widgets(self, session):

        for prop in self.inspector.attrs:

            name = prop.key
            seq_key = '{}_criterions'.format(name)
            map_key = '{}_criterion'.format(name)
            node_key = 'value'
            widget = self.schema[seq_key][map_key][node_key].widget
            try:
                widget.populate(session)

            except AttributeError:
                continue


class SQLAlchemySimpleSearchForm(SQLAlchemyForm):

    def __init__(self, class_, includes=None, excludes=None, overrides=None, **kw):
        self.class_ = class_
        self.bootstrap = 'bootstrap_form_style' in kw
        schema = SQLAlchemySearchSchemaNode(class_,
                                            includes=includes,
                                            excludes=excludes,
                                            overrides=overrides)
        self.inspector = inspect(class_)
        for prop in self.inspector.attrs:

            name = prop.key
            map_name = '{}_criterion'.format(name)
            if map_name not in schema:
                continue

            try:
                getattr(self.inspector.column_attrs, name)
                factory = 'get_widget_from_column'

            except AttributeError:
                getattr(self.inspector.relationships, name)
                factory = 'get_widget_from_relationship'

            mapping_schema = schema[map_name]
            value_schema = mapping_schema[name]
            if value_schema.widget is None:
                widget = getattr(self, factory)(prop)
                value_schema.widget = widget

            comparator_schema = mapping_schema['comparator']
            if comparator_schema.widget is None:
                widget = self.get_comparator_widget(schema.comparators[name])
                comparator_schema.widget = widget

        # Add widgets start, limit order_by, direction, intersect.
        schema['start'].widget = HiddenWidget()
        schema['limit'].widget = HiddenWidget()
        schema['order_by'].widget = HiddenWidget()
        schema['direction'].widget = HiddenWidget()
        schema['intersect'].widget = HiddenWidget()

        # It is needed parent of __SQLAlchemyForm__ !!!
        super(SQLAlchemyForm, self).__init__(schema, **kw)

    def get_comparator_widget(self, values, multiple=False):
        return HiddenWidget()

    def populate_widgets(self, session):

        for prop in self.inspector.attrs:

            name = prop.key
            map_key = '{}_criterion'.format(name)
            try:
                self.schema[map_key][name].widget.populate(session)

            except (KeyError, AttributeError) as e:
                continue
