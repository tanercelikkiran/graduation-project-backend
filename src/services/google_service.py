# src/services/google_service.py

from fastapi import HTTPException
from datetime import timedelta
import secrets
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from src.database.database import user_table
from src.services.user_service import create_user as create_local_user
from src.services.authentication_service import create_access_token
from src.models.user import UserIn


async def verify_google_id_token(token: str):
    """
    1. Verify the Google ID token
    2. Fetch or create user in the DB
    3. Return your app's JWT
    """
    try:
        # "audience" should be your Web client ID from Google Cloud console
        # or the Android/iOS client IDs if you validated that as well
        id_info = id_token.verify_oauth2_token(token, google_requests.Request())

        # Basic checks
        if "email" not in id_info:
            raise HTTPException(status_code=400, detail="No email found in token")

        email = id_info["email"]
        name = id_info.get("name", "GoogleUser")

        # Check if user exists in DB
        existing_user = user_table.find_one({"email": email})

        if not existing_user:
            # Create a new user
            random_password = secrets.token_hex(16)  # random placeholder
            new_user_data = UserIn(
                username=name,
                email=email,
                password=random_password,
                learning_language="",
                purpose="",
                level="",
            )
            created_user = create_local_user(new_user_data)
            user_id = created_user.id
        else:
            user_id = str(existing_user["_id"])

        # Generate your own access token
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=expires_delta
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "email": email,
            "user_id": user_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unexpected error: {str(e)}")
