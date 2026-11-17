import asyncio

from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

password_hash = PasswordHash((BcryptHasher(),))


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(password_hash.hash, password)


async def verify_password(password: str, encoded_hash: str) -> bool:
    return await asyncio.to_thread(password_hash.verify, password, encoded_hash)
