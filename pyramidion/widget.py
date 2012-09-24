
from deform_bootstrap.widget import ChosenSingleWidget
from pyramid.path import DottedNameResolver


class SQLAChosenSingleWidget(ChosenSingleWidget):

    def __init__(self, class_, label, value, **kw):
        self.class_ = class_
        self.label = label
        self.value = value
        ChosenSingleWidget.__init__(self, **kw)

    def populate(self, session, *filters):
        class_ = DottedNameResolver().resolve(self.class_)
        query = session.query(getattr(class_, self.value),
                              getattr(class_, self.label))
        self.values = [('', '')] + [t for t in query.filter(*filters).all()]
