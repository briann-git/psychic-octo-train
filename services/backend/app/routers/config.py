import os

from fastapi import APIRouter, HTTPException, Request

from app.config import SAFE_CONFIG_KEYS

router = APIRouter()


@router.get("")
def get_config():
    return {k: os.environ[k] for k in SAFE_CONFIG_KEYS if k in os.environ}


@router.patch("")
async def update_config(request: Request):
    body = await request.json()
    updated: dict = {}
    for key, value in body.items():
        if key not in SAFE_CONFIG_KEYS:
            raise HTTPException(400, detail=f"Unknown config key: {key}")
        os.environ[key] = str(value)
        updated[key] = str(value)
    return updated
