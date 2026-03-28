from ninja import Schema
from datetime import datetime
from typing import Optional


class UserSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    display_name: str


class WorkspaceSchema(Schema):
    id: int
    name: str
    slug: str
    created_at: datetime


class MembershipSchema(Schema):
    id: int
    user: UserSchema
    role: str
    joined_at: datetime


class InvitationSchema(Schema):
    id: int
    email: str
    created_at: datetime
    accepted_at: Optional[datetime] = None


class WorkspaceCreateSchema(Schema):
    name: str


class InviteSchema(Schema):
    email: str


class APIKeySchema(Schema):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
