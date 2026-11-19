from fastapi import APIRouter

from . import boms, materials, processes, routings

router = APIRouter()
router.include_router(materials.router)
router.include_router(processes.router)
router.include_router(boms.router)
router.include_router(routings.router)
