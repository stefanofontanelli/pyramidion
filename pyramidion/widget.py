
from deform_bootstrap.widget import ChosenSingleWidget
from sqlalchemy.orm.mapper import class_mapper


class SQLAChosenSingleWidget(ChosenSingleWidget):

    def __init__(self, class_, label, value, **kw):
        self.class_ = class_
        self.label = label
        self.value = value
        ChosenSingleWidget.__init__(self, **kw)

    def populate(self, session, *filters):
        class_ = class_mapper(self.class_, compile=False)
        query = session.query(getattr(class_, self.value),
                              getattr(class_, self.label))
        self.values = [t for t in query.filter(*filters).all()]
