"""Create a dedicated local work-order rounding acceptance fixture."""

from decimal import Decimal

from sqlalchemy import select

from app.config.database import engine
from app.models import basic, system
from app.models.workorder_seed import fixture_archive, seed_definitions
from app.services.basic import module_lock
from app.utils.event_loop import run


async def provision():
    if engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("测试样例仅允许写入本地数据库")
    try:
        async with engine.begin() as db:
            await module_lock(db)
            actor = await db.scalar(select(system.user.c.id).where(system.user.c.username == "admin"))
            if actor is None:
                raise SystemExit("请先初始化本地数据库")
            product = await fixture_archive(db, basic.material, "QA-WO-ROUND", "舍零验收成品",
                                            category_code="FINISHED", unit_code="PCS", is_product=True)
            component = await fixture_archive(db, basic.material, "QA-WO-ROUND-PART", "舍零验收子件",
                                              category_code="RAW", unit_code="PCS", is_product=False)
            process = await fixture_archive(db, basic.process, "QA-WO-ROUND-STEP", "舍零验收工序")
            await seed_definitions(db, actor, product, component, process,
                                   base_qty=Decimal("1000"), component_qty=Decimal("1"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    run(provision())
