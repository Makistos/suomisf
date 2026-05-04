"""
Check lonnrot.net for work links not yet in the database.

Fetches https://www.lonnrot.net/etext.html, finds the
"Kirjailijat ja heidän kirjansa" section, then for each
author/work pair checks whether the work exists in the DB
and whether its lonnrot.net link is already in worklink.
Prints author and work name for any missing links.
"""
import sys
import os

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import dotenv

directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(directory_path)
import app.orm_decl as orm  # noqa: E402

dotenv.load_dotenv(os.path.join(directory_path, '../.env'))

BASE_URL = 'https://www.lonnrot.net'
PAGE_URL = f'{BASE_URL}/etext.html'
SECTION = 'Kirjailijat ja heidän kirjansa'

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Server omits charset; actual encoding is UTF-8
    resp.encoding = 'utf-8'
    return BeautifulSoup(resp.text, 'html.parser')


def find_section_start(soup: BeautifulSoup) -> object:
    for h2 in soup.find_all('h2'):
        if SECTION in h2.get_text():
            return h2
    return None


def work_exists_in_db(title: str) -> orm.Work | None:
    return (
        session.query(orm.Work)
        .filter(orm.Work.title.ilike(title))
        .first()
    )


def link_already_saved(work_id: int, link: str) -> bool:
    return (
        session.query(orm.WorkLink)
        .filter(
            orm.WorkLink.work_id == work_id,
            orm.WorkLink.link == link,
        )
        .first()
    ) is not None


def main() -> None:
    soup = fetch_soup(PAGE_URL)
    section_h2 = find_section_start(soup)
    if not section_h2:
        print(f'Section "{SECTION}" not found on page', file=sys.stderr)
        sys.exit(1)

    current_author = None
    node = section_h2.find_next_sibling()
    while node:
        if node.name == 'h2':
            break
        if node.name == 'h3':
            current_author = node.get_text(strip=True)
        elif node.name == 'ul' and current_author:
            for li in node.find_all('li'):
                a = li.find('a')
                if not a:
                    continue
                work_title = a.get_text(strip=True)
                href = a.get('href', '').strip()
                if not href:
                    continue
                full_link = BASE_URL + href

                work = work_exists_in_db(work_title)
                if not work:
                    continue

                if not link_already_saved(work.id, full_link):
                    print(
                        f'{current_author}: {work_title}'
                        f' - {full_link}'
                    )
        node = node.find_next_sibling()


if __name__ == '__main__':
    main()
