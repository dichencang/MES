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


@router.get("/processes/options")
async def process_options(
    db: Db, account: Account, keyword: str | None = None, page: Page = 1, pageSize: PageSize = 20,
):
    return success(await service.archives(db, model.process, keyword, "0", page, pageSize, options=True))


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
