from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.models import tenant, user, project, ontology

engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
print('Tables after create_all:', inspect(engine).get_table_names())
Session = sessionmaker(bind=engine)
db_session = Session()
t = Tenant(name='Test Corp', plan='free')
db_session.add(t)
db_session.commit()
print('Tenant created:', t.id)
from app.services.ontology.store import OntologyStore
store = OntologyStore(db_session)
obj = store.create_object(tenant_id=t.id, name='Order', source_entity='t_order', datasource_id='db1', datasource_type='sql')
print('Object created:', obj.id)
