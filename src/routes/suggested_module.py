from fastapi import APIRouter, Depends
from src.models.user import UserOut
from src.services import suggested_module_service
from src.services.authentication_service import verify_token

router = APIRouter(prefix="/suggested-module", tags=["suggested-module"])


@router.get("/get")
async def get_suggested_module(user: UserOut = Depends(verify_token)):
    module_type = suggested_module_service.get_suggested_module_type(user.id)
    return {"module_type": module_type}
