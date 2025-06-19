from fastapi import APIRouter, Depends
from typing import List
from src.models.user import UserOut
from src.services.authentication_service import verify_token
from src.services.weekly_progress_service import (
    WeeklyProgressResponse,
    get_weekly_progress,
)

router = APIRouter()


@router.get("/weekly-progress/get", response_model=WeeklyProgressResponse)
async def get_weekly_progress_route(user: UserOut = Depends(verify_token)):
    """Kullanıcının haftalık ilerleme grafiği için veri döndürür"""
    return await get_weekly_progress(user.id)
