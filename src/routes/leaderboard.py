from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from src.models.user import UserOut
from src.services.leaderboard_service import get_leaderboard, get_leaderboard_for_user
from src.services.authentication_service import verify_token

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/get", response_model=Dict[str, Any])
async def read_leaderboard(user: UserOut = Depends(verify_token)):
    """
    Endpoint to get the leaderboard data.
    """
    try:
        leaderboard_data = get_leaderboard()
        return leaderboard_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Leaderboard data cannot be retrieved: {str(e)}"
        )


@router.get("/get/me", response_model=Dict[str, Any])
async def read_my_rank(user: UserOut = Depends(verify_token)):
    """
    This endpoint returns the leaderboard data for the authenticated user.
    """
    try:
        leaderboard_data = get_leaderboard_for_user(user.id)
        return leaderboard_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Leaderboard data cannot be retrieved: {str(e)}"
        )
