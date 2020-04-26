import asyncio
import logging.config
import os

from colorama import init

init()

from settings.logger import LOGGER_CONFIG

logging.config.dictConfig(LOGGER_CONFIG)
logger = logging.getLogger(__name__)

import aiohttp

import ilias
import model_parser
import moodle
from settings import settings
from downloader import download_files
from utils import user_statistics


async def main():
    if not settings.check_if_set():
        raise ValueError("Please run 'python setup.py'")

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        await user_statistics(session, settings.username)

        await moodle.login(session)
        await ilias.login(session)

        producers = []
        model_file = os.path.join(os.path.dirname(__file__), "models/FS2020/semester2.yml")
        await model_parser.parse(session, producers, model_file)

        queue = asyncio.Queue()

        producers = [asyncio.create_task(function(session=session, queue=queue, base_path=base_path, **kwargs))
                     for function, kwargs, base_path in producers]

        consumers = [asyncio.create_task(download_files(session, queue)) for _ in range(20)]

        await asyncio.gather(*producers)

        await queue.join()

        for c in consumers:
            c.cancel()


if __name__ == '__main__':
    import time

    start_t = time.time()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    logger.info(f"Finished in {(time.time() - start_t):.2f} seconds")
