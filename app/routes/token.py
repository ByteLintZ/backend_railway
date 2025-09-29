from fastapi import APIRouter
import secrets

router = APIRouter()

@router.post("/token/new")
def generate_token():
    """Generate a new unique user token."""
    token = secrets.token_urlsafe(32)
    return {"token": token}
