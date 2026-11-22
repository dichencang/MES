from fastapi import APIRouter, Depends

from app.dto import plan as dto
from app.dto.management import Id
from app.routers.auth import Account, Db
from app.routers.management import Page, PageSize
from app.services import plan as service
from app.services.audit import AuditRoute
from app.services.management import require
from app.utils.responses import success

router = APIRouter(prefix="/plan", tags=["计划管理"], route_class=AuditRoute)


def permission(code):
    async def authorize(db: Db, account: Account):
        await require(db, account, f"plan:{code}")
    return Depends(authorize)


@router.get("/sales-orders", dependencies=[permission("sales-order:list")])
async def list_orders(
    db: Db, orderNo: str | None = None, customerName: str | None = None,
    status: dto.OrderStatus | None = None, dateStart: dto.DateString | None = None, dateEnd: dto.DateString | None = None,
    page: Page = 1, pageSize: PageSize = 10,
):
    return success(await service.list_orders(db, orderNo, customerName, status, dateStart, dateEnd, page, pageSize))


@router.get("/sales-orders/{id}", dependencies=[permission("sales-order:list")])
async def order_detail(id: Id, db: Db):
    return success(await service.order_detail(db, int(id)))


@router.post("/sales-orders", dependencies=[permission("sales-order:create")])
async def create_order(body: dto.SalesOrderInput, db: Db, account: Account):
    return success(await service.save_order(db, account["id"], body))


@router.put("/sales-orders/{id}", dependencies=[permission("sales-order:update")])
async def update_order(id: Id, body: dto.SalesOrderInput, db: Db, account: Account):
    return success(await service.save_order(db, account["id"], body, int(id)))


@router.post("/sales-orders/{id}/cancel", dependencies=[permission("sales-order:cancel")])
async def cancel_order(id: Id, body: dto.Cancel, db: Db, account: Account):
    return success(await service.cancel_order(db, account["id"], int(id), body))


@router.get("/sales-order-items", dependencies=[permission("production-plan:create")])
async def candidates(
    db: Db, orderNo: str | None = None, productId: Id | None = None,
    onlyAvailable: bool = False, page: Page = 1, pageSize: PageSize = 10,
):
    return success(await service.candidates(db, orderNo, int(productId) if productId else None,
                                            onlyAvailable, page, pageSize))


@router.get("/production-plans", dependencies=[permission("production-plan:list")])
async def list_plans(
    db: Db, planNo: str | None = None, orderNo: str | None = None, productId: Id | None = None,
    status: dto.PlanStatus | None = None, dateStart: dto.DateString | None = None, dateEnd: dto.DateString | None = None,
    page: Page = 1, pageSize: PageSize = 10,
):
    return success(await service.list_plans(db, planNo, orderNo, int(productId) if productId else None,
                                            status, dateStart, dateEnd, page, pageSize))


@router.get("/production-plans/{id}", dependencies=[permission("production-plan:list")])
async def plan_detail(id: Id, db: Db):
    return success(await service.plan_detail(db, int(id)))


@router.post("/production-plans", dependencies=[permission("production-plan:create")])
async def create_plan(body: dto.PlanCreate, db: Db, account: Account):
    return success(await service.save_plan(db, account["id"], body))


@router.put("/production-plans/{id}", dependencies=[permission("production-plan:update")])
async def update_plan(id: Id, body: dto.PlanUpdate, db: Db, account: Account):
    return success(await service.save_plan(db, account["id"], body, int(id)))


@router.post("/production-plans/{id}/cancel", dependencies=[permission("production-plan:cancel")])
async def cancel_plan(id: Id, body: dto.Cancel, db: Db, account: Account):
    return success(await service.cancel_plan(db, account["id"], int(id), body))


@router.post("/production-plans/{id}/transfer", dependencies=[permission("production-plan:transfer")])
async def transfer_plan(id: Id, db: Db):
    return success(await service.transfer_plan(db, int(id)))


@router.get("/gantt", dependencies=[permission("gantt:list")])
async def gantt(db: Db, dateStart: dto.DateString, dateEnd: dto.DateString, productId: Id | None = None):
    return success(await service.gantt(db, dateStart, dateEnd, int(productId) if productId else None))
