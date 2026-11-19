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


@router.get("/routings/products")
async def list_routing_products(
    db: Db, account: Account, keyword: str | None = None,
    configStatus: dto.ConfigStatus = "all", page: Page = 1, pageSize: PageSize = 10,
):
    await require(db, account, "basic:routing:list")
    return success(await service.product_list(db, service.ROUTING, keyword, configStatus, page, pageSize))


@router.get("/routings/{id}")
async def get_routing(id: Id, db: Db, account: Account):
    await require(db, account, "basic:routing:query")
    return success(await service.version_details(db, service.ROUTING, int(id)))


@router.post("/routings")
async def create_routing(body: dto.VersionCreate, db: Db, account: Account):
    await require(db, account, "basic:routing:create")
    if body.source_version_id:
        await require(db, account, "basic:routing:query")
    return success(await service.new_version(db, service.ROUTING, body, account["id"]))


@router.put("/routings/{id}")
async def save_routing(id: Id, body: dto.RoutingSave, db: Db, account: Account):
    await require(db, account, "basic:routing:update")
    return success(await service.save_version(db, service.ROUTING, int(id), body, account["id"]))


@router.post("/routings/{id}/publish")
async def publish_routing(id: Id, body: dto.Publish, db: Db, account: Account):
    await require(db, account, "basic:routing:publish")
    return success(await service.publish_version(db, service.ROUTING, int(id), body, account["id"]))


@router.delete("/routings/{id}")
async def delete_routing(id: Id, draftToken: DeleteToken, db: Db, account: Account):
    await require(db, account, "basic:routing:delete")
    await service.delete_version(db, service.ROUTING, int(id), draftToken)
    return success()
