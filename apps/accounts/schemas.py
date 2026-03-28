from ninja import Schema


class UserSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    display_name: str
