import aai_logon
from .constants import *


async def login(session):
    await aai_logon.login(session, AUTH_URL, IDP_DATA)


async def test_connection(session):
    async with session.get(BASE_URL) as response:
        content = await response.read()

    return b"Moodle Course: Hier k\xc3\xb6nnen Sie sich anmelden" not in content

