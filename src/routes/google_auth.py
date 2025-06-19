# src/routes/auth.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.services.google_service import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    id_token: str


@router.post("/google/verify")
async def verify_google_login(request: Request, payload: GoogleLoginRequest):
    """
    Receive Google ID token from the client,
    verify it, create/fetch the user in DB,
    then return your app's JWT.
    """
    try:
        # Validate ID token with Google's public keys or the Google library
        auth_response = await verify_google_id_token(payload.id_token)
        return JSONResponse(content=auth_response, status_code=200)
    except HTTPException as e:
        raise e
