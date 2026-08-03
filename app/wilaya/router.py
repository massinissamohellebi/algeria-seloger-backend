from typing import Annotated

from fastapi import APIRouter, Depends

from app.wilaya.dependencies import get_wilaya_service
from app.wilaya.schemas import WilayaRead
from app.wilaya.service import WilayaService

router = APIRouter(prefix="/wilayas", tags=["wilayas"])

ServiceDep = Annotated[WilayaService, Depends(get_wilaya_service)]


@router.get("", response_model=list[WilayaRead])
async def list_wilayas(service: ServiceDep) -> list[WilayaRead]:
    """Public, unauthenticated list of the 58 Algerian wilayas, sorted by code."""
    return await service.list_wilayas()
