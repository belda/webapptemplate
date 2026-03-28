from ninja import Router
from .schemas import UserSchema

router = Router(tags=["Accounts"])


@router.get("/me/", response=UserSchema)
def me(request):
    """Return the current user's profile."""
    return request.user
