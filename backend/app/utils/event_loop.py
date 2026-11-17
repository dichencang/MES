import asyncio
import sys


def run(coroutine):
    if sys.platform == "win32":
        # psycopg's asynchronous connection requires add_reader on Windows.
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            return runner.run(coroutine)
    return asyncio.run(coroutine)
