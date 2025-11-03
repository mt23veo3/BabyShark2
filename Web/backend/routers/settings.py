from fastapi import APIRouter, Body
from services.settings_service import (
    get_settings,
    update_settings,
    get_setting_by_key,
)

router = APIRouter()

@router.get("")
@router.get("/")
def all_settings():
    return get_settings()

@router.get("/{key}")
@router.get("/{key}/")
def setting_by_key(key: str):
    return get_setting_by_key(key)

@router.post("/update")
@router.post("/update/")
def update_config(payload: dict = Body(...)):
    return update_settings(payload)