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
from typing import Dict, List, Tuple, Optional

db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

magazine_header = {'name': 0,
                   'issn': 1,
                   'link': 2,
                   'publisher': 4,
                   'fullname': 5
                   }

issue_header= {'Number': 0,
               'Count': 1,
               'Year': 2,
               'Editor': 3,
               'Image_src': 4,
               'Pges': 5,
               'Size': 6,
               'Link': 7,
               'Notes': 8,
               'Title': 9
              }

article_header = {'magazine': 0,
                  'number': 1,
                  'author': 2,
                  'title': 3,
                  'tags': 4
                 }

issues: Dict= {}
articles: Dict = {}


def get_publisher(s, name: str) -> int:
    if name == '':
        return None
    publisher = s.query(Publisher).filter(name == name).first()

    if publisher:
        return publisher.id
    else:
        publisher = Publisher(name=name, fullname=name)
        s.add(publisher)
        s.commit()
        return publisher.id


def get_person(s, name: str, create_missing: bool = False) -> Optional[int]:
    try:
        person = s.query(Person)\
                .filter(or_(Person.name == name,
                            Person.alt_name == name))\
                .first()

        if not person:
            if create_missing:
                alt_name = name
                names = name.split(' ')
                name = names[-1] + ', ' + ' '.join(names[0:-1])
                person = Person(name=name,
                                alt_name=alt_name,
                                first_name=' '.join(names[0:-1]),
                                last_name=names[-1])
                s.add(person)
                s.commit()
            else:
                return None
    except Exception as e:
        print(f'get_person exception: {e}.')

    return person.id


def get_size(s, name: str) -> Optional[int]:
    size = s.query(PublicationSize).filter(name == name).first()
    if size:
        return size.id
    else:
        return None


def get_tags(s, tags: List[str]) -> List[int]:
    retval = []
    for tag in tags:
        tag_item = s.query(Tag).filter(Tag.name == tag).first()
        if not tag_item:
            tag_item = Tag(name=tag)
            s.add(tag_item)
            s.commit()
        retval.append(tag_item.id)

    return retval


def import_issues(s, dir: str, name: str, id: int) -> None:
        if name not in issues:
            return
        try:
            for issue in issues[name]:
                number = issue['Number']
                count = issue['Count']
                year = issue['Year']
                editor = issue['Editor']
                image_src = issue['Image_src']
                pages = issue['Pages']
                size = issue['Size']
                link = issue['Link']
                notes = issue['Notes']
                title = issue['Title']

                editor_id = get_person(s, editor, True)
                size_id = get_size(s, size)

                if image_src == ''_
                    image_src = None

                iss = Issue(magazine_id=id,
                            number=int(number),
                            count=int(count),
                            year=int(year),
                            editor_id=editor_id,
                            image_src=image_src,
                            pages=int(pages),
                            size=size_id,
                            link=link,
                            notes=notes,
                            title=title)

                s.add(iss)
                s.commit()

                import_articles(s, dir, name, int(count), iss.id)
        except Exception as e:
            print(f'import_issues exception: {e}.')


def import_articles(s, dir: str, name: str, issue_num: int, id: int) -> None:
    if not name in articles:
        return

    try:
        for article in articles[name]:
            number: int = int(article['nro'])
            if issue_num == number:
                magazine = article['Lehti'] # Not really needed

                author_field = article['Tekijä']
                title = article['Artikkeli']
                tags = article['Aihe']
                people = article['Viitteet']

                author_names: List[str] = []
                author_ids = []
                authors = author_field.split('&')
                for auth in author_field.split('&'):
                    author = auth.strip()
                    author_id = get_person(s, author, True)
                    if not author_id:
                        author_names.append(author)
                    else:
                        author_ids.append(author_id)

                person_names = None
                person_ids = []
                for p in people.split(','):
                    person = p.strip()
                    person_id = get_person(s, person, True)
                    person_ids.append(person_id)

                tag_list = tags.split(',')
                tag_ids = get_tags(s, tag_list)

                if len(author_names) > 0:
                    author_str = ' & '.join(author_names)
                else:
                    author_str = None
                art = Article(title=title,
                            author=author_str)

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

    except Exception as e:
        print(f'Exception in import_articles: {e}.')


def import_magazines(dir: str) -> None:
    global issues
    global articles

    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    filenames = glob.glob(dir + 'Magazines_*_lehdet.csv')
    print(f'Found issues: {filenames}')
    for filename in filenames:
        with open(filename, 'r', encoding='utf-8-sig') as csvfile:
            print(f'Reading issues from {filename}.')
            issue_file = csv.DictReader(csvfile,
                                        dialect='excel',
                                        delimiter=';',
                                        quotechar='"')
            m = re.search('.+\/Magazines_(.+)_lehdet.csv', filename)
            if m:
                l = []
                #next(issue_file)
                for issue in issue_file:
                    l.append(issue)
                issues[m.group(1).replace('_', ' ')] = l
            else:
                continue

    filenames = glob.glob(dir + 'Magazines_*_artikkelit.csv')
    print(f'Found article files: {filenames}.')
    for filename in filenames:
        with open(filename, 'r', encoding='utf-8-sig') as csvfile:
            print(f'Reading articles from {filename}.')
            article_file = csv.DictReader(csvfile,
                                          dialect='excel',
                                          delimiter=';',
                                          quotechar='"')
            m = re.search('.+\/Magazines_(.+)_artikkelit_1.csv', filename)
            if m:
                l = []
                #next(article_file)
                for article in article_file:
                    l.append(article)
                articles[m.group(1).replace('_', ' ')] = l
            else:
                continue

    with open(dir + 'Magazines.csv', 'r', encoding='utf-8-sig') as csvfile:
        print(f'Reading Magazines.csv')
        magazines = csv.DictReader(csvfile,
                                   dialect='excel',
                                   delimiter=';',
                                   quotechar='"')
        next(magazines) # Skip first row
        next(magazines) # And second
        try:
            for magazine in magazines:
                name = magazine['Magazine']
                issn = magazine['Issn']
                link = magazine['Link']
                publisher = magazine['Pubname']

                pub_id = get_publisher(s, publisher)

                print(f'Writing {name}.')
                mag = Magazine(name=name,
                            publisher_id=pub_id,
                            issn=issn,
                            link=link)
                s.add(mag)
                s.commit()

                import_issues(s, dir, name, mag.id)
        except Exception as e:
            print(f'Exception in import_magazines: {e}.')


if __name__ == '__main__':
    import_magazines('bibfiles/')
