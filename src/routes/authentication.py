from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from src.services.authentication_service import login, verify_token
from src.services.event_service import log_login, log_app_open

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@router.post("/login")
async def login_endpoint(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await login(form_data)
        log_login(user["user_id"])
        return user
    except HTTPException:
        # Re-raise the exception to maintain the original error
        raise
    except Exception as e:
        # Log the exception details for debugging
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred during login. Please try again."
        )


@router.post("/log-app-open")
async def app_open_endpoint(token: str = Depends(oauth2_scheme)):
    """
    Endpoint to log when the application is opened
    """
    # Get user from token
    user = await verify_token(token)
    # Assuming get_current_user_id is a function that verifies the token and retrieves the user ID
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    # Log the app open event
    log_app_open(user.id)
    return {"message": "App open event logged successfully"}
