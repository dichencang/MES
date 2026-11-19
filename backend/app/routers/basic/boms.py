from typing import Annotated

from fastapi import APIRouter, Query

from app.dto import basic as dto
from app.dto.management import Id
from app.routers.auth import Account, Db
from app.routers.management import Page, PageSize
from app.services import basic as service
from app.services.audit import AuditRoute
from app.services.management import require
from app.utils.responses import success

router = APIRouter(tags=["基础数据"], route_class=AuditRoute)
DeleteToken = Annotated[dto.Token, Query()]


@router.get("/boms/products")
async def list_bom_products(
    db: Db, account: Account, keyword: str | None = None,
    configStatus: dto.ConfigStatus = "all", page: Page = 1, pageSize: PageSize = 10,
):
    await require(db, account, "basic:bom:list")
    return success(await service.product_list(db, service.BOM, keyword, configStatus, page, pageSize))


@router.get("/boms/{id}")
async def get_bom(id: Id, db: Db, account: Account):
    await require(db, account, "basic:bom:query")
    return success(await service.version_details(db, service.BOM, int(id)))


@router.post("/boms")
async def create_bom(body: dto.VersionCreate, db: Db, account: Account):
    await require(db, account, "basic:bom:create")
    if body.source_version_id:
        await require(db, account, "basic:bom:query")
    return success(await service.new_version(db, service.BOM, body, account["id"]))


@router.put("/boms/{id}")
async def save_bom(id: Id, body: dto.BomSave, db: Db, account: Account):
    await require(db, account, "basic:bom:update")
    return success(await service.save_version(db, service.BOM, int(id), body, account["id"]))


@router.post("/boms/{id}/publish")
async def publish_bom(id: Id, body: dto.Publish, db: Db, account: Account):
    await require(db, account, "basic:bom:publish")
    return success(await service.publish_version(db, service.BOM, int(id), body, account["id"]))


@router.delete("/boms/{id}")
async def delete_bom(id: Id, draftToken: DeleteToken, db: Db, account: Account):
    await require(db, account, "basic:bom:delete")
    await service.delete_version(db, service.BOM, int(id), draftToken)
    return success()
