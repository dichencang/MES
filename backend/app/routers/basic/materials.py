from fastapi import APIRouter

from app.dto import basic as dto
from app.dto.management import Flag, Id, Status
from app.models import basic as model
from app.routers.auth import Account, Db
from app.routers.management import Page, PageSize
from app.services import basic as service
from app.services.audit import AuditRoute
from app.services.management import require
from app.utils.responses import success

router = APIRouter(tags=["基础数据"], route_class=AuditRoute)


@router.get("/materials/options")
async def material_options(
    db: Db, account: Account, keyword: str | None = None, isProduct: bool | None = None,
    status: Flag = "0", page: Page = 1, pageSize: PageSize = 20,
):
    return success(await service.archives(
        db, model.material, keyword, status, page, pageSize, product=isProduct, options=True,
    ))


@router.get("/materials")
async def list_materials(
    db: Db, account: Account, keyword: str | None = None, status: Flag | None = None,
    page: Page = 1, pageSize: PageSize = 10,
    categoryCode: str | None = None, isProduct: bool | None = None,
):
    await require(db, account, "basic:material:list")
    return success(await service.archives(db, model.material, keyword, status, page, pageSize, category=categoryCode, product=isProduct))


@router.post("/materials")
async def create_material(body: dto.MaterialCreate, db: Db, account: Account):
    await require(db, account, "basic:material:create")
    return success(await service.write_archive(db, model.material, body))


@router.put("/materials/{id}")
async def update_material(id: Id, body: dto.MaterialEdit, db: Db, account: Account):
    await require(db, account, "basic:material:update")
    return success(await service.write_archive(db, model.material, body, int(id)))


@router.put("/materials/{id}/status")
async def set_material_status(id: Id, body: Status, db: Db, account: Account):
    await require(db, account, "basic:material:set-status")
    await service.set_status(db, model.material, int(id), body.status)
    return success()
