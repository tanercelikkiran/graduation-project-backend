from fastapi import APIRouter, Depends, HTTPException
from src.services.xp_service import get_xp, update_xp as update_user_xp
from src.services.authentication_service import verify_token
from src.models.user import UserOut

router = APIRouter(
    prefix="/xp",
    tags=["xp"],
)


@router.get("/get")
async def get_user_xp_data(current_user: UserOut = Depends(verify_token)):
    # Verify user is accessing their own data or has admin rights

    user_data = await get_xp(current_user.id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_data


@router.post("/update")
async def update_xp(amount: dict, current_user: UserOut = Depends(verify_token)):
    # Verify user is accessing their own data or has admin rights
    user_id = current_user.id

    if not isinstance(amount, dict) or "xp" not in amount:
        raise HTTPException(status_code=400, detail="Invalid request body")

    xp_amount = amount["xp"]
    if not isinstance(xp_amount, int):
        raise HTTPException(status_code=400, detail="XP amount must be an integer")

    current_xp = await get_xp(user_id)
    await update_user_xp(user_id, current_xp["xp"] + xp_amount)
    return {"message": "XP updated successfully"}


@router.post("/add")
async def add_xp(amount: dict, current_user: UserOut = Depends(verify_token)):
    """
    Add XP to a user.
    """
    user_id = current_user.id
    # Verify user is accessing their own data or has admin rights
    if not isinstance(amount, dict) or "amount" not in amount:
        raise HTTPException(status_code=400, detail="Invalid request body")

    xp_amount = amount["amount"]
    if not isinstance(xp_amount, int):
        raise HTTPException(status_code=400, detail="XP amount must be an integer")

    current_xp = await get_xp(user_id)

    await update_user_xp(user_id, current_xp["xp"] + xp_amount)
    return {"message": "XP added successfully"}

