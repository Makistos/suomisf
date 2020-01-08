from app.orm_decl import Work, Edition, Part, Person, Author, Translator,\
Editor, Publisher, Pubseries, Bookseries, User, Genre, Alias
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from importbib import publishers
from importbib import bookseries, pubseries, important_pubseries, misc_strings
import re
import os
import sys
from dotenv import load_dotenv
import argparse
import logging
import re

publishers_re = {}
bookseries_re = {}
pubseries_re = {}
for pub in publishers:
    publishers_re[pub[0]] = re.compile('(' + pub[0] + ')[\.\s]')
for series in pubseries:
    pubseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX\d]+)?')
for series in bookseries:
    bookseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX\d]+)?\s?')
translator_re = re.compile("([a-zA-ZåäöÅÄÖ]+\s)*([Ss]uom\.?\s)([A-ZÄÅÖ]+[\.\s]?[a-zA-ZäöåÅÄÖéü&\-]*[\.\s]?[a-zA-ZåäöÅÄÖéü&\-\s,]*)(\.)")
translator_re2 = re.compile("([Ss]uom\.?\s)?([A-ZÄÅÖ](\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü\-]+)\s?([A-ZÄÅÖ](\.\s?[A-ZÅÄÖ][a-zåäö]*|[a-zåäöü]+))*\s*([A-ZÅÄÖ](\.\s?[A-ZÄÅÖ][a-zåäö]*|[a-zäöåü]+)*)*\s?([A-ZÅÄÖa-zåäöü]+)*(\.)*)")
translator_re3 = re.compile("([A-ZÄÅÖ]+[\.\s]?[a-zA-ZäöåÅÄÖéü&\-]*[\.\s]?[a-zA-ZåäöÅÄÖéü&\-\s]*)")


pubseries_publisher = {}

genres_list = {'F' : 'F',
          'K' : 'K',
          'Paleof' : 'Paleof',
          'paleof' : 'Paleof',
          'PF' : 'PF',
          'SF' : 'SF',
          'VEH' : 'VEH',
          'utopia' : 'utopia',
          'nF' : 'nF',
          'nSF' : 'nSF',
          'nSf' : 'nSF',
          'nK' : 'nH',
          'lasten SF' : 'lSF',
          'satu' : 'satu',
          'ei-sf' : 'eiSF',
          'eiSF' : 'eiSF',
          'eisf' : 'eiSF',
          'rajatap' : 'rajatapaus'
          }

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
        s = ''
        num = ''
        m = patterns[item[0]].search(st)
        if m:
            # Add all matches to a list. Item contains the entire
            # match and cleaned up name of the item.
            if 'num2' in m.groupdict():
                num = m.groupdict()['num2']
            else:
                if 'num' in m.groupdict():
                    if m.groupdict()['num'] != '.':
                        num = m.groupdict()['num']
                    else:
                        num = ''
                else:
                    num = ''
            if 'ext' in m.groupdict():
                if m.groupdict()['ext'] != None:
                    s = item[1] + ' ' + m.groupdict()['ext']
                else:
                    s = item[1]
            else:
                s = item[1]
            match_list.append((m.group(0), s, num))
    if len(match_list) > 0:
        maxlen = 0
        # Search for the longest matching string
        for item in match_list:
            if len(item[0]) > maxlen:
                maxlen = len(item[0])
                retval = item
    return retval


def get_books(books):
    """ This is so ugly it hurts my head.

        General idea is to pick out parts of the book info more or less from
        the easiest or most distinguisable one to the more difficult ones and
        removing each identified part so the string left gets shorter and
        shorter. There is a wide variety of different formats so this is the
        only way I could get this to work.

        This function returns a list of tuples where the first item is the
        work and the second is a list of editions for that work. E.g.
        (({work1}, [edition1, edition2...]),
         ({work2}, [edition1, edition2...]), ...
        )
        Every work has at least one edition, with exactly the same info as the
        work itself. This is considered first edition for that work.
    """


    works = []
    editions = []
    curr_book = {}
    misc_str = ''
    edition_re = re.compile('(\d+?)\.((?:laitos|painos)):(.+)')
    for b in books:
        full_string = b
        tmp_misc = ''
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
                    try:
                        book['bookseriesorder'] = int(bseries[2])
                    except:
                        book['bookseriesorder'] = 0
                    tmp = tmp.replace(bseries[0], '')
                if 'bookseries' not in book:
                    book['bookseries'] = ''
                    book['bookseriesnum'] = ''
                    book['bookseriesorder'] = 0

                # Find publisher series
                pseries = find_item_from_string(pubseries, tmp, pubseries_re)
                if pseries:
                    book['pubseries'] = pseries[1]
                    book['pubseriesnum'] = pseries[2]
                    tmp = tmp.replace(pseries[0], '')
                if 'pubseries' not in book:
                    book['pubseries'] = ''
                    if book['collection'] == False:
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
                    book['pubyear'] = None
                # Find translator
                m2 = re.search(translator_re, tmp)
                if m2:
                    book['translator'] = m2.group(3)
                    tmp = tmp.replace(m2.group(0), '')
                else:
                    book['translator'] = ''

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
                #print("Adding: {}".format(book['title']))
                # Adding to editions for this work
                works[-1][1].append(book)
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
            book['collection'] = False
            if m:
                genre = m.group(1)
                m2 = re.search('(\d\/\d+)', genre)
                if m2:
                    genre = genre.replace(m2.group(0), '')
                if genre.find('kok'):
                    book['collection'] = True
                    if genre != 'esseekokoelma':
                        genre.replace('kok', '')
                if m2:
                    misc_str += ' ' + m2.group(0) + ' '
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
                book['origname'] = book['title']
                book['origyear'] = '0'
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
                if book['origyear'] == '0':
                    book['origyear'] = book['pubyear']
            else:
                book['pubyear'] = None

            m2 = re.search(translator_re, tmp)
            if m2:
                book['translator'] = m2.group(3)
                tmp = tmp.replace(m2.group(0), '')
            else:
                book['translator'] = ''

            if len(re.sub('[\s\.]', '', tmp)) == 0:
                tmp = ''
            book['rest'] = misc_str + ' ' + tmp.replace(r' .', '').strip()
            misc_str = ''
            book['fullstring'] = full_string
            curr_book = dict(book)
            # Add work and default first edition
            works.append((book, [book]))
    return works


def read_bibs(filelist):
    """ Return a dict containing contents of the bibliography files
        with author name as key and list of books returned from
        get_books() for that author.
    """
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
    # Create a dict with author's name as key and books as item
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
    """ Import publishers  to database. """
    logging.info('Importing publishers')
    s = session()
    for pub in publishers:
        logging.debug("Pub1: %s",pub[1])
        p = s.query(Publisher).filter(Publisher.name == pub[1]).first()
        if not p:
            publisher = Publisher(name=pub[1], fullname=pub[2])
            s.add(publisher)
    s.commit()


def import_bookseries(session, serieslist):
    """ Import bookseries to database. """
    logging.info('Importing bookseries')
    s = session()
    for series in serieslist:
        q = s.query(Bookseries).filter(Bookseries.name == series[1]).first()
        if not q:
            new_series = Bookseries(name=series[1])
            s.add(new_series)
    s.commit()


def import_pubseries(session, serieslist):
    """ Import publisher series to database. """
    logging.info('Importing publisher series')
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
    """ Add a "bookperson". A person is either author, translator or
        editor. Authors link to work, the other two to editions.

        This function will check if that connection already exists
        to avoid adding double entries. This should really never happen.
    """
    if type == 'A':
        bookperson = s.query(Author).filter(Author.person_id == person.id,
                Author.part_id == book.id).first()
        if not bookperson:
            logging.debug('Adding author %s for %s.',person.name, book.title)
            bookperson = Author(person_id = person.id, part_id = book.id)
    elif type == 'T':
        bookperson = s.query(Translator).filter(Translator.person_id ==
                person.id, Translator.part_id == book.id).first()
        if not bookperson:
            logging.debug('Adding translator %s for %s.', person.name, book.title)
            bookperson = Translator(person_id = person.id, part_id = book.id)
    elif type == 'E':
        bookperson = s.query(Editor).filter(Editor.person_id ==
                person.id, Editor.edition_id == book.id).first()
        if not bookperson:
            logging.debug('Adding editor %s for %s.', person.name, book.title)
            bookperson = Editor(person_id = person.id, edition_id = book.id)
    else:
        return

    s.add(bookperson)
    s.commit()


def import_authors(s, names, source=''):
    """ Imports an author line (found within <h2> tags).
        There are several different variations, including more than
        one author and some or all information missing except for name.
        Information gathered for each author:
        - Full name,
        - First name(s),
        - Last name,
        - Possible alias with full name & first & last names,
        - Nationality,
        - Year of birth,
        - Year of death.
    """
    persons = []
    names = re.sub(r'\n', ' ', names.strip())
    for tmp_name in names.split('&'):
        name = None
        first_name = None
        last_name = None
        real_name = None
        real_first_name = None
        real_last_name = None
        dob = None
        dod = None
        country = None
        if '(toim.)' in tmp_name:
            tmp_name = re.sub(r'\(toim.\)', '', tmp_name)
        if '(' in tmp_name:
            m = re.search(r'(.+)\((.+[^\)])\)?', tmp_name)
            if m:
                if '(oik.' in m.group(1): # This is a pseudonym
                    m3 = re.search(r'(?P<alias>.+)\s\(oik.\s(?P<realname>.+)\)', m.group(1))
                    if m3:
                        real_name = m3.group('realname')
                        real_names = real_name.split(' ')
                        real_first_name = ' '.join(real_names[0:-1]).strip()
                        real_last_name = str(real_names[-1]).strip()
                        real_name = real_last_name + ", " + real_first_name
                        name = m3.group('alias')
                        names = name.split(', ')
                        last_name = names[0].strip()
                        if len(names) > 1:
                            first_name = names[1].strip()
                            name = last_name + ", " + first_name
                        else:
                            name = last_name

                else: # Real name
                    m3 = re.search(r'(?P<alias>.+)', m.group(1))
                    name = m3.group('alias')
                    names = m3.group('alias').split(', ')
                    last_name = names[0].strip()
                    if len(names) > 1:
                        first_name = names[1].strip()
                        name = last_name + ", " + first_name
                    else:
                        name = last_name
                    real_name = None
                    real_first_name = None
                    real_last_name = None
                if m3:
                    m2 = re.search(r'(?P<country>[\w\-]+)(,\s)?(?P<dob>\d+)?-?(?P<dod>\d+)?', m.group(2))
                    if m2:
                        country = m2.group('country')
                        dob = m2.group('dob')
                        dod = m2.group('dod')
                else:
                    country = None
                    dob = None
                    dod = None
        else: # Just a name
            names = tmp_name.split(', ')
            name = tmp_name
            last_name = names[0].strip()
            if len(names) > 1: # More than one part in name
                first_name = names[1].strip()
                name = last_name + ", " + first_name
            else:
                first_name = None
                name = last_name
            country = None
            dob = None
            dod = None
            real_name = None
            real_first_name = None
            real_last_name = None
        if real_name is not None:
            person = s.query(Person)\
                      .filter(Person.name==real_name)\
                      .first()
            if not person:
                person = Person(name=real_name.strip(),
                                first_name=real_first_name,
                                last_name=real_last_name,
                                birthplace=country,
                                dob=dob,
                                dod=dod)
                s.add(person)
                s.commit()
            person2 = s.query(Person)\
                       .filter(Person.name==name)\
                       .first()
            if not person2:
                person2=Person(name=name.strip(),
                               first_name=first_name,
                               last_name=last_name)
                s.add(person2)
                s.commit()
                # Only add the pseudonym to the list as that's the
                # author under which it is placed.
            alias = s.query(Alias)\
                     .filter(Alias.realname==person.id,
                             Alias.alias==person2.id)\
                     .first()
            if not alias:
                alias = Alias(realname=person.id, alias=person2.id)
                s.add(alias)
                s.commit()
            persons.append(person2)
        else:
            person = s.query(Person)\
                      .filter(Person.name==name)\
                      .first()
            if not person:
                person = Person(name=name,
                                first_name=first_name,
                                last_name=last_name,
                                birthplace=country,
                                dob=dob,
                                dod=dod)
                s.add(person)
                s.commit()
            persons.append(person)
    return persons


def import_persons(s, name, source=''):
    """ Searches for given person by name from the Person table and if
        that name is not found, adds it to the Person table.

        The person object, whether already existing or just created, is
        returned to caller.
    """
    persons = []
    for p in name.split('&'):
        p = re.sub(r'\n', '', p.strip())
        p = re.sub(r'\([^()]*\)', '', p)
        names = p.split(' ')
        first_name = ' '.join(names[0:-1]).strip()
        last_name = str(names[-1]).strip()
        name_inv = last_name + ", " + first_name
        person = s.query(Person).filter(Person.name==name_inv).first()
        if not person:
            person = Person(name=name_inv, fullstring=source, first_name=first_name,
                    last_name=last_name)
            s.add(person)
            s.commit()
        persons.append(person)
    return persons


def import_books(session, authors):
    logging.info('Importing books')
    s = session()
    for author, books in authors.items():
        print("Author: {}".format(author)) # Progress meter
        logging.debug('Author: %s', author)
        authorlist = import_authors(s, author, author)
        for book in books:
            # Each book has a dict for the work and one or more dicts for
            # editions.
            work = book[0]
            # Find related rows from other tables (Publisher, Bookseries,
            # Pubseries).
            bookseries = None
            if work['bookseries'] != '':
                bookseries = s.query(Bookseries).filter(Bookseries.name ==
                    work['bookseries']).first()
            if bookseries:
                bookseriesid = bookseries.id
            else:
                bookseriesid = None

            workitem = Work(
                    title = work['origname'],
                    pubyear = work['origyear'],
                    language = '',
                    bookseries_id = bookseriesid,
                    bookseriesnum = work['bookseriesnum'],
                    misc = work['rest'],
                    collection=work['collection'],
                    fullstring = work['fullstring'])

            s.add(workitem)
            s.commit()

            save_genres(session, workitem.id, work['type'])

            for edition in book[1]:
                pubseries = None
                if edition['pubseries'] != '':
                    pubseries = s.query(Pubseries).filter(Pubseries.name ==
                        edition['pubseries']).first()
                if pubseries:
                    pubseriesid = pubseries.id
                else:
                    pubseriesid = None
                pubseriesnum = edition['pubseriesnum']
                publisher = None
                if edition['publisher'] != '':
                    publisher = s.query(Publisher).filter(Publisher.name ==
                            edition['publisher']).first()
                if publisher:
                    publisherid = publisher.id
                else:
                    publisherid = None
                translator = import_persons(s, edition['translator'], edition['fullstring'])
                editor = import_persons(s, edition['editor'], edition['fullstring'])

                # Create new edition to database.
                if edition['edition']:
                    editionnum = str(edition['edition'])
                else:
                    editionnum = '1'
                logging.debug("Adding edition {} for {} ({})."\
                        .format(editionnum,
                                workitem.title,
                                edition['title']))
                ed = Edition(
                        title = edition['title'],
                        pubyear = edition['pubyear'],
                        language = 'FI', # Every book in these files is in Finnish
                        publisher_id = publisherid,
                        editionnum = editionnum,
                        isbn = '', # No ISBNs in the data
                        pubseries_id = pubseriesid,
                        pubseriesnum = edition['pubseriesnum'],
                        misc = edition['rest'],
                        fullstring = edition['fullstring'])
                s.add(ed)
                s.commit()

                part = Part(
                        edition_id = ed.id,
                        work_id = workitem.id,
                        shortstory_id = None,
                        title = ed.title)

                s.add(part)
                s.commit()

                # Add links between people and edition
                for authoritem in authorlist:
                    if '(toim.)' in author:
                        add_bookperson(s, authoritem, ed, 'E')
                    else:
                        add_bookperson(s, authoritem, part, 'A')
                if edition['translator'] != '' and len(translator)>0:
                    add_bookperson(s, translator[0], part, 'T')
                if edition['editor'] != '' and len(editor)>0:
                    add_bookperson(s, editor[0], ed, 'E')


def save_genres(session, workid, genrelist):

    s = session()

    genrelist.replace('/', ',')
    for genre in genrelist.split(','):
        if genre in genres_list:
            genreobj = Genre(workid=workid, genre_name=genres_list[genre])
            s.add(genreobj)
    s.commit()

def update_creators(session):
    """ Update the owner string for every work. This is used
        to group books together and is needed because combining
        authors and editors for books with multiple creators would
        be very complex otherwise. """

    logging.info('Updating creator strings')
    print('Updating creator strings...')
    s = session()
    works = s.query(Work).all()

    i = 0
    for work in works:
        authors = s.query(Person)\
                   .join(Author)\
                   .filter(Person.id == Author.person_id)\
                   .join(Part)\
                   .filter(Part.id == Author.part_id)\
                   .filter(Part.work_id == work.id)\
                   .all()
        if authors:
            author_list = ' & '.join([x.name for x in authors])
            work.creator_str = author_list
        else:
            editors = s.query(Person)\
                       .join(Editor)\
                       .filter(Person.id == Editor.person_id)\
                       .join(Edition)\
                       .filter(Edition.id == Editor.edition_id)\
                       .join(Part)\
                       .filter(Part.edition_id == Edition.id,
                               Part.work_id == work.id)\
                       .all()
            if editors:
                editor_list = ' & '.join([x.name for x in editors])
                work.creator_str = editor_list + ' (toim.)'

        s.add(work)
        s.commit()
        if i % 100 == 0:
            print('.', end='', flush=True)
        i += 1
    print()



def add_missing_series(session):
    # This important publisher series is missing from the imported data.
    logging.info('Creating missing Kirjayhtymä series')
    s = session()
    publisher = s.query(Publisher).filter(Publisher.name ==
    'Kirjayhtymä').first()
    pubseries = Pubseries(name='Kirjayhtymän science fiction -sarja',
            important=True, publisher_id = publisher.id)
    s.add(pubseries)
    s.commit()


def create_admin(session):
    logging.info('Creating admin')
    s = session()
    user = User(name='admin', is_admin=True)
    user.set_password('admin')
    s.add(user)
    s.commit()


def import_all(filelist):
    import glob
    import pprint

    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(basedir, '.env'))

    logging.info('Starting import')
    data = read_bibs(filelist)

    logging.debug(data)
    #pprint.pprint(data)
    #pprint.pprint(pubseries_publisher)

    db_url = os.environ.get('DATABASE_URL') or \
            'sqlite:///suomisf.db'

    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)
    import_pubs(session, publishers)
    import_bookseries(session, bookseries)
    import_pubseries(session, pubseries)
    import_books(session, data)
    update_creators(session)

    add_missing_series(session)
    create_admin(session)


def import_stories(filename):
    logging.info('Importing short stories')

    content = ''

    with open(filename, 'r', encoding='iso8859-1') as fle:
        content += str(fle.read()).replace('&amp;', '&')

    id_str = '\[[A-Z]{1}[a-z]{2}:\w{2}\]'
    id_re = re.compile(id_str)
    book_re = re.compile(id_str + '\s=\s(?P<author>.+)\s:\s(?P<title>'))
    data = content.split('\n')

    for line in data:
        if id_re.match(line):
            print(line)



    # Build dict


def read_params(args):
    p = argparse.ArgumentParser()
    p.add_argument('--debug', '-d', action='store_true', default=False)
    p.add_argument('--file', '-f', default='')
    p.add_argument('--stories', '-s', action='store_true', default=False)

    return vars(p.parse_args(args))


if __name__ == '__main__':
    import glob
    params = read_params(sys.argv[1:])
    loglevel = logging.INFO
    if params['debug'] == True:
        loglevel = logging.DEBUG
    logging.basicConfig(filename='import.log', filemode='w',
        level=loglevel)
    if params['file']:
        filelist = [params['file']]
        print(filelist)
    elif params['stories']:
        filename = 'bibfiles/sf_nov_u.txt'
        import_stories(filename)
    else:
        filelist = glob.glob('bibfiles/*.html')
        import_all(filelist)

