from typing import Annotated

from fastapi import APIRouter, Query

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
DeleteToken = Annotated[dto.Token, Query()]


@router.get("/materials/options")
async def material_options(
    db: Db, account: Account, keyword: str | None = None, isProduct: bool | None = None,
    status: Flag = "0", page: Page = 1, pageSize: PageSize = 20,
):
    return success(await service.archives(
        db, model.material, keyword, status, page, pageSize, product=isProduct, options=True,
    ))


@router.get("/processes/options")
async def process_options(
    db: Db, account: Account, keyword: str | None = None, page: Page = 1, pageSize: PageSize = 20,
):
    return success(await service.archives(db, model.process, keyword, "0", page, pageSize, options=True))


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


@router.get("/processes")
async def list_processes(
    db: Db, account: Account, keyword: str | None = None, status: Flag | None = None,
    page: Page = 1, pageSize: PageSize = 10,
):
    await require(db, account, "basic:process:list")
    return success(await service.archives(db, model.process, keyword, status, page, pageSize))


@router.post("/processes")
async def create_process(body: dto.ProcessCreate, db: Db, account: Account):
    await require(db, account, "basic:process:create")
    return success(await service.write_archive(db, model.process, body))


@router.put("/processes/{id}")
async def update_process(id: Id, body: dto.ProcessEdit, db: Db, account: Account):
    await require(db, account, "basic:process:update")
    return success(await service.write_archive(db, model.process, body, int(id)))


@router.put("/processes/{id}/status")
async def set_process_status(id: Id, body: Status, db: Db, account: Account):
    await require(db, account, "basic:process:set-status")
    await service.set_status(db, model.process, int(id), body.status)
    return success()


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
