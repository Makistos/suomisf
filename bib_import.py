# -*- coding: utf-8 -*-
from app.orm_decl import Work, Edition, Part, Person, Author, Translator,\
Editor, Publisher, Pubseries, Bookseries, User, Genre, Alias
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from importbib import publishers
from importbib import bookseries, pubseries, important_pubseries, misc_strings, translators, editors
import re
import os
import sys
from dotenv import load_dotenv
import argparse
import logging
import re
from typing import Tuple, Dict, List, Pattern, Optional
import cProfile

publishers_re = {}
bookseries_re = {}
pubseries_re = {}
for pub in publishers:
    publishers_re[pub[0]] = re.compile('(' + pub[0] + ')[\.\s]')
for series in pubseries:
    pubseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX:\d]+)?')
for series in bookseries:
    bookseries_re[series[0]] = re.compile('(?P<name>' + series[0] + ')\s?(?P<num>[\#IVX\d]+)?\s?')
translator_re = re.compile("([a-zA-ZåäöÅÄÖ]+\s)*([Ss]uom\.?\s+)([A-ZÄÅÖ]+[\.\s]?[a-zA-ZäöåÅÄÖéüõ&\-]*[\.\s]?[a-zA-ZåäöÅÄÖéüõ&\-\s,]*)(\.)")

pubseries_publisher = {}

genres_list = {'F' : 'F',
          'K' : 'K',
          'Paleof' : 'paleof',
          'paleof' : 'paleof',
          'PF' : 'PF',
          'SF' : 'SF',
          'VEH' : 'VEH',
          'utopia' : 'utopia',
          'nF' : 'nF',
          'nSF' : 'nSF',
          'nSf' : 'nSF',
          'nK' : 'nK',
          'lasten SF' : 'lSF',
          'satu' : 'satu',
          'ei-sf' : 'eiSF',
          'eiSF' : 'eiSF',
          'eisf' : 'eiSF',
          'rajatap' : 'rajatap',
          'lasten kuvakirja' : 'lasten kuvakirja',
          'kok' : 'kok',
          'kok ' : 'kok',
          'Kok' : 'kok'
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


def find_translators(s: str) -> Tuple[str, str]:
    result: str = ''
    res_tmp: str = ''
    for person in translators:
        # Find the names that are hard to match
        if re.search(person[0], s):
            res_tmp += person[1] + ' ' + person[2] + ','
            repl = person[0]
            s = re.sub(repl, '', s)
    s = ','.join([x for x in s.split(',') if x.strip() != '']) # Remove empty slots
    m2 = re.search(translator_re, s)
    if m2:
        result = m2.group(3)
        s = s.replace(m2.group(0), '')
    else:
        result = ''
        if res_tmp:
            if res_tmp[-1] == ',' or res_tmp[-1] == '&':
                res_tmp = res_tmp[0:-1]
    result = res_tmp + result
    # Fix some odds and ends. These will otherwise generate
    # ghosts.
    if len(result) > 0:
        result = result.strip()
        if result[-1] == '&':
            result = result[0:-1]
        result = result.strip()
        if result[-1] == ',':
            result = result[0:-1]
    #s = re.sub(' +', ' ', s)
    return (result, s)


def find_editors(s: str) -> Tuple[str, str]:
    result: str = ''
    res_tmp: str = ''
    for person in editors:
        if re.search(person[0], s):
            res_tmp += person[1] + ' ' + person[2] + ', '
            s = s.replace(person[0], '')
    m2 = re.search('[Tt]oim\.? ([A-Za-zÅÄÖåäö\-\&\s]+)\.', s)
    if m2:
        result = m2.group(1)
        s = s.replace('Toim ' + m2.group(1) + '. ', '')
        s = s.replace('toim ' + m2.group(1) + '. ', '')
    else:
        result = ''
    result = res_tmp + result

    return (result, s)


def find_series(s: str, is_coll: bool, series_list: List, series_re: Dict[str, Pattern[str]]) -> Tuple[str, str, str]:
    retval_name: str = ''
    retval_num: str = ''

    pseries = find_item_from_string(series_list, s, series_re)
    if pseries:
        retval_name = pseries[1]
        retval_num = pseries[2]
        s = s.replace(pseries[0], '')
    if retval_name == '' and is_coll:
        retval_num = ''

    return (retval_name, retval_num, s)


def find_publisher(s: str) -> Tuple[str, str]:
    pub_name = ''

    publisher = find_item_from_string(publishers, s,
        publishers_re)
    if publisher:
        pub_name = publisher[1]
        s = s.replace(publisher[0], '')

    return (pub_name, s)

roman_numbers: Dict = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
                       'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
                       'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
                       'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20,
                       'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24, 'XXV': 25}

ordered_numbers: Dict = {'ensimmäinen': 1,
                         'toinen': 2,
                         'kolmas': 3,
                         'neljäs': 4,
                         'viides': 5,
                         'kuudes': 6,
                         'seitsemäs': 7,
                         'kahdeksas': 8,
                         'yhdeksäs': 9,
                         'kymmenes': 10}

def seriesnum_to_int(str_num: str):
    if str_num is None:
        return None

    if str_num == '':
        return None

    try:
        return int(str_num)
    except Exception as e:
        pass

    if str_num in roman_numbers:
        return roman_numbers[str_num]

    if str_num.lower() in ordered_numbers:
        return ordered_numbers[str_num.lower()]

    if str_num.startswith('#'):
        try:
            return int(str_num[1:])
        except Exception as e:
            print(f'Failed to convert book number: {str_num}')

    if ':' in str_num:
        return str_num.split(':')[0]

    print(f'Book number not found: {str_num}')
    return None


def find_commons(s: str, book: Dict) -> str:
    # Find publisher series
    (book['pubseries'], pubseriesnum, s) = \
            find_series(s, book['collection'], pubseries, pubseries_re)

    book['pubseriesnum'] = seriesnum_to_int(pubseriesnum)
    (book['publisher'], s) = find_publisher(s)

    if book['pubseries'] != '':
        if book['pubseries'] not in pubseries_publisher and book['publisher'] != '':
            pubseries_publisher[book['pubseries']] = book['publisher']

    (book['bookseries'], book['bookseriesnum'], s) = \
            find_series(s, book['collection'], bookseries, bookseries_re)

    book['bookseriesorder'] = seriesnum_to_int(book['bookseriesnum'])

    if book['bookseries'] == '':
        book['bookseriesorder'] = 0

    # Find translator
    (book['translator'], s) = find_translators(s)

    # Find editors
    (book['editor'], s) = find_editors(s)

    return s


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
        tmp_e = ''
        tmp_t = ''
        # Many of the lines are split in the middle of a data item.
        # Fix this by replacing the newline character with a space
        # and the truncating any extra spaces.
        tmp = b.replace('\n', ' ')
        tmp = ' '.join(tmp.split())
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
                if '-- ks.' in tmp:
                    continue
                # Found another edition
                book = dict(curr_book)
                if m:
                    book['title'] = m.group(1)
                    tmp = tmp.replace(m.group(0), '')
                book['oldtitle'] = curr_book['title']
                book['origyear'] = curr_book['origyear']
                book['translation'] = curr_book['translation']
                book['collection'] = curr_book['collection']
                book['edition'] = m2.group(1)
                tmp = tmp.replace(m2.group(1) + '.' + m2.group(2) + ':', '')

                tmp = find_commons(tmp, book)

                m2 = re.search('\d{4}', tmp)
                if m2:
                    book['pubyear'] = m2.group(0)
                    tmp = tmp.replace(m2.group(0), '')
                else:
                    book['pubyear'] = None

                if len(re.sub('[\s\.]', '', tmp)) == 0:
                    tmp = ''
                book['rest'] = misc_str + ' ' + tmp.replace(r' .', '').strip()
                misc_str = ''
                book['fullstring'] = full_string
                # Adding to editions for this work
                works[-1][1].append(book)
        elif m:
            if 'ks. myös ' in tmp or '-- ks.' in tmp:
                continue
            book = {}
            book['title'] = m.group(1)
            curr_book = book
            book['edition'] = '1'
            rstr = '<b>'+ m.group(1) + '</b>'
            tmp = tmp.replace(rstr, '')
            # Find type
            m = re.search('\[(.+)\]', tmp)
            book['collection'] = False
            book['coll_info'] = ''
            if m:
                genre = m.group(1)
                if genre.find('kok') != -1 or genre.find('Kok') != -1:
                    book['collection'] = True
                m2 = re.search('(.+)\s(\d+\/\d+)', genre)
                if m2:
                    book['coll_info'] = m2.group(2)
                book['type'] = m.group(1)
                tmp = tmp.replace('[' + m.group(1) + ']', '')
            else:
                book['type'] = ''
            # Find original title (=translation)
            m = re.search('\((.+?)\)', tmp)
            if m:
                # Find if there's also an original publisher year
                m2 = re.search('(.+),\s*(\d{4})', m.group(1))
                if m2:
                    book['origname'] = m2.group(1)
                    book['origyear'] = m2.group(2)
                    book['translation'] = True
                else:
                    book['origname'] = m.group(1)
                    book['origyear'] =  '0'
                    book['translation'] = True
                tmp = tmp.replace('(' + m.group(1)  + '). ', '')
            else:
                book['origname'] = book['title']
                book['origyear'] = '0'
                book['translation'] = False

            tmp = find_commons(tmp, book)

            m = re.search('(\d{4})', tmp)
            if m:
                book['pubyear'] = m.group(1)
                tmp = tmp.replace(m.group(1), '')
                if book['origyear'] == '0':
                    book['origyear'] = book['pubyear']
            else:
                book['pubyear'] = None

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
        with open(filename, 'r', encoding='ISO-8859-1') as fle:
            content += fle.read().replace('&amp;', '&')

    #content = content.decode('iso-8859-1').encode('utf-8').replace('&amp;', '&')
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
    tmp_name: str = ''
    for tmp_name in names.split('&'):
        # This requires each person to be separeted
        # by an ampersand and each section like this
        # to include all the relevant info, e.g.
        # real name, pseudonym, dob etc.
        name = None
        alt_name = None
        first_name = None
        last_name = None
        real_name = None
        real_first_name = None
        real_last_name = None
        pseudo_name = None
        dob = None
        dod = None
        country = None
        is_pseudo = False
        if '(toim.)' in tmp_name:
            tmp_name = re.sub(r'\(toim.\)', '', tmp_name)
        if '(' in tmp_name:
            m = re.search(r'(.+)\((.+[^\)])\)?', tmp_name)
            if m:
                if 'Bachman, Richard' in tmp_name:
                    # Getting to complex to make this name work
                    real_first_name = 'Stephen (Edwin)'
                    real_last_name = 'King'
                    real_name = 'King, Stephen (Edwin)'
                    alt_name = 'Stephen (Edwin) King'
                    name = 'Bachman, Richard'
                    last_name = 'Bachman'
                    first_name = 'Richard'
                    pseudo_name = 'Richard Bachman'
                    is_pseudo = True
                else:
                    if 'oik.' in m.group(1): # This is a pseudonym
                        m3 = re.search(r'(?P<alias>.+)\s\(oik.\s(?P<realname>.+)\)', m.group(1))
                        is_pseudo = True
                    elif 'oik.' in m.group(2):
                        m3 = re.search(r'(?P<alias>.+)\s\(oik.\s(?P<realname>.+)\)',
                                m.group(0))
                        is_pseudo = True
                    if is_pseudo and pseudo_name == None:
                        try:
                            real_name = m3.group('realname')
                        except Exception as e:
                            print(e)
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
                            alt_name = real_first_name + ' ' + real_last_name
                            pseudo_name = first_name + ' ' + last_name
                        else:
                            name = last_name
                            alt_name = real_first_name + ' ' + real_last_name
                            pseudo_name = last_name

                    else: # Real name
                        m3 = re.search(r'(?P<alias>.+)', m.group(1))
                        name = m3.group('alias').strip()
                        names = m3.group('alias').split(', ')
                        last_name = names[0].strip()
                        if len(names) > 1:
                            first_name = names[1].strip()
                            name = last_name + ", " + first_name
                            alt_name = first_name + ' ' + last_name
                        else:
                            name = last_name
                            alt_name = last_name
                        real_name = None
                        real_first_name = None
                        real_last_name = None
                    if m3 and not is_pseudo:
                        m2 = re.search(r'(?P<country>[\w\-]+)(,\s)?(?P<dob>\d+)?-?(?P<dod>\d+)?', m.group(2))
                        if m2:
                            country = m2.group('country')
                            dob = m2.group('dob')
                            dod = m2.group('dod')
                    elif m3 and is_pseudo:
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
                alt_name = first_name + ' ' + last_name
            else:
                first_name = None
                name = last_name
                alt_name = name
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
                                alt_name=alt_name,
                                first_name=real_first_name,
                                last_name=real_last_name,
                                birthplace=country,
                                dob=dob,
                                dod=dod)
            else:
                if not person.birthplace:
                    person.birthplace = country
                if not person.dob:
                    person.dob = dob
                if not person.dod:
                    person.dod = dod
            s.add(person)
            s.commit()
            persons.append(person)
            person2 = s.query(Person)\
                       .filter(Person.name==name)\
                       .first()
            if not person2:
                person2=Person(name=name.strip(),
                               alt_name=pseudo_name,
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
                                alt_name=alt_name,
                                first_name=first_name,
                                last_name=last_name,
                                birthplace=country,
                                dob=dob,
                                dod=dod)
            else:
                if not person.birthplace:
                    person.birthplace = country
                if not person.dob:
                    person.dob = dob
                if not person.dod:
                    person.dod = dod
            s.add(person)
            s.commit()

            persons.append(person)
    return persons


def import_persons(s, name: str, source: str='') -> List:
    """ Searches for given person by name from the Person table and if
        that name is not found, adds it to the Person table.

        The person object, whether already existing or just created, is
        returned to caller.
    """
    persons = []
    name = name.strip()
    name = name.replace(',', '&')
    name = name.replace(' ja ', '&')

    if name == '' or name == '&':
        return []
    for p in name.split('&'):
        p = re.sub(r'\n', '', p.strip())
        p = re.sub(r'\([^()]*\)', '', p)
        names = p.split(' ')
        # If p only included a single comma names will have
        # two empty strings.
        if len(names) > 1:
            if len(names[0]) == 0 and len(names[1]) == 0:
                continue
        first_name = ' '.join(names[0:-1]).strip()
        last_name = str(names[-1]).strip()
        name_inv = last_name + ", " + first_name
        alt_name = first_name + ' ' + last_name
        person = s.query(Person).filter(Person.name==name_inv).first()
        if not person:
            person = Person(name=name_inv, fullstring=source, first_name=first_name,
                    last_name=last_name, alt_name=alt_name.strip())
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
            is_new = False
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

            # Works are matched with title and pubyear.
            # So yeah, pubyear is the one thing that can't be
            # fixed with this.
            workitem = s.query(Work)\
                        .filter(Work.title == work['origname'],
                                Work.pubyear == work['origyear'])\
                        .first()
            if workitem:
                workitem.bookseries_id = bookseriesid
                workitem.bookseriesnum = work['bookseriesnum']
                workitem.bookseriesorder = work['bookseriesorder']
                workitem.misc = work['rest']
                workitem.collection = work['collection']
                workitem.fullstring = work['fullstring']
            else:
                workitem = Work(
                        title = work['origname'],
                        pubyear = work['origyear'],
                        language = '',
                        bookseries_id = bookseriesid,
                        bookseriesnum = work['bookseriesnum'],
                        bookseriesorder = work['bookseriesorder'],
                        misc = work['rest'],
                        collection=work['collection'],
                        fullstring = work['fullstring'])
                is_new = True

            s.add(workitem)
            s.commit()

            save_genres(session, workitem.id, work['type'])

            for edition in book[1]:
                pubseries = None
                if edition['pubseries'] != '':
                    pubseries = s.query(Pubseries)\
                                 .filter(Pubseries.name == edition['pubseries'])\
                                 .first()
                if pubseries:
                    pubseriesid = pubseries.id
                else:
                    pubseriesid = None
                if edition['pubseriesnum']:
                    try:
                        pubseriesnum = int(edition['pubseriesnum'])
                    except Exception as e:
                        print(f'Failed to convert pubseriesnum: {edition["pubseriesnum"]}')
                else:
                    pubseriesnum = None
                publisher = None
                if edition['publisher'] != '':
                    publisher = s.query(Publisher).filter(Publisher.name ==
                            edition['publisher']).first()
                if publisher:
                    publisherid = publisher.id
                else:
                    publisherid = None
                translators = import_persons(s, edition['translator'], edition['fullstring'])
                editors = import_persons(s, edition['editor'], edition['fullstring'])

                # Create new edition to database.
                if edition['edition']:
                    editionnum = str(edition['edition'])
                else:
                    editionnum = '1'
                logging.debug("Adding edition {} for {} ({})."\
                        .format(editionnum,
                                workitem.title,
                                edition['title']))

                # Editions are matched by title, pubyear and publisher.
                # So these three cannot be changed properly.
                ed = s.query(Edition)\
                      .filter(Edition.title == edition['title'],
                              Edition.pubyear == edition['pubyear'],
                              Edition.publisher_id == publisherid)\
                      .first()
                if ed:
                    ed.translation = edition['translation']
                    ed.editionnum = editionnum
                    ed.pubseries_id = pubseriesid
                    ed.pubseriesnum = pubseriesnum
                    ed.coll_info = edition['coll_info']
                    ed.misc = edition['rest']
                    ed.fullstring = edition['fullstring']
                else:
                    ed = Edition(
                            title = edition['title'],
                            pubyear = edition['pubyear'],
                            translation = edition['translation'],
                            language = 'FI', # Every book in these files is in Finnish
                            publisher_id = publisherid,
                            editionnum = editionnum,
                            isbn = '', # No ISBNs in the data
                            pubseries_id = pubseriesid,
                            pubseriesnum = pubseriesnum,
                            collection = workitem.collection,
                            coll_info = edition['coll_info'],
                            misc = edition['rest'],
                            fullstring = edition['fullstring'])
                    is_new = True
                s.add(ed)
                s.commit()

                if not is_new:
                    part = s.query(Part)\
                            .filter(Part.edition_id == ed.id,
                                    Part.work_id == workitem.id)\
                            .first()
                if is_new or not part:
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
                if edition['translator'] != '':
                    for translator in translators:
                        add_bookperson(s, translator, part, 'T')
                if edition['editor'] != '':
                    for editor in editors:
                        add_bookperson(s, editor, ed, 'E')


def save_genres(session, workid, genrelist):
    """ Save genres for a work.

        This function first deletes existing ones.
        This is the easiest way to make sure any
        changes are written to db.
    """
    retval = ''
    s = session()

    # First remove old genre definitions
    genres = s.query(Genre)\
              .filter(Genre.workid == workid)\
              .all()
    for genre in genres:
        s.delete(genre)
    s.commit()

    # Then add again
    genrelist.replace('/', ',')
    for genre in genrelist.split(','):

        m = re.search('(.+)\s(\d+\/\d+)', genre)
        if m:
            genre = m.group(1)
        if genre in genres_list:
            genreobj = s.query(Genre)\
                        .filter(Genre.workid == workid,
                                Genre.genre_name==genres_list[genre])\
                        .first()
            if not genreobj:
                genreobj = Genre(workid=workid, genre_name=genres_list[genre])
                s.add(genreobj)
    s.commit()
    return retval


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
        if i % 100 == 0:
            print('.', end='', flush=True)
        i += 1
    s.commit()
    print()



def add_missing_series(session):
    # This important publisher series is missing from the imported data.
    s = session()
    publisher = s.query(Publisher).filter(Publisher.name == 'Kirjayhtymä')\
                 .first()
    pubseries = s.query(Pubseries)\
                 .filter(Pubseries.publisher_id == publisher.id,
                         Pubseries.name == \
                        'Kirjayhtymän science fiction -sarja')\
                 .first()
    if not pubseries:
        logging.info('Creating missing Kirjayhtymä series')
        pubseries = Pubseries(name='Kirjayhtymän science fiction -sarja',
                important=True, publisher_id = publisher.id)
        s.add(pubseries)
        s.commit()


def create_admin(session):
    s = session()
    user = s.query(User)\
            .filter(User.name == 'admin')\
            .first()
    if not user:
        logging.info('Creating admin')
        user = User(name='admin', is_admin=True)
        user.set_password('admin')
        s.add(user)
        s.commit()

db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

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
        content += str(fle.read()).encode('utf8').replace('&amp;', '&')

    id_str = '\[[A-Z]{1}[a-z]{2}:\w{2}\]'
    id_re = re.compile(id_str)
    book_re = re.compile(id_str + '\s=\s(?P<author>.+)\s:\s(?P<title>')
    data = content.split('\n')

    for line in data:
        if id_re.match(line):
            print(line)



def insert_showroom():
    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)

    s = session()
    person = s.query(Person).filter(Person.alt_name == 'Isaac Asimov').first()

    person.bio = 'Asimovia pidetään yhtenä merkittävimmistä tieteiskirjailijoista. Hänen nimeään juhlistaa vieläkin Isaac Asimov\'s -niminen tieteiskirjallinen vihkolehti. Hänet on nimetty yhdeksi tieteiskirjallisuuden Grand Mastereista.'
    person.bio_src = 'Wikipedia'
    person.bio_src_url = 'http://www.wikipedia.fi'
    person.image = 'http://www.isfdb.org/wiki/images/4/47/Isaac_Asimov_on_Throne.png'
    person.image_src_url = 'http://www.isfdb.org'
    person.image_src = 'ISFDB'

    s.add(person)
    s.commit()

def read_params(args):
    p = argparse.ArgumentParser()
    p.add_argument('--debug', '-d', action='store_true', default=False)
    p.add_argument('--file', '-f', default='')
    p.add_argument('--stories', '-s', action='store_true', default=False)
    p.add_argument('--showroom', '-i',  help='Insert showroom', action='store_true', default=False)

    return vars(p.parse_args(args))


if __name__ == '__main__':
    import glob
    params = read_params(sys.argv[1:])
    loglevel = logging.INFO
    if params['debug'] == True:
        loglevel = logging.DEBUG
    logging.basicConfig(filename='import.log', filemode='w',
        level=loglevel)
    if params['showroom'] == True:
        insert_showroom()
        exit(0)
    if params['file']:
        filelist = [params['file']]
        print(filelist)
        import_all(filelist)
    elif params['stories']:
        filename = 'bibfiles/sf_nov_u.txt'
        import_stories(filename)
    else:
        filelist = glob.glob('bibfiles/*.html')
        import_all(filelist)
