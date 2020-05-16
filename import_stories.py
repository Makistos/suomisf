from app.orm_decl import Work, Edition, Part, Person, Author, Editor, ShortStory, Alias
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import os
from typing import Dict, List, Tuple

people: Dict = {}

db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

def add_to_db(person: str):
    """ Add person missing from the main bib files to the database."""
    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    alt_name = ''
    name = ''
    first_name = ''
    last_name = ''
    if ' ' in person:
        if ',' in person:
            parts = person.split(', ')
            alt_name = parts[1] + ' ' + parts[0]
            first_name = parts[1]
            last_name = parts[0]
            name = person
        else:
            parts = person.split(' ')
            alt_name = person
            first_name = ' '.join(parts[0:-1])
            last_name = parts[-1]
            name = parts[-1] + ', ' + ' '.join(parts[0:-1])
    else:
        alt_name = person
        last_name = person
        name = person
        first_name = ''
    p = s.query(Person).filter(Person.alt_name == person)
    if not p:
        #print(f'Adding person to database: {name} | {alt_name} | {first_name} | {last_name}')
        p = Person(name=name, alt_name=alt_name,
                    first_name=first_name,
                    last_name=last_name)
        s.add(p)
        s.commit()

def get_people():
    """ Get the people in the database into a nice dict. """
    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    peoples = s.query(Person).all()

    for person in peoples:
        if person.alt_name not in people:
            people[person.alt_name] = person.id
            if person.first_name and person.last_name:
                #if person.last_name == 'Haldeman':
                first_name = person.first_name.split(' ')[0]
                people[person.last_name + ', ' + person.first_name] = person.id
                people[person.first_name + ' ' + person.last_name] = person.id
                people[first_name + ' ' + person.last_name] = person.id
                people[person.last_name + ', ' + first_name] = person.id

    with open('/tmp/people.txt', 'w') as fle:
        for person in peoples:
            if person.first_name:
                first_name = person.first_name
            else:
                first_name = '___'
            if person.last_name:
                last_name = person.last_name
            else:
                last_name = '___'
            fle.write(person.name + ' : ' + first_name + ' : ' + last_name + ' : ' + person.alt_name + '\n')
    with open('/tmp/people2.txt', 'w') as fle:
        for key, person in people.items():
            fle.write(key + '\n')


def create_keys(name: List[str], reversed: bool) -> List[str]:
    retval: List[str] = []
    if len(name) > 1:
        if reversed:
            first_name = name[-1].strip()
            last_name = name[0].strip()
            retval.append(name[1] + ' ' + ' '.join(name[0]))
        else:
            first_name = name[0].strip()
            last_name = name[-1].strip()
            retval.append(' '.join(name))
        retval.append(last_name + ', ' + first_name)
        retval.append(first_name + ' ' + last_name)
        retval.append(first_name.split(' ')[0] + ' ' + last_name)
    else:
        retval.append(name[0])
    return list(set(retval))


def get_authors(line: str) -> Tuple[List, bool]:
    """ Gets author info from line. """
    retval: List = []
    all_found: bool = True
    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)
    s = session()

    authors = line.strip().split(' & ')
    reversed = False
    for author in authors:
        a = None
        parts = []
        if 'oik.' in author:
            # Pseudonym
            alias = re.search('(\(oik\..+\))', author)
            if alias:
                author = author.replace(alias.group(1), '')
        if ',' in author:
            reversed = True
            parts = author.split(', ')
            author = parts[1] + ' ' + parts[0]
        else:
            parts = author.split(' ')
            reversed = False
        # a = s.query(Person)\
        #      .filter(Person.alt_name == author).first()
        keys = create_keys(parts, reversed)
        for key in keys:
            if key in people:
                a = people[key]
                break
        if not a:
            print(f'X: {author}')
            all_found = False
            if reversed:
                last_name = parts[0]
            else:
                last_name = parts[-1]
            alt = s.query(Person)\
                   .filter(Person.last_name.like(last_name))\
                   .all()
            if alt:
                print(f'?: {[a.alt_name for a in alt]}')
            else:
                # No meaningful alternative found so let's add this to db
                add_to_db(author)
        else:
            retval.append(a)

    return (list(set(retval)), all_found)


def import_stories(filename: str, books: Dict = {}):
    """ Import all the short stories from one the files. """
    stories: Dict = {}
    engine = create_engine(db_url, echo=False, encoding='iso8859-1')
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()

    id_re = '(?P<id>(\[[A-Z][a-zÄÅÖäåö]{2}[:_][A-ZÄÅÖa-zäåö][a-zÄÅÖäåö0-9]+[\]\}]\s?)+)'

    with open(filename, 'r', encoding='iso8859-1') as fle:
        line = fle.readline()  # Skip first line
        line = fle.readline()
        while not line.startswith('*******'):
            line = fle.readline()

        book_re = id_re + '\s=\s(?P<author>.+)\s:\s(?P<title>[A-Za-z0-9äöåÄÖÅ&\-\s\?:!]+)[,\.\(]'
        line = fle.readline()

        # Go through the list of books at the top of the file
        while not line.startswith('*******'):
            line = fle.readline()
            m = re.search(book_re, line, re.S|re.U)
            if m:
                if m.groupdict()['id'] in books:
                    continue
                author = m.groupdict()['author']
                is_ed = False
                if re.search('\(toim.\)', author):
                    author = author.replace('(toim.)', '').strip()
                    is_ed = True
                if '&' in author:
                    # One author is enough to identify the book
                    author = author.split(' & ')[0]
                books[m.groupdict()['id']] = [author, m.groupdict()['title'].strip(), is_ed]
                person = s.query(Person)\
                          .filter(Person.alt_name == author)\
                          .all()
                #if not person:
                #    print(f'Person not found: {author}')
            else:
                if line != '\n' and not line.startswith('*******'):
                    pass
                    #print(f'*** {line}')

        line = fle.readline()

        # Go through the lists of short stories
        ss_re = \
            r"""(?P<title>.+)  # Title
                \s
                \(
                (?P<origtitle>.+)  # Original title/year
                \)
                \s?""" + id_re
        prev_line: str = ''
        authors: List = []
        all_found: bool = True
        while line != '':
            if line == '\n':
                prev_line = line
                line = fle.readline()
                continue
            if line.startswith('-----'):
                # Previous line was an author name
                (authors, all_found) = get_authors(line=prev_line)
                prev_line = line
                line = fle.readline()
                continue
            if not all_found:
                # Skip stories if we didn't find all of the authors
                # from the database.
                prev_line = line
                line = fle.readline()
                continue
            ids: List = []
            m = re.search(id_re, line, re.S|re.U)
            #if not m:
            #    if (line != '\n' and not line.startswith('*****') and
            #        not authors):
            #        print(f'*** {line}')
            #    prev_line = line
            #    line = fle.readline()
            #    continue
            # Maybe there's more than just the title, like the
            # original title in some other language and the original
            # year of publication?
            m = re.search(ss_re, line, re.S|re.U|re.VERBOSE)
            if m:
                # Yep, we found something like that.
                title = m.groupdict()['title']
                items = m.groupdict()['origtitle'].split(',')
                if len(items) > 1:
                    # There's an original title and year.
                    orig_title = ','.join(items[0:-1])
                    year = items[-1]
                else:
                    # Either there's a year or an original title
                    m2 = re.match('(?P<year>\d\d\d\d)', m.groupdict()['origtitle'])
                    if m2:
                        # It's just a year
                        orig_title = title
                        year = m2.groupdict()['year']
                    else:
                        # It's an original title with no year
                        orig_title = m.groupdict()['title']
                        year = ''
                ids_tmp = m.groupdict()['id'].strip().split(']')
                for id in ids_tmp:
                    if id != '' and id != '\n':
                        ids.append(id.strip() + ']')

                #id = m.groupdict()['id']
                #print(f'{title}: {orig_title}, {year}, {id}')
                #for id in ids:
                #    if id not in books:
                #        print(f'{title} not found from list!')
            else:
                # Nothing but the title and id, perhaps?
                ss2_re = '(?P<title>.+)\s' + id_re

                m = re.search(ss2_re, line, re.S|re.U|re.VERBOSE)
                if m:
                    # Yep, just a title and id
                    title = m.groupdict()['title']
                    orig_title = title
                    year = ''
                    ids_tmp = m.groupdict()['id'].split(']')
                    for id in ids_tmp:
                        ids.append(id + ']')
                    #print(f'{title}, {id}')
                elif line != '\n':
                    # Some other crap we can just ignore
                    pass
                    #print(f'*** {line}')

            for id in ids:
                if id not in stories:
                    stories[id] = [{'title': title, 'orig_title': orig_title, 'year': year, 'authors': authors}]
                else:
                    stories[id].append({'title': title, 'orig_title': orig_title, 'year': year, 'authors': authors})
            prev_line = line
            line = fle.readline()

        # Combine books with stories and save to database
        for key, book in books.items():
            editions = []
            # Try to find edition by title and author/editor
            if book[0] not in people:
                #print(f'Author not found: {book[0]}')
                continue
            author_id = people[book[0]]
            if book[2] == False:
                # Person is also the author
                editions = s.query(Edition)\
                            .filter(Edition.title == book[1])\
                            .join(Part)\
                            .filter(Part.edition_id == Edition.id)\
                            .join(Author)\
                            .filter(Author.part_id == Part.id)\
                            .filter(Author.person_id == author_id)\
                            .all()
            else:
                # Person is the editor
                editions = s.query(Edition)\
                            .filter(Edition.title == book[1])\
                            .join(Editor)\
                            .filter(Editor.edition_id == Edition.id)\
                            .filter(Editor.person_id == author_id)\
                            .all()
            if not editions:
                #print(f'Edition not found: {book[0]} - {book[1]}')
                continue

            # This script assumes that for these books there is a
            # 1:m relationship, i.e. one work for m editions,
            # there are no editions consisting of multiple works.
            work = s.query(Work)\
                    .join(Part)\
                    .filter(Part.work_id == Work.id)\
                    .filter(Part.edition_id == editions[0].id)\
                    .first()
            # Create row in ShortStory and Part.
            # ShortStory has the original title while part has
            # the translated name if this is a translation.
            if key not in stories:
                pass
                #print(f'Key {key} not found in stories.')
            else:
                for st in stories[key]:
                    story = s.query(ShortStory)\
                             .filter(ShortStory.title == st['orig_title'],\
                                     ShortStory.pubyear == st['year'])\
                             .first()
                    if not story:
                        story = ShortStory(title = st['orig_title'], pubyear=st['year'])
                        s.add(story)
                        s.commit()
                    for edition in editions:
                        part = Part(edition_id = edition.id,
                                    title = st['title'],
                                    work_id = work.id,
                                    shortstory_id = story.id)
                        s.add(part)
                        s.commit()
                        for auth in st['authors']:
                            try:
                                author = Author(part_id = part.id,
                                                person_id = auth)
                            except Exception as e:
                                print(f'Excpetion {e}')
                            s.add(author)
                        s.commit()

if __name__ == '__main__':
    get_people()
    books: Dict = {'[Ias:V1]': ['Reijo Kalvas', 'Isaac Asimov Science Fiction valikoima 1', True],
                   '[Ias:V2]': ['Reijo Kalvas', 'Isaac Asimov Science Fiction valikoima 2', True],
                   '[Ias:V3]': ['Reijo Kalvas', 'Isaac Asimov Science Fiction valikoima 3', True],
                   '[Neu:My]': ['Neuvostokirjailijain tieteiskertomuksia', 'Maxwellin yhtälöt (Uravnenija Maksvella)', True],
                   '[Dah:Rk]': ['Roald Dahl', 'Rakkaani, kyyhkyläiseni', False],
                   '[Kin:Ao]': ['Stephen (Edwin) King', 'Anteeksi, oikea numero', False],
                   '[Kin:Py]': ['Stephen (Edwin) King', 'Pimeä yö, tähdetön taivas', False]}
    import_stories('bibfiles/sf_nov_u.txt', books)

    books = {'[Sun:Kt]': ['Shimo Suntila', 'Hei, rillumapunk!', True]}

    import_stories('bibfiles/sf_nov_s.txt', books)
