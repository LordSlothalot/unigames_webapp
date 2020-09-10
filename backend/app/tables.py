from flask_table import Table, Col, LinkCol
 
class UserTable(Table):
    _id = Col('_id', show=False)
    first_name = Col('First Name')
    last_name = Col('Last Name')
    email = Col('Email')
    role = Col('Role')
    edit = LinkCol('Edit', 'edit', url_kwargs=dict(id='_id'))