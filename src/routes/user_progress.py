from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from src.models.user import UserOut
from src.services.authentication_service import verify_token
from src.services.user_progress_service import (
    get_user_progress,
    update_user_progress,
    set_weekly_goal,
)

router = APIRouter(
    prefix="/user-progress",
    tags=["User Progress"],
    responses={404: {"description": "Not found"}},
)


class WeeklyGoalRequest(BaseModel):
    goal: int


@router.get("/get")
async def get_progress(current_user: UserOut = Depends(verify_token)):
    """Kullanıcının ilerleme bilgilerini döndürür"""
    try:
        progress_data = await get_user_progress(current_user.id)
        return {
            "progress": progress_data.get("progress", 0.0),
            "remaining": progress_data.get("remaining", 0),
            "weekly_goal": progress_data.get("weekly_goal", 1000),
            "current_xp": progress_data.get("current_xp", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update")
async def update_progress(
    current_xp: int = Body(..., embed=True),
    current_user: UserOut = Depends(verify_token),
):
    """Kullanıcının ilerleme bilgilerini günceller"""
    try:
        result = await update_user_progress(current_user.id, current_xp)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/weekly-goal")
async def update_weekly_goal(
    request: WeeklyGoalRequest, current_user: UserOut = Depends(verify_token)
):
    """Kullanıcının haftalık hedefini günceller"""
    try:
        result = await set_weekly_goal(current_user.id, request.goal)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
