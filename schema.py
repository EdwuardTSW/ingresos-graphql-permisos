from decimal import Decimal
from enum import Enum

import strawberry
from sqlalchemy import select
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter

from database import SessionLocal
from models import Account, CompanyUser, CompanyUserRole, Permission, Role, RolePermission, Transaction


@strawberry.enum
class PermissionResource(Enum):
    COMPANY_USERS = "COMPANY_USERS"
    ACCOUNTS = "ACCOUNTS"
    CONCEPTS = "CONCEPTS"
    TRANSACTIONS = "TRANSACTIONS"
    ROLES = "ROLES"


RESOURCE_PREFIXES = {
    PermissionResource.COMPANY_USERS: "company.users.",
    PermissionResource.ACCOUNTS: "accounts.",
    PermissionResource.CONCEPTS: "concepts.",
    PermissionResource.TRANSACTIONS: "transactions.",
    PermissionResource.ROLES: "roles.",
}


@strawberry.type
class RoleType:
    id: int
    code: str


@strawberry.type
class PermissionType:
    id: int
    code: str
    name: str
    description: str


@strawberry.type
class RolePermissionType:
    role: RoleType
    permission: PermissionType
    is_active: bool


@strawberry.type
class CompanyUserType:
    id: int
    name: str


@strawberry.type
class AccountType:
    id: int
    name: str


@strawberry.type
class TransactionType:
    id: int
    type: str
    amount: float
    description: str


@strawberry.type
class RolePermissionPlan:
    role: RoleType
    current: list[PermissionType]
    to_activate: list[PermissionType]
    to_deactivate: list[PermissionType]
    unchanged: list[PermissionType]
    final_count: int


@strawberry.type
class RolePermissionUpdate:
    role: RoleType
    activated: list[PermissionType]
    deactivated: list[PermissionType]
    unchanged: list[PermissionType]
    final_count: int
    changed: bool


@strawberry.input
class PermissionRoleInput:
    role_id: int
    permission_id: int


@strawberry.input
class AssignRoleInput:
    company_user_id: int
    role_id: int


@strawberry.input
class SetRolePermissionsInput:
    role_id: int
    permission_ids: list[int]


def permission_type(permission: Permission) -> PermissionType:
    return PermissionType(id=permission.id, code=permission.code, name=permission.name, description=permission.description)


def role_type(role: Role) -> RoleType:
    return RoleType(id=role.id, code=role.code)


def exigir_permiso(db: Session, actor_company_user_id: int, permission_code: str) -> None:
    active_role = db.scalar(select(CompanyUserRole).where(CompanyUserRole.company_user_id == actor_company_user_id, CompanyUserRole.is_active.is_(True)))
    if not active_role:
        raise ValueError("El usuario no tiene un rol activo")
    allowed = db.scalar(select(RolePermission).join(Permission).where(RolePermission.role_id == active_role.role_id, RolePermission.is_active.is_(True), Permission.is_active.is_(True), Permission.code == permission_code))
    if not allowed:
        raise ValueError(f"Acceso rechazado: falta el permiso {permission_code}")


def _validate_configuration(db: Session, input: SetRolePermissionsInput) -> tuple[Role, list[Permission]]:
    role = db.get(Role, input.role_id)
    if not role or not role.is_active:
        raise ValueError("El rol no existe o está inactivo")
    if role.code == "ADMINISTRADOR":
        raise ValueError("No se permite cambiar la configuración de ADMINISTRADOR en este laboratorio")
    if len(input.permission_ids) != len(set(input.permission_ids)):
        raise ValueError("La lista de permissionIds contiene IDs repetidos")
    permissions = []
    for permission_id in input.permission_ids:
        permission = db.get(Permission, permission_id)
        if not permission or not permission.is_active:
            raise ValueError(f"El permiso {permission_id} no existe o está inactivo")
        permissions.append(permission)
    return role, sorted(permissions, key=lambda item: item.code)


def _configuration_diff(db: Session, input: SetRolePermissionsInput):
    role, desired = _validate_configuration(db, input)
    pairs = db.scalars(select(RolePermission).where(RolePermission.role_id == role.id)).all()
    all_pairs = {pair.permission_id: pair for pair in pairs}
    current = sorted([pair.permission for pair in pairs if pair.is_active], key=lambda item: item.code)
    desired_ids, current_ids = {item.id for item in desired}, {item.id for item in current}
    to_activate = [item for item in desired if item.id not in current_ids]
    to_deactivate = sorted([item for item in current if item.id not in desired_ids], key=lambda item: item.code)
    unchanged = sorted([item for item in current if item.id in desired_ids], key=lambda item: item.code)
    return role, current, to_activate, to_deactivate, unchanged, all_pairs


def apply_role_permissions(db: Session, input: SetRolePermissionsInput, force_failure: bool = False) -> RolePermissionUpdate:
    """Modifica la sesión sin confirmar; la mutación confirma una sola vez."""
    role, _current, to_activate, to_deactivate, unchanged, all_pairs = _configuration_diff(db, input)
    for permission in to_activate:
        pair = all_pairs.get(permission.id)
        if pair:
            pair.is_active = True
        else:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id, is_active=True))
    for permission in to_deactivate:
        all_pairs[permission.id].is_active = False
    db.flush()
    if force_failure:
        raise RuntimeError("Fallo controlado de prueba antes del commit")
    return RolePermissionUpdate(role=role_type(role), activated=[permission_type(item) for item in to_activate], deactivated=[permission_type(item) for item in to_deactivate], unchanged=[permission_type(item) for item in unchanged], final_count=len(input.permission_ids), changed=bool(to_activate or to_deactivate))


@strawberry.type
class Query:
    @strawberry.field
    def roles(self) -> list[RoleType]:
        with SessionLocal() as db:
            return [role_type(role) for role in db.scalars(select(Role).order_by(Role.code)).all()]

    @strawberry.field
    def permissions(self) -> list[PermissionType]:
        with SessionLocal() as db:
            return [permission_type(item) for item in db.scalars(select(Permission).order_by(Permission.code)).all()]

    @strawberry.field
    def role_permissions(self, role_id: int) -> list[RolePermissionType]:
        with SessionLocal() as db:
            pairs = db.scalars(select(RolePermission).where(RolePermission.role_id == role_id).order_by(RolePermission.id)).all()
            return [RolePermissionType(role=role_type(pair.role), permission=permission_type(pair.permission), is_active=pair.is_active) for pair in pairs]

    @strawberry.field
    def company_users(self) -> list[CompanyUserType]:
        with SessionLocal() as db:
            return [CompanyUserType(id=m.id, name=m.user.name) for m in db.scalars(select(CompanyUser).order_by(CompanyUser.id)).all()]

    @strawberry.field
    def permission_catalog(self, actor_company_user_id: int, resource: PermissionResource | None = None) -> list[PermissionType]:
        with SessionLocal() as db:
            exigir_permiso(db, actor_company_user_id, "roles.read")
            query = select(Permission).where(Permission.is_active.is_(True))
            if resource is not None:
                query = query.where(Permission.code.startswith(RESOURCE_PREFIXES[resource]))
            return [permission_type(item) for item in db.scalars(query.order_by(Permission.code)).all()]

    @strawberry.field
    def preview_role_permissions(self, input: SetRolePermissionsInput, actor_company_user_id: int) -> RolePermissionPlan:
        with SessionLocal() as db:
            exigir_permiso(db, actor_company_user_id, "roles.read")
            role, current, activate, deactivate, unchanged, _ = _configuration_diff(db, input)
            return RolePermissionPlan(role=role_type(role), current=[permission_type(item) for item in current], to_activate=[permission_type(item) for item in activate], to_deactivate=[permission_type(item) for item in deactivate], unchanged=[permission_type(item) for item in unchanged], final_count=len(input.permission_ids))


@strawberry.type
class Mutation:
    @strawberry.mutation
    def set_role_permissions(self, input: SetRolePermissionsInput, actor_company_user_id: int) -> RolePermissionUpdate:
        with SessionLocal() as db:
            try:
                exigir_permiso(db, actor_company_user_id, "roles.write")
                result = apply_role_permissions(db, input)
                db.commit()
                return result
            except Exception:
                db.rollback()
                raise

    @strawberry.mutation
    def assign_permission_to_role(self, input: PermissionRoleInput, actor_company_user_id: int) -> RolePermissionType:
        with SessionLocal() as db:
            try:
                exigir_permiso(db, actor_company_user_id, "roles.write")
                pair = db.scalar(select(RolePermission).where(RolePermission.role_id == input.role_id, RolePermission.permission_id == input.permission_id))
                if pair and pair.is_active: raise ValueError("La pareja rol-permiso ya está activa")
                if pair: pair.is_active = True
                else:
                    pair = RolePermission(role_id=input.role_id, permission_id=input.permission_id, is_active=True); db.add(pair)
                db.commit(); db.refresh(pair)
                return RolePermissionType(role=role_type(pair.role), permission=permission_type(pair.permission), is_active=pair.is_active)
            except Exception:
                db.rollback(); raise

    @strawberry.mutation
    def remove_permission_from_role(self, input: PermissionRoleInput, actor_company_user_id: int) -> RolePermissionType:
        with SessionLocal() as db:
            try:
                exigir_permiso(db, actor_company_user_id, "roles.write")
                pair = db.scalar(select(RolePermission).where(RolePermission.role_id == input.role_id, RolePermission.permission_id == input.permission_id, RolePermission.is_active.is_(True)))
                if not pair: raise ValueError("No existe una pareja rol-permiso activa")
                pair.is_active = False; db.commit(); db.refresh(pair)
                return RolePermissionType(role=role_type(pair.role), permission=permission_type(pair.permission), is_active=pair.is_active)
            except Exception:
                db.rollback(); raise

    @strawberry.mutation
    def assign_role(self, input: AssignRoleInput, actor_company_user_id: int) -> CompanyUserType:
        with SessionLocal() as db:
            try:
                exigir_permiso(db, actor_company_user_id, "roles.write")
                for assignment in db.scalars(select(CompanyUserRole).where(CompanyUserRole.company_user_id == input.company_user_id, CompanyUserRole.is_active.is_(True))).all(): assignment.is_active = False
                assignment = db.scalar(select(CompanyUserRole).where(CompanyUserRole.company_user_id == input.company_user_id, CompanyUserRole.role_id == input.role_id))
                if assignment: assignment.is_active = True
                else: db.add(CompanyUserRole(company_user_id=input.company_user_id, role_id=input.role_id, is_active=True))
                db.commit(); member = db.get(CompanyUser, input.company_user_id)
                return CompanyUserType(id=member.id, name=member.user.name)
            except Exception:
                db.rollback(); raise

    @strawberry.mutation
    def create_account(self, name: str, actor_company_user_id: int) -> AccountType:
        with SessionLocal() as db:
            exigir_permiso(db, actor_company_user_id, "accounts.write")
            item = Account(name=name); db.add(item); db.commit(); db.refresh(item)
            return AccountType(id=item.id, name=item.name)

    @strawberry.mutation
    def create_transaction(self, type: str, amount: float, description: str, actor_company_user_id: int) -> TransactionType:
        with SessionLocal() as db:
            exigir_permiso(db, actor_company_user_id, "transactions.write")
            item = Transaction(type=type, amount=Decimal(str(amount)), description=description)
            db.add(item); db.commit(); db.refresh(item)
            return TransactionType(id=item.id, type=item.type, amount=float(item.amount), description=item.description)


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
