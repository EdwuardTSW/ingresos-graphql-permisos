from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Company, CompanyUser, CompanyUserRole, Permission, Role, RolePermission, User

PERMISSIONS = {
    "company.users.read": ("Ver usuarios", "Ver usuarios de la empresa"),
    "company.users.write": ("Administrar usuarios", "Invitar o desactivar usuarios"),
    "accounts.read": ("Ver cuentas", "Consultar cuentas de la empresa"),
    "accounts.write": ("Crear cuentas", "Registrar nuevas cuentas"),
    "concepts.read": ("Ver conceptos", "Consultar conceptos"),
    "concepts.write": ("Crear conceptos", "Registrar conceptos"),
    "transactions.read": ("Ver movimientos", "Consultar movimientos"),
    "transactions.write": ("Registrar movimientos", "Registrar ingresos o egresos"),
    "roles.read": ("Ver roles", "Consultar roles y permisos"),
    "roles.write": ("Configurar roles", "Configurar roles y permisos"),
}

ROLE_PERMISSIONS = {
    "ADMINISTRADOR": set(PERMISSIONS),
    "CONTADOR": {"company.users.read", "accounts.read", "accounts.write", "concepts.read", "concepts.write", "transactions.read", "transactions.write", "roles.read"},
    "CAPTURISTA": {"accounts.read", "concepts.read", "transactions.read", "transactions.write"},
    "CONSULTA": {"company.users.read", "accounts.read", "concepts.read", "transactions.read"},
}


def seed_database(db: Session) -> None:
    roles = {}
    for code in ROLE_PERMISSIONS:
        role = db.scalar(select(Role).where(Role.code == code))
        if not role:
            role = Role(code=code)
            db.add(role)
            db.flush()
        roles[code] = role
    permissions = {}
    for code, (name, description) in PERMISSIONS.items():
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if not permission:
            permission = Permission(code=code, name=name, description=description, is_active=True)
            db.add(permission)
            db.flush()
        permissions[code] = permission
    for role_code, granted in ROLE_PERMISSIONS.items():
        # Solo carga la matriz si el rol nunca tuvo relaciones. Una lista vacía
        # deliberadamente conservada tiene filas inactivas y no debe restablecerse.
        initialized = db.scalar(select(RolePermission.id).where(RolePermission.role_id == roles[role_code].id))
        if initialized is None:
            for permission_code in granted:
                db.add(RolePermission(role_id=roles[role_code].id, permission_id=permissions[permission_code].id, is_active=True))
    company = db.scalar(select(Company).where(Company.name == "Sistema General de Ingresos"))
    if not company:
        company = Company(name="Sistema General de Ingresos")
        db.add(company)
        db.flush()
    people = [("Ana", "ADMINISTRADOR", True), ("Luis", "CONTADOR", False), ("María", "CAPTURISTA", False), ("José", "CAPTURISTA", False), ("Pedro", "CONSULTA", False)]
    for name, role_code, is_admin in people:
        user = db.scalar(select(User).where(User.name == name))
        if not user:
            user = User(name=name)
            db.add(user)
            db.flush()
        member = db.scalar(select(CompanyUser).where(CompanyUser.company_id == company.id, CompanyUser.user_id == user.id))
        if not member:
            member = CompanyUser(company_id=company.id, user_id=user.id, is_admin=is_admin)
            db.add(member)
            db.flush()
            db.add(CompanyUserRole(company_user_id=member.id, role_id=roles[role_code].id, is_active=True))
    db.commit()
