
from app.orm_decl import Book, Person, BookPerson, Publisher, Pubseries, Bookseries, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from importbib import publishers
from importbib import bookseries, pubseries, important_pubseries, misc_strings
import re
import os
from dotenv import load_dotenv

publishers_re = {}
bookseries_re = {}
pubseries_re = {}
for pub in publishers:
    publishers_re[pub[0]] = re.compile('(' + pub[0] + ')[\.\s]')
for series in pubseries:
    pubseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX\d]+)?')
for series in bookseries:
    bookseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX\d]+)?')
translator_re = re.compile("([a-zA-ZåäöÅÄÖ]+\s)*([Ss]uom\.?\s)([A-ZÄÅÖ]+[\.\s]?[a-zA-ZäöåÅÄÖéü&\-]*[\.\s]?[a-zA-ZåäöÅÄÖéü&\-\s,]*)(\.)")
translator_re2 = re.compile("([Ss]uom\.?\s)?([A-ZÄÅÖ](\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü\-]+)\s?([A-ZÄÅÖ](\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü]+))*\s*([A-ZÅÄÖ](\.\s?[A-ZÄÅÖ][a-zåäö]*|[a-zäöåü]+)*)*\s?([A-ZÅÄÖa-zåäöü]+)*(\.)*)")
translator_re3 = re.compile("([A-ZÄÅÖ]+[\.\s]?[a-zA-ZäöåÅÄÖéü&\-]*[\.\s]?[a-zA-ZåäöÅÄÖéü&\-\s]*)")

    #([Ss]uom\.?\s)? # group 1
    #   ([A-ZÄÅÖ] # group 2
    #    (\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü\-]+) # group 3
    #    \s
    #    ([A-ZÄÅÖ] # group 4
    #        (\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü]+))? # group 5
    #    \s?
    #    ([A-ZÅÄÖ]
    #        (\.\s?[A-ZÄÅÖ][a-zåäö]*|[a-zäöåü]+))?
    #    \s
    #    ([A-ZÅÄÖa-zåäöü]+)
    #   (\.))
    #   """

pubseries_publisher = {}

def find_item_from_string(item_list, st, patterns):
    retval = ()
    match_list = []
    # Following is complex. Issue here is that there are other
    # stuff, notably publishers who could mess this up. E.g. there
    # are plenty of series with the word "kirja" in them.
    # Unfortunately there was also a publishing company called
    # "Kirja". We have to somehow distinguish these. Solution is
    # to look for the longest string that matches in the
    # bookseries list. This is still not foolproof but should work
    # in most cases.
    # In the series list, first item contains the regular
    # expression pattern and second the cleaned up name of the
    # series.
    for item in item_list:
        m = patterns[item[0]].search(st)
        if m:
            # Add all matches to a list. Item contains the entire
            # match and cleaned up name of the item.
            if 'num' in m.groupdict():
                num = m.groupdict()['num']
            else:
                num = ''
            match_list.append((m.group(0), item[1], num))
    if len(match_list) > 0:
        maxlen = 0
        # Search for the longest matching string
        for item in match_list:
            if len(item[0]) > maxlen:
                maxlen = len(item[0])
                retval = item
    return retval


def single_name(s, pat, part_of_multi):
    to_remove = ''
    name = ''

    m2 = re.search('[Ss]uom', s)
    if not m2 and part_of_multi:
        pat = translator_re3
        idx = 0
    else:
        idx = 3
    m = pat.search(s)
    if m:
        found = m.group(idx)
        if found[-1].isupper():
            # Last character is upper case -> name is probably something like
            # Pentti J. Penttinen. We assume therefore there are more stops
            # than just the separator.
            m2 = translator_re2.search(s)
            if m2:
                name = m2.group(2)
                to_remove = m2.group(0)
            else:
                print("Not found: {} {}".format(s, found[-1]))
        else:
            name = found
            to_remove = m.group(0)

    return (to_remove, name)

def multiple_persons(s, pat):
    handled_list = []
    retval = []
    to_remove = ''
    has_and = False
    n1 = s.split('&')
    if len(n1) == 1:
        # No &'s, e.g. "A, B, C"
        names = s.split(',')
    elif len(n1) == 2:
        # One &, e.g. "A, B & C"
        names = n1[0].split(',')
        names.append(n1[1])
    else:
        # More than one &, e.g. "A & B & C"
        names = n1

    #names = re.split('[&,]', s)
    if ' ja ' in names[-1]:
       last_pair = names[-1]
       del names[-1]
       names += last_pair.split(' ja ')
       has_and = True
       #print(last_pair.split(' ja '))
    for name in names:
        n = re.sub(r'[Ss]uom\.?', '', name.strip())
        retval.append(n)
        #match = single_name(name, pat, True)
        #retval.append(match[1])
        #handled_list.append(match[0])

    # Now we need to reconstruct the matched string back
    for idx, name in enumerate(retval[:-1]):
        print("name : {}".format(name))
        m = re.search(str(name) + '(.+)' + str(retval[idx+1]), s)
        if m:
            to_remove += str(name) + m.group(1)
        else:
            to_remove += str(name)
            if has_and:
                to_remove += ' ja '
    to_remove += str(retval[-1])
    return (to_remove, retval)

#def multiple_persons(s, pat):
#    handled_list = []
#    retval = []
#    to_remove = ''
#    names = re.split('&', s)
#    if ' ja ' in names[-1]:
#       last_pair = names[-1]
#       del names[-1]
#       names += re.split(' ja ', last_pair)
    #print(names)
#    for name in names:
#        match = single_name(name, pat, True)
#        retval.append(match[1])
#        handled_list.append(match[0])

    # Now we need to reconstruct the matched string back
#    for idx, name in enumerate(retval[:-1]):
#        m = re.search(str(name) + '(.+)' + str(retval[idx+1]), s)
#        to_remove += str(name) + m.group(1)
#    to_remove += str(retval[-1])
#    return (to_remove, retval)

def find_persons(s, type):

    names = []
    to_remove = ''
    if type == 'translator':
        pat = translator_re

    if ',' in s or '&' in s or " ja " in s:
        (to_remove, names) = multiple_persons(s, pat)
    else:
        (to_remove, n) = single_name(s, pat, False)
        names.append(n)

    return (to_remove, names)

def get_books(books):
    """ This is so ugly it hurts my head. """
    retval = []
    curr_book = {}
    misc_str = ''
    for b in books:
        full_string = b
        tmp = b.replace('\n', '')
        tmp = re.sub('<a.+?>', '', tmp)
        tmp = re.sub('</a>', '', tmp)
        tmp = re.sub('&amp;', '&', tmp)
        for misc in misc_strings.misc_strings:
            if tmp.find(misc) != -1:
                misc_str = misc
                tmp.replace(misc, '')
        # Find title
        # Another edition?
        edition_re = re.compile('(\d+?)\.((?:laitos|painos)):(.+)')
        m2 = edition_re.search(tmp)
        m = re.search('<b>(.+)<\/b>', tmp, re.S)
        if m2 and curr_book:
            if m2:
                # Found another edition
                book = dict(curr_book)
                if m:
                    book['title'] = m.group(1)
                    tmp = tmp.replace(m.group(0), '')
                book['oldtitle'] = curr_book['title']
                book['origyear'] = curr_book['origyear']
                book['pubseries'] = ''
                book['edition'] = m2.group(1)
                tmp = tmp.replace(m2.group(1) + '.' + m2.group(2) + ':', '')
                bseries = find_item_from_string(bookseries, tmp,
                        bookseries_re)
                if bseries:
                    book['bookseries'] = bseries[1]
                    book['bookseriesnum'] = bseries[2]
                    tmp = tmp.replace(bseries[0], '')
                if 'bookseries' not in book:
                    book['bookseries'] = ''
                    book['bookseriesnum'] = ''

                # Find publisher series
                pseries = find_item_from_string(pubseries, tmp, pubseries_re)
                if pseries:
                    book['pubseries'] = pseries[1]
                    book['pubseriesnum'] = pseries[2]
                    tmp = tmp.replace(pseries[0], '')
                if 'pubseries' not in book:
                    book['pubseries'] = ''
                    book['pubseriesnum'] = ''
                if book['pubseries'] == 'Kuoriaiskirjat':
                    # Publisher series has the same name.
                    book['publisher'] = 'Kuoriaiskirjat'

                publisher = find_item_from_string(publishers, tmp,
                        publishers_re)
                if publisher:
                    book['publisher'] = publisher[1]
                    tmp = tmp.replace(publisher[0], '')
                if 'publisher' not in book:
                    book['publisher'] = ''

                if pseries:
                    if pseries[1] not in pubseries_publisher and book['publisher'] != '':
                        pubseries_publisher[pseries[1]] = book['publisher']

                m2 = re.search('(\d{4})', tmp)
                if m2:
                    book['pubyear'] = m2.group(1)
                    tmp = tmp.replace(m2.group(1), '')
                else:
                    book['pubyear'] = '0'
                # Find translator
                m2 = re.search(translator_re, tmp)
                if m2:
                    book['translator'] = m2.group(3)
                    tmp = tmp.replace(m2.group(0), '')
                else:
                    book['translator'] = ''
                #(to_remove, names) = find_persons(tmp, 'translator')
                #if len(names) > 0:
                #    book['translator'] = ','.join(names)
                #tmp = tmp.replace(to_remove, '')

                m2 = re.search('[Tt]oim\.? ([A-Za-zÅÄÖåäö\-\&\s]+)\.', tmp)
                if m2:
                    book['editor'] = m2.group(1)
                    tmp = tmp.replace('Toim ' + m2.group(1) + '. ', '')
                    tmp = tmp.replace('toim ' + m2.group(1) + '. ', '')
                else:
                    book['editor'] = ''
                if len(re.sub('[\s\.]', '', tmp)) == 0:
                    tmp = ''
                book['rest'] = misc_str + ' ' + tmp.replace(r' .', '').strip()
                misc_str = ''
                book['fullstring'] = full_string
                retval.append(book)
        elif m:
            if 'ks. myös ' in tmp:
                continue
            book = {}
            book['title'] = m.group(1)
            curr_book = book
            book['edition'] = '1'
            rstr = '<b>'+ m.group(1) + '</b>. '
            tmp = tmp.replace(rstr, '')
            # Find type
            m = re.search('\[(.+)\]', tmp)
            if m:
                book['type'] = m.group(1)
                tmp = tmp.replace('[' + m.group(1) + ']', '')
            else:
                book['type'] = ''
            # Find original title (=translation)
            m = re.search('\((.+?)\)', tmp)
            if m:
                # Find if there's also an original publisher year
                m2 = re.search('(.+), (\d{4})', m.group(1))
                if m2:
                    book['origname'] = m2.group(1)
                    book['origyear'] = m2.group(2)
                else:
                    book['origname'] = m.group(1)
                    book['origyear'] =  '0'
                tmp = tmp.replace('(' + m.group(1)  + '). ', '')
            else:
                book['origname'] = ''
                book['origyear'] = None
            # Find editor
            m = re.search('[Tt]oim\.? ([A-Za-zÅÄÖåäö\-\&\s]+)\.', tmp)
            if m:
                book['editor'] = m.group(1)
                tmp = tmp.replace('Toim ' + m.group(1) + '. ', '')
                tmp = tmp.replace('toim ' + m.group(1) + '. ', '')
            else:
                book['editor'] = ''

            # Find book series
            bseries = find_item_from_string(bookseries, tmp, bookseries_re)
            if bseries:
                book['bookseries'] = bseries[1]
                book['bookseriesnum'] = bseries[2]
                tmp = tmp.replace(bseries[0], '')
            if 'bookseries' not in book:
                book['bookseries'] = ''
                book['bookseriesnum'] = ''
            pseries = find_item_from_string(pubseries, tmp, pubseries_re)
            if pseries:
                book['pubseries'] = pseries[1]
                book['pubseriesnum'] = pseries[2]
                tmp = tmp.replace(pseries[0], '')
            if 'pubseries' not in book:
                book['pubseries'] = ''
                book['pubseriesnum'] = ''
            if book['pubseries'] == 'Kuoriaiskirjat':
                book['publisher'] = 'Kuoriaiskirjat'

            # Find publisher
            publisher = find_item_from_string(publishers, tmp,
                publishers_re)
            if publisher:
                book['publisher'] = publisher[1]
                tmp = tmp.replace(publisher[0], '')
            if 'publisher' not in book:
                book['publisher'] = ''
            if pseries:
                if pseries[1] not in pubseries_publisher and book['publisher'] != '':
                    pubseries_publisher[pseries[1]] = book['publisher']

            m = re.search('(\d{4})', tmp)
            if m:
                book['pubyear'] = m.group(1)
                tmp = tmp.replace(m.group(1), '')
            else:
                book['pubyear'] = '0'
            m2 = re.search(translator_re, tmp)
            if m2:
                book['translator'] = m2.group(3)
                tmp = tmp.replace(m2.group(0), '')
            else:
                book['translator'] = ''
            #(to_remove, names) = find_persons(tmp, 'translator')
            #book['translator'] = '&'.join(names)
            #tmp = tmp.replace(to_remove, '')

            if len(re.sub('[\s\.]', '', tmp)) == 0:
                tmp = ''
            book['rest'] = misc_str + ' ' + tmp.replace(r' .', '').strip()
            misc_str = ''
            #if book['rest'] == '.':
            #    book['rest'] = ''
            book['fullstring'] = full_string
            curr_book = dict(book)
            retval.append(book)
    return retval


def read_bibs(filelist):
    """ Return a dict containing contents of the bibliography files
        split """
    content = ''
    for filename in filelist:
        print("Handling {}".format(filename))
        if filename == 'sfbib.htm':
            encoding = 'iso8859-1'
        else:
            encoding = 'windows-1252'
        with open(filename, 'r', encoding='iso8859-1') as fle:
            content += str(fle.read()).replace('&amp;', '&')

    auth_data = content.split('\n\n\n')
    auth_p = r'<h2>([a-zA-ZåäöÄÅÖ].*?)</h2>(.+)'
    authors = {}
    for auth in auth_data:
        m = re.search(auth_p, auth, re.S|re.U)
        if m:
            authors[m.group(1)] = m.group(2).replace('\r\n', '')
    authors = {x[0]: x[1] for x in authors.items() if re.search(r'<b>', x[1], re.S)}
    retval = {}
    for key, author in authors.items():
        retval[key] = get_books(author.split('<br>'))
    return retval


def import_pubs(session, publishers):
    s = session()
    for pub in publishers:
        p = s.query(Publisher).filter(Publisher.name == pub[1]).first()
        if not p:
            publisher = Publisher(name=pub[1], fullname=pub[2])
            s.add(publisher)
    s.commit()


def import_authors(session, authors):
    s = session()
    for name in authors.keys():
        q = s.query(Person).filter(Person.name == name).first()
        if not q:
            author = Person(name=name)
            s.add(author)
    s.commit()


def import_translators(session, translators, source):
    s = session()
    if not translators:
        return
    if translators != '':
        for t in translators.split('&'):
            q = s.query(Person).filter(Person.name ==
                    t.strip()).first()
            if not q:
                translator = Person(name=t.strip(), source=source)
                s.add(translator)
                s.commit()


def import_editors(session, editors):
    pass

def import_bookseries(session, serieslist):
    s = session()
    for series in serieslist:
        q = s.query(Bookseries).filter(Bookseries.name == series[1]).first()
        if not q:
            new_series = Bookseries(name=series[1])
            s.add(new_series)
    s.commit()


def import_pubseries(session, serieslist):
    import pprint
    s = session()
    for series in serieslist:
        q = s.query(Pubseries).filter(Pubseries.name == series[1]).first()
        if not q:
            if series[1] in pubseries_publisher:
                publisher = s.query(Publisher).filter(Publisher.name ==
                        pubseries_publisher[series[1]]).first()
                if publisher:
                    if series[1] in important_pubseries:
                        important = True
                    else:
                        important = False
                    new_series = Pubseries(name=series[1], publisher_id =
                            publisher.id, important=important)
                    s.add(new_series)
    s.commit()


def add_bookperson(s, person, book, type):
    bookperson = s.query(BookPerson).filter(BookPerson.person_id == person.id,
            BookPerson.book_id == book.id).first()
    if not bookperson:
        bookperson = BookPerson(person_id=person.id, book_id=book.id,
                type=type)
        s.add(bookperson)
        s.commit()


def import_books(session, authors):
    s = session()
    for author, books in authors.items():
        print("Author: {}".format(author))
        authoritem = s.query(Person).filter(Person.name == author).first()
        for book in books:
            if not authoritem:
                authoritem = Person(name=author, source = book['fullstring'])
                s.add(authoritem)
                s.commit()
            bookitem = s.query(Book).filter(Book.title == book['title']).first()
            if not bookitem:
                # Find related rows from other tables (Publisher, Bookseries,
                # Pubseries).
                bookseries = None
                if book['bookseries'] != '':
                    bookseries = s.query(Bookseries).filter(Bookseries.name ==
                        book['bookseries']).first()
                if bookseries:
                    bookseriesid = bookseries.id
                else:
                    bookseriesid = None
                bookseriesnum = book['bookseriesnum']
                pubseries = None
                if book['pubseries'] != '':
                    pubseries = s.query(Pubseries).filter(Pubseries.name ==
                        book['pubseries']).first()
                if pubseries:
                    pubseriesid = pubseries.id
                else:
                    pubseriesid = None
                pubseriesnum = book['pubseriesnum']
                publisher = None
                if book['publisher'] != '':
                    publisher = s.query(Publisher).filter(Publisher.name ==
                            book['publisher']).first()
                if publisher:
                    publisherid = publisher.id
                else:
                    publisherid = None
                translator = None
                translator = s.query(Person).filter(Person.name ==
                book['translator']).first()
                if not translator:
                    translator = Person(name=book['translator'], source =
                            book['fullstring'])
                    s.add(translator)
                    s.commit()
                #import_translators(session, book['translator'],
                #book['fullstring'])
                #if book['translator'] != '':
                #    for name in book['translator'].split(','):
                #        translator = s.query(Person).filter(Person.name ==
                #                name).first()
                #        if not translator:
                #            try:
                #                translator = Person(name=name, source = book['fullstring'])
                #                s.add(translator)
                #                s.commit()
                #            except:
                #                print("translator: {}, author {}".format(name,
                #                        author))
                editor = None
                if book['editor'] != '':
                    editor = s.query(Person).filter(Person.name ==
                        book['editor']).first()
                    if not editor:
                        editor = Person(name=book['editor'], source = book['fullstring'])
                        s.add(editor)
                        s.commit()

                # Create new book to database.
                bookitem = Book(title = book['title'],
                    pubyear = book['pubyear'], edition = book['edition'],
                    publisher_id = publisherid,
                    originalname = book['origname'],
                    origpubyear = book['origyear'],
                    pubseries_id = pubseriesid,
                    pubseriesnum = book['pubseriesnum'],
                    bookseries_id = bookseriesid,
                    bookseriesnum = book['bookseriesnum'],
                    genre = book['type'],
                    misc = book['rest'],
                    fullstring = book['fullstring'])
                s.add(bookitem)
                s.commit()

                # Add links between people and book
                add_bookperson(s, authoritem, bookitem, 'A')
                if book['translator'] != '':
                    #for name in book['translator'].split('&'):
                    #    print("Name = {}".format(name))
                    translator = s.query(Person).filter(Person.name == book['translator']).first()
                    add_bookperson(s, translator, bookitem, 'T')
                if book['editor'] != '':
                    editor = s.query(Person).filter(Person.name == book['editor']).first()
                    add_bookperson(s, editor, bookitem, 'E')


def add_missing_series(session):
    # This important publisher series is missing from the imported data.
    s = session()
    publisher = s.query(Publisher).filter(Publisher.name ==
    'Kirjayhtymä').first()
    pubseries = Pubseries(name='Kirjayhtymän science fiction -sarja',
            important=True, publisher_id = publisher.id)
    s.add(pubseries)
    s.commit()


def create_admin(session):
    s = session()
    user = User(name='admin', is_admin=True)
    user.set_password('admin')
    s.add(user)
    s.commit()


def import_all(dirname):
    import glob
    import pprint

    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(basedir, '.env'))

    data = read_bibs(glob.glob(dirname + '/*.html'))

    #pprint.pprint(data)
    #pprint.pprint(pubseries_publisher)

    engine = create_engine(os.environ.get('DATABASE_URL'))
    session = sessionmaker()
    session.configure(bind=engine)
    import_pubs(session, publishers)
    import_bookseries(session, bookseries)
    import_pubseries(session, pubseries)
    import_books(session, data)

    add_missing_series(session)
    create_admin(session)


    #pprint.pprint(pubseries)

if __name__ == '__main__':
    dirname = 'bibfiles'
    import_all(dirname)
    #print(find_persons('Suom U. Ruhanen ja R. Sirokov. Edistys 1968.',
    #    'translator'))
    #print(find_persons('Suom P. Kopperi & J. Linturi & E. Palsbo & M. Rutanen & A. Tiusanen & V. Vankkoja. Omnibus-sarja. Tammi 1964.', 'translator'))
    #print(find_persons('Suom Pentti P. Keränen.', 'translator'))
    #print(find_persons('Suom Pentti Penttinen.', 'translator'))
