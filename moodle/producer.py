from bs4 import BeautifulSoup

from constants import BEAUTIFUL_SOUP_PARSER
from moodle.parser import parse_main_page


async def get_html(session, id):
    async with session.get(f"https://moodle-app2.let.ethz.ch/course/view.php?id={id}") as response:
        html = await response.read()
    return html


async def producer(session, queue, base_path, id):
    html = await get_html(session, id)
    return await parse_main_page(session, queue, html, base_path, id)


async def get_folder_name(session, id):
    html = await get_html(session, id)
    soup = BeautifulSoup(html, BEAUTIFUL_SOUP_PARSER)

    header = soup.find("div", class_="page-header-headings")
    header_name = str(header.h1.string)
    return header_name
