import argparse
import asyncio
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import text

from app.config.database import engine
from app.models.system import metadata
from app.services.bootstrap import seed_system
from app.utils.event_loop import run


async def initialize(reset):
    url = engine.url
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database in {
        None, "postgres", "template0", "template1",
    }:
        raise SystemExit("Configure a local project database before running this command")
    async with await psycopg.AsyncConnection.connect(
        host=url.host, port=url.port, user=url.username, password=url.password,
        dbname="postgres", autocommit=True,
    ) as connection:
        cursor = await connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,),
        )
        exists = await cursor.fetchone()
        if not exists:
            await connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, config, "head")
    async with engine.begin() as connection:
        if reset:
            tables = ", ".join(table.name for table in metadata.sorted_tables)
            await connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY"))
        await seed_system(connection)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create and seed the local MES database")
    parser.add_argument("--reset", action="store_true", help="Erase all MES model tables and reseed")
    run(initialize(parser.parse_args().reset))
