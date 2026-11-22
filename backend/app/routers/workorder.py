from fastapi import APIRouter, Depends

from app.dto.management import Id
from app.dto.plan import DateString, PlanUpdate
from app.dto import workorder as dto
from app.routers.auth import Account, Db
from app.routers.management import Page, PageSize
from app.services import workorder as service
from app.services.audit import AuditRoute
from app.services.management import require
from app.utils.responses import success

router = APIRouter(prefix="/workorders", tags=["生产工单"], route_class=AuditRoute)


def permission(code):
    async def authorize(db: Db, account: Account):
        await require(db, account, f"workorder:{code}")
    return Depends(authorize)


@router.get("", dependencies=[permission("list")])
async def list_orders(
    db: Db, workOrderNo: str | None = None, planNo: str | None = None,
    productId: Id | None = None, status: dto.Status | None = None,
    dateStart: DateString | None = None, dateEnd: DateString | None = None,
    page: Page = 1, pageSize: PageSize = 10,
):
    return success(await service.listing(db, workOrderNo, planNo, int(productId) if productId else None,
                                         status, dateStart, dateEnd, page, pageSize))


@router.get("/assignee-options", dependencies=[permission("assign")])
async def assignee_options(db: Db, keyword: str | None = None, page: Page = 1, pageSize: PageSize = 10):
    return success(await service.options(db, keyword, page, pageSize))


@router.get("/gantt", dependencies=[permission("gantt:list")])
async def gantt(db: Db, dateStart: DateString, dateEnd: DateString, productId: Id | None = None):
    return success(await service.gantt(db, dateStart, dateEnd, int(productId) if productId else None))


@router.get("/{id}", dependencies=[permission("list")])
async def detail(id: Id, db: Db):
    return success(await service.detail(db, int(id)))


@router.get("/{id}/events", dependencies=[permission("list")])
async def events(id: Id, db: Db, page: Page = 1, pageSize: PageSize = 10):
    return success(await service.events(db, int(id), page, pageSize))


@router.post("", dependencies=[permission("create")])
async def create(body: dto.Create, db: Db, account: Account):
    return success(await service.create_manual(db, account["id"], body))


@router.put("/{id}", dependencies=[permission("update")])
async def update(id: Id, body: PlanUpdate, db: Db, account: Account):
    return success(await service.update(db, account["id"], int(id), body))


@router.post("/{id}/release", dependencies=[permission("release")])
async def release(id: Id, db: Db, account: Account):
    return success(await service.transition(db, account["id"], int(id), "release"))


@router.post("/{id}/start", dependencies=[permission("start")])
async def start(id: Id, db: Db, account: Account):
    return success(await service.transition(db, account["id"], int(id), "start"))


@router.post("/{id}/cancel", dependencies=[permission("cancel")])
async def cancel(id: Id, body: dto.Cancel, db: Db, account: Account):
    return success(await service.transition(db, account["id"], int(id), "cancel", body.cancel_reason))


@router.put("/{id}/steps/{stepId}/assignees", dependencies=[permission("assign")])
async def assign(id: Id, stepId: Id, body: dto.Assign, db: Db, account: Account):
    return success(await service.assign(db, account["id"], int(id), int(stepId), body))
