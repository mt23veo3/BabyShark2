from fastapi import APIRouter
from services.user_service import (
    get_user_info,
    get_session_info,
)

router = APIRouter()

@router.get("/info")
@router.get("/info/")
def user_info():
    return get_user_info()

@router.get("/session")
@router.get("/session/")
def session_info():
    return get_session_info()