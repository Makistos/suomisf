# -*- coding: utf-8 -*-
from sqlalchemy.pool import NullPool
from app.orm_decl import (Article, ArticleAuthor, ArticlePerson, ArticleTag,
                          Issue, Magazine, Person, Publisher, PublicationSize, Tag, IssueContent,
                          IssueEditor, ShortStory, Part, StoryTag, Contributor)
from app import app
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import re
import os
import csv
import glob
import re
from typing import Dict, List, Tuple, Optional

db_url = app.config['SQLALCHEMY_DATABASE_URI']

magazine_header = {'Magazine': 0,
                   'Issn': 1,
                   'Link': 2,
                   'Publisher': 4,
                   }

issue_header = {'Number': 0,
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

issues: Dict = {}
articles: Dict = {}
stories: Dict = {}

db_tags = {'runo': 0, 'filk': 0, 'raapale': 0}


def get_publisher(s, name: str) -> int:
    if name == '':
        return None

    publisher = s.query(Publisher).filter(Publisher.fullname == name).first()

    if not publisher:
        publisher = Publisher(name=name, fullname=name)
        s.add(publisher)
        s.commit()

    return publisher.id


def get_person(s, name: str, create_missing: bool = False) -> Optional[int]:
    if name == '':
        return None
    try:
        name = name.strip()
        if name[-1] == '.':
            # Replace last dot so this matches better
            name = name[0:-1]
        person = s.query(Person)\
            .filter(or_(Person.name.like(name + '%'),
                        Person.alt_name.like(name + '%')))\
            .first()

        if not person:
            if create_missing:
                if name == '':
                    print('Ei tiedossa')
                #name = name
                if name == 'anonyymi':
                    # Hack hack
                    name = 'Anonyymi'
                if name.find(',') == -1:
                    # Firstname lastname
                    names = name.split()
                    #alt_name = names[-1] + ', ' + ' '.join(names[0:-1])
                    alt_name = name
                    if name == 'Olaf Stapledon':
                        print(
                            f'Stapleton: {names[0]} {names[1]} - {len(names)}.')
                    if len(names) == 1:
                        first_name = ''
                        last_name = names[0]
                        this_name = last_name
                        print(f'Len == 1: {name} - {this_name}')
                    elif len(names) == 2:
                        first_name = names[0]
                        last_name = names[1]
                        this_name = last_name + ', ' + first_name
                        print(f'Len == 2: {name} - {this_name}')
                    else:
                        first_name = ' '.join(names[0:-1])
                        last_name = names[-1]
                        this_name = last_name + ', ' + ' '.join(first_name)
                else:
                    # Lastname, firstname
                    names = name.split(',')
                    last_name = names[0].strip()
                    first_name = str(' '.join(names[1:])).strip()
                    this_name = name
                    alt_name = ' '.join(first_name) + ' ' + last_name

                person = Person(name=this_name,
                                alt_name=alt_name,
                                fullname=this_name,
                                first_name=first_name,
                                last_name=last_name)
                s.add(person)
                s.commit()
            else:
                return None
    except Exception as e:
        print(f'get_person exception: {e}.')

    return person.id


def get_size(s, name: str) -> Optional[int]:
    size = s.query(PublicationSize)\
            .filter(PublicationSize.name == name)\
            .first()
    if size:
        return size.id
    else:
        return None


def get_tags(s, tags: List[str]) -> List[int]:
    if len(tags) == 0:
        return []
    tag_list: List[str] = []
    for tag in tags:
        tag_name = tag.strip().lower()
        tag_item = s.query(Tag).filter(Tag.name == tag_name).first()
        if not tag_item:
            tag_item = Tag(name=tag_name)
            s.add(tag_item)
            s.commit()
        tag_list.append(tag_name)
    tag_items = s.query(Tag).filter(Tag.name.in_(tag_list))
    return [x.id for x in tag_items]
    # return retval


def add_tag(s, story_id: int, tag_name: str):

    if tag_name not in db_tags:
        tag = Tag(name=tag_name)
        s.add(tag)
        s.commit()
        db_tags[tag_name] = tag.id

    tag_id = db_tags[tag_name]

    st = s.query(StoryTag)\
        .filter(StoryTag.shortstory_id == story_id)\
        .filter(StoryTag.tag_id == tag_id)\
        .first()
    if not st:
        st = StoryTag(shortstory_id=story_id,
                      tag_id=tag_id)

        s.add(st)
        s.commit()


def make_creators(s, ids) -> str:
    if len(ids) == 0:
        return ''
    people = s.query(Person).filter(Person.id.in_(ids)).all()
    return ' & '.join([x.name for x in people])


def import_issues(s, dir: str, name: str, id: int) -> None:
    if name not in issues:
        return
    try:
        number: Optional[int]
        count: Optional[int]
        year: Optional[int]
        for issue in issues[name]:
            if issue['Number'] != '':
                number = int(issue['Number'])
            else:
                number = None
            extra = issue['Number_extra']
            if issue['Count'] != '':
                count = int(issue['Count'])
            else:
                count = None
            if issue['Year'] != '':
                year = int(issue['Year'])
            else:
                year = None
            editors = issue['Editor'].split('&')
            image_src = issue['Image_src']
            pgs = issue['Pages']
            if pgs == '':
                pages = None
            else:
                pages = int(pgs)
            size = issue['Size']
            link = issue['Link']
            notes = issue['Notes']
            if 'Title' in issue:
                title = issue['Title']
            else:
                title = None

            editor_ids = []
            for editor in editors:
                editor_id = get_person(s, editor.strip(), True)
                if editor_id:
                    editor_ids.append(editor_id)

            size_id = get_size(s, size)

            if image_src == '':
                image_src = None

            iss = Issue(magazine_id=id,
                        number=number,
                        number_extra=extra,
                        count=count,
                        year=year,
                        image_src=image_src,
                        pages=pages,
                        size_id=size_id,
                        link=link,
                        notes=notes.strip(),
                        title=title)

            s.add(iss)
            s.commit()

            for eid in editor_ids:
                ie = IssueEditor(issue_id=iss.id, person_id=eid)
                s.add(ie)
            s.commit()

            import_articles(s, name,
                            number, extra, year,
                            count, iss.id)
            import_stories(s, name,
                           number, extra, year,
                           count, iss.id)

    except Exception as e:
        print(f'import_issues exception: {e}.')


def import_articles(s,
                    name: str,
                    issue_number: Optional[int],
                    issue_extra: str,
                    issue_year: Optional[int],
                    issue_count: Optional[int],
                    id: int) -> None:
    if not name in articles:
        return

    try:
        for article in articles[name]:
            in_issue: bool = False
            if article['Count'] != '':
                if (article['Count'] == str(issue_count) and
                        article['Number_extra'] == issue_extra):
                    in_issue = True
            else:
                if (article['Number'] == str(issue_number) and
                    article['Number_extra'] == issue_extra and
                        article['Year'] == str(issue_year)):
                    in_issue = True
            if in_issue:
                magazine = article['Lehti']  # Not really needed

                author_field = article['Tekijä']
                title = article['Artikkeli']
                tags = article['Aihe']
                people = article['Viitteet']

                author_names: List[str] = []
                author_ids = []
                for auth in author_field.split('&'):
                    author = auth.strip()
                    author_id = get_person(s, author.strip(), True)
                    if not author_id:
                        author_names.append(author)
                    else:
                        author_ids.append(author_id)

                person_ids = []
                if len(people) > 0:
                    person_names = None
                    for p in people.split('&'):
                        person = p.strip()
                        person_id = get_person(s, person.strip(), True)
                        if person_id:
                            person_ids.append(person_id)

                tag_list = tags.split(',')
                tag_ids = get_tags(s, tag_list)

                author_str = None
                if author_names is not None:
                    if len(author_names) > 0:
                        author_str = ' & '.join(author_names)

                # if len(author_ids) > 1:
                #    creator_str = make_creators(s, author_ids)
                # else:
                #    creator_str = author_field.strip()

                art = Article(title=title.strip())
                # creator_str=creator_str)

                s.add(art)
                s.commit()

                for tag_id in tag_ids:
                    a_tag = ArticleTag(article_id=art.id, tag_id=tag_id)
                    s.add(a_tag)
                s.commit()

                for author_id in author_ids:
                    a_person = ArticleAuthor(article_id=art.id,
                                             person_id=author_id)
                    s.add(a_person)
                s.commit()

                for person_id in person_ids:
                    p_id = ArticlePerson(article_id=art.id,
                                         person_id=person_id)
                    s.add(p_id)
                s.commit()

                ic = IssueContent(issue_id=id, article_id=art.id)
                s.add(ic)
                s.commit()

    except Exception as e:
        print(f'Exception in import_articles: {e}.')


def import_stories(s,
                   name: str,
                   issue_num: Optional[int],
                   issue_extra: str,
                   issue_year: Optional[int],
                   issue_count: Optional[int],
                   id: int):
    if not name in stories:
        return

    try:
        for story in stories[name]:
            in_issue: bool = False
            if story['Count'] != '':
                if (story['Count'] == str(issue_count) and
                        story['Number_extra'] == issue_extra):
                    in_issue = True
            else:
                if (story['Number'] == str(issue_num) and
                    story['Number_extra'] == issue_extra and
                        story['Year'] == str(issue_year)):
                    in_issue = True
            if in_issue:
                magazine = story['Lehti']  # Not really needed
                year = story['Year']
                authors = story['Tekijä']
                title = story['Novelli']
                orig_title = story['Alkup-novelli']
                orig_year = story['Alkup-vuosi']
                translators = story['Suomentaja']
                runo = story['runo']
                raapale = story['raapale']
                filk = story['filk']

                if orig_title == '':
                    orig_title = title

                if year == '':
                    year = None

                if orig_year == '':
                    orig_year = year

                author_ids = []
                for author in authors.split('&'):
                    person_id = get_person(s, author.strip(), True)
                    if person_id:
                        author_ids.append(person_id)

                translator_ids = []
                if len(translators) > 0:
                    for person in translators.split('&'):
                        person_id = get_person(s, person.strip(), True)
                        if person_id:
                            translator_ids.append(person_id)

                story_item = s.query(ShortStory)\
                    .filter(ShortStory.title == orig_title)\
                    .first()
                if not story_item:
                    # if len(author_ids) > 1:
                    #    creator_str = make_creators(s, author_ids)
                    # else:
                    #    creator_str = authors.strip()

                    story_item = ShortStory(title=title,
                                            orig_title=orig_title,
                                            pubyear=orig_year)
                    # creator_str=creator_str)
                    s.add(story_item)
                    s.commit()

                part_item = Part(shortstory_id=story_item.id,
                                 title=title)
                s.add(part_item)
                s.commit()

                for auth_id in author_ids:
                    auth = Contributor(part_id=part_item.id,
                                       person_id=auth_id,
                                       role_id=1)
                    s.add(auth)

                for trans_id in translator_ids:
                    translator = Contributor(part_id=part_item.id,
                                             person_id=trans_id,
                                             role_id=2)
                    s.add(translator)

                if runo != '':
                    add_tag(s, story_item.id, 'runo')
                if raapale != '':
                    add_tag(s, story_item.id, 'raapale')
                if filk != '':
                    add_tag(s, story_item.id, 'filk')

                ic = IssueContent(issue_id=id, shortstory_id=story_item.id)
                s.add(ic)
                s.commit()
    except Exception as e:
        print(f'Exception in import_stories: {e}.')


def read_file(filename: str, d: Dict):
    with open(filename, 'r', encoding='utf-8-sig') as csvfile:
        print(f'Reading from {filename}.')
        csv_contents = csv.DictReader(csvfile,
                                      dialect='excel',
                                      delimiter=';',
                                      quotechar='"')
        m = re.search('.+\/Magazines_(.+)_.+.csv', filename)
        if m:
            l = []
            for row in csv_contents:
                l.append(row)
            d[m.group(1).replace('_', ' ')] = l


def import_magazines(dir: str) -> None:
    global issues
    global articles

    engine = create_engine(db_url, poolclass=NullPool)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    filenames = glob.glob(dir + 'Magazines_*_lehdet.csv')
    print(f'Found issues: {filenames}')
    for filename in filenames:
        read_file(filename, issues)

    filenames = glob.glob(dir + 'Magazines_*_artikkelit.csv')
    print(f'Found article files: {filenames}.')
    for filename in filenames:
        read_file(filename, articles)

    filenames = glob.glob(dir + 'Magazines_*_novellit.csv')
    print(f'Found short story files: {filenames}.')
    for filename in filenames:
        read_file(filename, stories)

    for key, tag in db_tags.items():
        tag_item = Tag(name=key)
        s.add(tag_item)
        s.commit()
        db_tags[key] = tag_item.id

    with open(dir + 'Magazines.csv', 'r', encoding='utf-8-sig') as csvfile:
        print(f'Reading Magazines.csv')
        magazines = csv.DictReader(csvfile,
                                   dialect='excel',
                                   delimiter=';',
                                   quotechar='"')
        try:
            issn: Optional[str]
            link: Optional[str]
            publisher: Optional[str]
            pub_id: Optional[int]
            for magazine in magazines:
                name = magazine['Magazine']
                if 'Issn' in magazine:
                    issn = magazine['Issn']
                else:
                    issn = None
                if 'Link' in magazine:
                    link = magazine['Link']
                else:
                    link = None
                if 'Publisher' in magazine:
                    publisher = magazine['Publisher']
                    pub_id = get_publisher(s, publisher)
                else:
                    pub_id = None

                print(f'Writing {name}.')
                mag = Magazine(name=name,
                               publisher_id=pub_id,
                               issn=issn,
                               link=link,
                               type=0)
                s.add(mag)
                s.commit()

                import_issues(s, dir, name, mag.id)
        except Exception as e:
            print(f'Exception in import_magazines: {e}.')


if __name__ == '__main__':
    import_magazines('bibfiles/')
