import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ingresos.db")

from database import Base, SessionLocal, engine
from models import Permission, Role, RolePermission
from schema import SetRolePermissionsInput, apply_role_permissions
from seed import seed_database


class AtomicidadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_database(db)

    def test_fallo_controlado_revierte_toda_la_lista(self):
        with SessionLocal() as db:
            role = db.query(Role).filter_by(code="CAPTURISTA").one()
            initial = [pair.permission.code for pair in db.query(RolePermission).filter_by(role_id=role.id, is_active=True).all()]
            ids = [item.id for item in db.query(Permission).filter(Permission.code.in_(["accounts.read", "accounts.write", "concepts.read", "transactions.read", "transactions.write"])).all()]
            with self.assertRaisesRegex(RuntimeError, "Fallo controlado"):
                apply_role_permissions(db, SetRolePermissionsInput(role_id=role.id, permission_ids=ids), force_failure=True)
            db.rollback()
        with SessionLocal() as verification:
            role = verification.query(Role).filter_by(code="CAPTURISTA").one()
            final = [pair.permission.code for pair in verification.query(RolePermission).filter_by(role_id=role.id, is_active=True).all()]
        self.assertCountEqual(initial, final)


if __name__ == "__main__":
    unittest.main()
