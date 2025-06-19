from fastapi import APIRouter, Depends, HTTPException, Body
from src.models.user import UserIn, UserOut, UserUpdate, PasswordChange
from src.services.user_service import (
    create_user,
    get_user_by_id,
    update_user,
    delete_user,
    refresh_access_token,
    invalidate_refresh_token,
    change_password,
)
from src.services.authentication_service import verify_token
from src.services.event_service import log_logout, log_refresh_token, get_user_events
from src.services.content_check_service import check_user_content, process_user_purpose_explanation
from src.models.user_event import EventType

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/register", status_code=201)
async def register(user_data: UserIn):
    # Check username content appropriateness
    if user_data.username:
        check_user_content(user_data.username, "username")
    
    # Process user purpose if provided
    if user_data.purpose:
        # Create user first, then update with processed purpose
        user = create_user(user_data)
        try:
            process_user_purpose_explanation(
                user_explanation=user_data.purpose,
                user_id=str(user["id"]),
                update_user_profile=True
            )
        except Exception:
            # If purpose processing fails, continue with registration
            pass
        return user
    else:
        user = create_user(user_data)
        return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, current_user=Depends(verify_token)):
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this user"
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/update")
async def update_user_route(user_data: UserUpdate, current_user=Depends(verify_token)):
    # Check username content appropriateness if being updated
    if user_data.username:
        check_user_content(user_data.username, "username", str(current_user.id))
    
    # Process user purpose if provided
    if user_data.purpose:
        try:
            process_user_purpose_explanation(
                user_explanation=user_data.purpose,
                user_id=str(current_user.id),
                update_user_profile=True
            )
            # Remove purpose from user_data since it's handled separately
            user_data.purpose = None
        except Exception:
            # If purpose processing fails, continue with update
            pass
    
    updated = update_user(str(current_user.id), user_data, str(current_user.id))
    if not updated:
        raise HTTPException(status_code=400, detail="User not updated")
    return {"message": "User updated successfully"}


@router.delete("/delete/{user_id}")
async def delete_user_route(user_id: str, current_user=Depends(verify_token)):
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user"
        )

    deleted = delete_user(user_id, str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.get("/get/me", response_model=UserOut)
async def get_current_user_profile(current_user=Depends(verify_token)):
    # The verify_token dependency already provides the user data.
    # No need to call get_current_user again.
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    return current_user


@router.post("/refresh-token")
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    tokens = refresh_access_token(refresh_token)
    if tokens and "user_id" in tokens:
        log_refresh_token(tokens["user_id"])
    return tokens


@router.post("/logout")
async def logout(current_user=Depends(verify_token)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authorized to logout")

    success = invalidate_refresh_token(str(current_user.id))
    if not success:
        raise HTTPException(status_code=400, detail="Logout failed")

    # Log the logout event
    log_logout(str(current_user.id))

    return {"message": "Logged out successfully"}


@router.get("/events")
async def get_activities(
    limit: int = 50, event_type: EventType = None, current_user=Depends(verify_token)
):
    """Get user activity history"""
    events = get_user_events(str(current_user.id), event_type, limit)
    return {"events": events}


@router.post("/change-password")
async def change_password_endpoint(
    password_data: PasswordChange, current_user=Depends(verify_token)
):
    """
    Change the user's password.
    Requires the current password and the new password.
    """
    success = change_password(
        str(current_user.id), 
        password_data.current_password, 
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Şifre değiştirme başarısız oldu")
    
    return {"message": "Şifre başarıyla değiştirildi"}
