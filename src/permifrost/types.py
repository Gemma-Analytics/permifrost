from typing import Dict, List, TypedDict, Union


class DatabaseSchemaBase(TypedDict):
    shared: bool


class DatabaseSchema(DatabaseSchemaBase, total=False):
    # Optional owner, with required shared for each database
    owner: str


class MemberDictType(TypedDict, total=False):
    include: List[str]
    exclude: List[str]


class ReadWriteSchema(TypedDict, total=False):
    read: List[str]
    write: List[str]


class PrivilegeSchema(TypedDict):
    databases: ReadWriteSchema
    schemas: ReadWriteSchema
    tables: ReadWriteSchema


class OwnsSchema(TypedDict):
    databases: List[str]
    schemas: List[str]
    tables: List[str]


class RoleSchemaBase(TypedDict):
    warehouses: List[str]
    integrations: List[str]
    member_of: Union[MemberDictType, List[str]]
    privileges: PrivilegeSchema
    owns: OwnsSchema


class RoleSchema(RoleSchemaBase, total=False):
    owner: str


class UserSchemaBase(TypedDict):
    can_login: bool
    member_of: List[str]


class UserSchema(UserSchemaBase, total=False):
    owner: str
    has_password: bool
    display_name: str
    first_name: str
    middle_name: str
    last_name: str
    email: str
    comment: str
    default_warehouse: str
    default_namespace: str
    default_role: str


class WarehouseSchemaBase(TypedDict):
    size: str


class WarehouseSchema(WarehouseSchemaBase, total=False):
    owner: str


class IntegrationSchemaBase(TypedDict):
    category: str


class IntegrationSchema(IntegrationSchemaBase, total=False):
    owner: str


class PermifrostSpecSchemaBase(TypedDict):
    databases: List[Dict[str, DatabaseSchema]]
    roles: List[Dict[str, RoleSchema]]
    users: List[Dict[str, UserSchema]]
    warehouses: List[Dict[str, WarehouseSchema]]
    integrations: List[Dict[str, IntegrationSchema]]


class PermifrostSpecSchema(PermifrostSpecSchemaBase, total=False):
    version: str
    require_owner: bool
