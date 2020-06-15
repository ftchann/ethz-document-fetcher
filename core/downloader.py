import asyncio
import copy
import shutil
import traceback
from urllib.parse import urlparse

import aiohttp
from colorama import Fore, Style

from core import pdf_highlighter
from core.constants import *
from core.storage.cache import *
from core.utils import *
from settings import settings

logger = logging.getLogger(__name__)


async def download_files(session: aiohttp.ClientSession, queue):
    while True:
        item = await queue.get()
        unique_key = item["unique_key"]
        signal_handler = item["signal_handler"]
        try:
            await download_if_not_exist(session, **item)
            signal_handler.finished_successful(unique_key)
        except asyncio.CancelledError:
            return
        except Exception as e:
            if settings.loglevel == "DEBUG":
                traceback.print_exc()
            logger.error(f"Consumer got an unexpected error: {type(e).__name__}: {e}")
            signal_handler.quit_with_error(unique_key, f"Could not download file from url: {item['url']}. Error: {e}")

        queue.task_done()


async def download_if_not_exist(session,
                                path,
                                url,
                                with_extension=True,
                                kwargs=None,
                                allowed_extensions=None,
                                forbidden_extensions=None,
                                checksum=None,
                                signal_handler=None,
                                unique_key=None):
    if kwargs is None:
        kwargs = {}

    if allowed_extensions is None:
        allowed_extensions = []

    allowed_extensions = [item.lower() for item in allowed_extensions + settings.allowed_extensions]
    if "video" in allowed_extensions:
        allowed_extensions += MOVIE_EXTENSIONS

    if forbidden_extensions is None:
        forbidden_extensions = []

    forbidden_extensions = [item.lower() for item in forbidden_extensions + settings.forbidden_extensions]
    if "video" in forbidden_extensions:
        forbidden_extensions += MOVIE_EXTENSIONS

    domain = urlparse(url).netloc

    timeout = aiohttp.ClientTimeout(total=0)
    if os.path.isabs(path):
        absolute_path = path
    else:
        absolute_path = os.path.join(settings.base_path, path)

    if not with_extension:
        absolute_path += "." + await check_extension(session, url)

    force = False
    if checksum is not None:
        force = not is_checksum_same(absolute_path, checksum)
    elif settings.force_download and domain not in FORCE_DOWNLOAD_BLACKLIST:
        force = True

    if os.path.exists(absolute_path) and not force:
        return

    if os.path.exists(absolute_path):
        headers = kwargs.get("headers", {})
        etag = get_etag(absolute_path)
        if etag is not None:
            headers["If-None-Match"] = etag
        if headers:
            kwargs["headers"] = headers

    if os.path.exists(absolute_path):
        action = ACTION_REPLACE
    else:
        action = ACTION_NEW

    file_name = os.path.basename(absolute_path)
    file_extension = get_extension(file_name)
    if allowed_extensions and file_extension.lower() not in allowed_extensions:
        return
    if file_extension.lower() in forbidden_extensions:
        return

    async with session.get(url, timeout=timeout, **kwargs) as response:
        response.raise_for_status()

        if response.status == 304:
            logger.debug(f"File '{absolute_path}' not modified")
            return

        if file_extension.lower() in MOVIE_EXTENSIONS:
            logger.info(f"Starting to download {file_name}")

        Path(os.path.dirname(absolute_path)).mkdir(parents=True, exist_ok=True)

        if action == ACTION_REPLACE and settings.keep_replaced_files:
            dir_path = os.path.dirname(absolute_path)
            pure_name, extension = split_name_extension(file_name)
            old_file_name = f"{pure_name}-old.{extension}"
            old_absolute_path = os.path.join(dir_path, old_file_name)
            os.replace(absolute_path, old_absolute_path)

        try:
            with open(absolute_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        except BaseException as e:
            os.remove(absolute_path)
            logger.debug(f"Removed file {absolute_path}")
            raise e

        if "ETag" in response.headers:
            save_etag(absolute_path, response.headers["ETag"])
        elif domain not in FORCE_DOWNLOAD_BLACKLIST:
            logger.warning(f"url: {url} had not an etag and is not in the blacklist")

    if action == ACTION_REPLACE and settings.keep_replaced_files and file_extension.lower() == "pdf":
        logger.debug("Adding highlights")
        pdf_highlighter.add_differ_highlight(absolute_path, old_absolute_path)

    if action == ACTION_REPLACE:
        method_msg = "Replaced"
    elif action == ACTION_NEW:
        method_msg = "Added new"
    else:
        method_msg = "Unexpected action"

    start = {
        "name": f"{method_msg} file: '{Fore.GREEN}{{}}{Style.RESET_ALL}'",
        "var": file_name,
        "priority": 100,
        "cut": "back",
    }

    end = {
        "name": " in '{}'",
        "var": os.path.dirname(absolute_path),
        "priority": -100,
        "cut": "front",
    }

    logger.info(fit_sections_to_console(start, end, margin=-8))

    save_checksum(absolute_path, checksum)


def fit_sections_to_console(*args, filler="..", min_length=10, margin=0):
    min_length = len(filler) + min_length
    c, _ = shutil.get_terminal_size(fallback=(0, 0))
    orig_sections = list(args)
    sections = copy.copy(orig_sections)
    sections.sort(key=lambda s: -s["priority"])

    free = c - sum([len(x["name"]) - 2 for x in sections]) - margin - 6
    length_vars = []
    count = 0
    for section in reversed(sections):
        length_vars.append(count)
        count += min(len(section["var"]), min_length)
    length_vars.reverse()
    if c:
        for length_var, section in zip(length_vars, sections):
            c_free = free - length_var
            if c_free < len(section["var"]) and len(section["var"]) > min_length:
                cut_length = max(c_free, min_length)
                if section["cut"] == "front":
                    section["var"] = (filler + section["var"][-cut_length + len(filler):])
                elif section["cut"] == "back":
                    section["var"] = (section["var"][:cut_length - len(filler)] + filler)

            free -= len(section["var"])

    return "".join([x["name"].format(x["var"]) for x in orig_sections])
