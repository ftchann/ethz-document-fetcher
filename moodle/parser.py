import asyncio
import re

from bs4 import BeautifulSoup

from one_drive import collector
from utils import *
from .constants import *


async def parse_main_page(session, queue, html, use_cache):
    soup = BeautifulSoup(html, "lxml")

    header = soup.find("div", class_="page-header-headings")
    header_name = str(header.h1.string)

    sections = soup.find_all("li", id=re.compile("section-([0-9]+)"))

    coroutines = [parse_sections(session, queue, section, header_name, use_cache) for section in sections]
    await asyncio.gather(*coroutines)


async def parse_sections(session, queue, section, header_name, use_cache):
    section_name = str(section["aria-label"])
    base_path = os.path.join(header_name, section_name)

    instances = section.find_all("div", class_="activityinstance")

    for instance in reversed(instances):

        try:
            img = instance.a.img["src"]
        except AttributeError:
            continue

        if img == PDF_IMG:
            file_name = str(instance.a.span.contents[0]) + ".pdf"
            url = instance.a["href"] + "&redirect=1"
            await queue.put({"path": os.path.join(base_path, file_name), "url": url})

        elif img == FOLDER_IMG:
            await parse_folder(session, queue, instance, base_path, use_cache)

        elif img == EXTERNAL_LINK_IMG:
            url = instance.a["href"] + "&redirect=1"
            name = str(instance.a.span.contents[0])

            url_reference_path = os.path.join(CACHE_PATH, "url.json")
            driver_url = await check_url_reference(session, url, url_reference_path)

            if "onedrive.live.com" in driver_url:
                await collector(session, queue, driver_url, base_path + f"; {name}")

    await parse_sub_folders(queue, soup=section, folder_path=base_path)


async def parse_folder(session, queue, instance, base_path, use_cache=False):
    folder_name = str(instance.a.span.contents[0])
    href = instance.a["href"]

    file_name = (base_path + ".txt").replace(":", " ").replace("/", " ")
    file_path = os.path.join(CACHE_PATH, file_name)

    if use_cache and os.path.exists(file_path):
        cached_href = load_txt(file_path)
        if cached_href == str(href):
            return

    if use_cache:
        save_txt(href, file_path)

    async with session.get(href) as response:
        text = await response.text()

    folder_soup = BeautifulSoup(text, "lxml")
    folder_path = os.path.join(base_path, folder_name)
    await parse_sub_folders(queue, soup=folder_soup, folder_path=folder_path, use_sub_folder_name=False)


async def parse_sub_folders(queue, soup, folder_path, use_sub_folder_name=True):
    sub_folders = filter(test_for_sub_folder, soup.find_all("span", class_="fp-filename"))
    for sub_folder in sub_folders:
        sub_folder_name = str(sub_folder.string)
        sub_folder_content = sub_folder.parent.next_sibling
        sub_files = sub_folder_content.find_all("span", class_="fp-filename")

        sub_folder_path = os.path.join(folder_path, sub_folder_name) if use_sub_folder_name else folder_path

        for sub_file in sub_files:
            sub_file_name = str(sub_file.string)
            sub_url = sub_file.parent["href"]
            await queue.put({"path": os.path.join(sub_folder_path, sub_file_name), "url": sub_url})


def test_for_sub_folder(tag):
    return tag.previous_sibling.img["src"] == SUB_FOLDER_IMG

