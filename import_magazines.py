# -*- coding: utf-8 -*-
from app.orm_decl import Article, ArticleAuthor, ArticlePerson, ArticleTag,\
Issue, Magazine, Person, Publisher, PublicationSize, Tag
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
import re
import os
import csv
import glob
import re
from typing import Dict, List, Tuple

db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

magazine_header = {'name': 0,
                   'issn': 1,
                   'link': 2,
                   'publisher': 4,
                   'fullname': 5
                   }

issue_header= {'number': 0,
               'count': 1,
               'year': 2,
               'editor': 3,
               'image_src': 4,
               'pages': 5,
               'size': 6,
               'link': 7,
               'notes': 8,
               'title': 9
              }

article_header = {'magazine': 0,
                  'number': 1,
                  'author': 2,
                  'title': 3,
                  'tags': 4
                 }

issues = {}
articles = {}


def get_publisher(s, name: str) -> int:
    publisher = s.query(Publisher).filter(name == name).first()

    if publisher:
        return publisher.id
    else:
        publisher = Publisher(name=name, fullname=name)
        s.add(publisher)
        s.commit()
        return publisher.id


def get_person(s, name: str) -> int:
    person = s.query(Person)\
              .filter(or_(Person.name == name,
                          Person.alt_name == name))\
              .first()

    if not person:
        return None

    return person.id


def get_size(s, name: str) -> int:
    size = s.query(PublicationSize).filter(name == name).first()
    if size:
        return size.id
    else:
        return None


def get_tags(s, tags: List[str]) -> List[int]:
    retval = []
    for tag in tags:
        tag_item = s.query(Tag).filter(name == tag).first()
        if not tag_item:
            tag_item = Tag(name=tag)
            s.add(tag_item)
            s.commit()
        retval.append(tag_item.id)

    return retval


def import_issues(s, dir: str, name: str, id: int) -> None:
        for magazine, issue in issues.items():
            number = issue[issue_header['number']]
            count = issue[issue_header['count']]
            year = issue[issue_header['year']]
            editor = issue[issue_header['editor']]
            image_src = issue[issue_header['image_src']]
            pages = issue[issue_header['pages']]
            size = issue[issue_heaer['size']]
            link = issue[issue_header['link']]
            notes = issue[issue_header['notes']]
            title = issue[issue_header['title']]

            editor_id = get_person(editor)
            size_id = get_size(size)

            iss = Issue(magazine_id=id,
                        number=number,
                        count=count,
                        year=year,
                        editor=editor_id,
                        image_src=image_src,
                        pages=pages,
                        size=size_id,
                        link=link,
                        description=notes)

            s.add(iss)
            s.commit()

            import_articles(s, dir, name, int(count), iss.id)


def import_articles(s, dir: str, name: str, issue_num: int, id: int) -> None:
    for magazine, article in articles.items():
        number = article[article_header['number']]
        if issue_num == number:
            magazine = article[article_header['magazine']] # Not really needed
            author_field = article[article_header['author']]
            title = article[article_header['title']]
            tags = article[article_header['tags']]

            author_names = None
            author_ids = []
            authors = author_field.split('&')
            for auth in author_field.split('&'):
                author = auth.strip()
                author_id = get_person(s, author)
                if not author_id:
                    author_names.appen(author)
                else:
                    author_ids.append(author_id)
            #person_names = None
            #person_ids = []
            #for person in persons
            tag_list = tags.split(',')
            tag_ids = get_tags(tag_list)

            art = Article(title=title,
                          author=author_names)

            s.add(art)
            s.commit()

            for tag_id in tag_ids:
                a_tag = ArticleTag(article_id=art.id, tag_id=tag_id)
                s.add(a_tag)
            s.commit()

            for author_id in author_ids:
                a_tag = ArticleAuthor(article_id=art.id,
                                      person_id=author_id)
                s.add(a_tag)
            s.commit()

            for person_id in person_ids:
                p_id = ArticlePerson(article_id=art.id,
                                     person_id=person_id)
                s.add(p_id)
            s.commit()



def import_magazines(dir: str) -> None:

    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    filenames = glob.glob(dir + 'Magazines_*_lehdet.csv')
    print(f'Found issues: {filenames}')
    for filename in filenames:
        with open(filename) as csvfile:
            print(f'Reading issues from {filename}.')
            issues = csv.reader(csvfile, delimiter=';', quotechar='"')
            magazine = re.search('_(.+)_', filename)
            issues[magazine] = issues

    filenames = glob.glob(dir + 'Magazines_*_artikkelit.csv')
    print('Found article files: {filenames}.')
    for filename in filenames:
        with open(filename) as csvfile:
            print(f'Reading articles from {filename}.')
            articles = csv.readerfile(csvfile, delimiter=';', quotechar='"')
            magazine = re.search('_(.+)_', filename)
            articles[magazine] = articles

    with open(dir + 'Magazines.csv') as csvfile:
        print(f'Reading Magazines.csv')
        magazines = csv.reader(csvfile, delimiter=';', quotechar='"')
        for magazine in magazines:
            name = magazine[magazine_header['name']]
            issn = magazine[magazine_header['issn']]
            link = magazine[magazine_header['link']]
            publisher = magazine[magazine_header['publisher']]
            fullname = magazine[magazine_header['fullname']]

            pub_id = get_publisher(publisher)

            mag = Magazine(name=name,
                           publisher_id=pub_id,
                           issn=issn,
                           link=link,
                           fullname=fullname)

            import_issues(s, dir, name, mag.id)


if __name__ == '__main__':
    import_magazines('bibfiles/')
