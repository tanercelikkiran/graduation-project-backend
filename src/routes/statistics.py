from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.models.user import UserOut
from src.services.statistics_service import get_user_statistics, update_user_statistics
from src.services.authentication_service import verify_token
from typing import Dict, Any

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)


@router.get("/get/all", response_model=Dict[str, Any])
async def get_statistics(user: UserOut = Depends(verify_token)):
    """
    Get all statistics for the authenticated user
    """
    return get_user_statistics(user.id)


@router.get("/get/vocabulary", response_model=Dict[str, Any])
async def get_vocabulary_statistics(
    user: UserOut = Depends(verify_token),
):
    """
    Get vocabulary statistics for the authenticated user
    """
    try:
        stats = get_user_statistics(user.id)
        if "vocabulary" in stats:
            return {"vocabulary": stats["vocabulary"]}
        return {"vocabulary": {}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bir hata oluştu: {str(e)}",
        )


@router.get("/get/pyramid", response_model=Dict[str, Any])
async def get_pyramid_statistics(user: UserOut = Depends(verify_token)):
    """
    Get pyramid statistics for the authenticated user
    """
    try:
        stats = get_user_statistics(user.id)
        if "pyramid" in stats:
            return {"pyramid": stats["pyramid"]}
        return {"pyramid": {}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bir hata oluştu: {str(e)}",
        )


@router.put("/update/{stats_type}", response_model=Dict[str, Any])
async def update_statistics(
    stats_type: str,
    stats_data: Dict[str, Any] = Body(...),
    user: UserOut = Depends(verify_token),
):
    """
    Update statistics for the authenticated user
    stats_type must be either 'pyramid' or 'vocabulary'
    """
    try:
        success = update_user_statistics(user.id, stats_type, stats_data)
        if success:
            return {"status": "success", "message": "İstatistikler güncellendi"}
        else:
            return {"status": "warning", "message": "İstatistikler güncellenmedi"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bir hata oluştu: {str(e)}",
        )
