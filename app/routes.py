
from flask import render_template
from app import app
from app.orm_decl import Person, BookPerson, Publisher, Book, Pubseries, Bookseries
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import pprint

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/people')
def people():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    people = session.query(Person).order_by(Person.name).all()
    return render_template('people.html', people=people)

def people_for_book(s, bookid, type):
    return s.query(Person).join(BookPerson).filter(BookPerson.book_id == bookid,
            BookPerson.type == type).all()

def books_for_person(s, personid, type):
    return s.query(Book).join(BookPerson).filter(BookPerson.person_id ==
            personid, BookPerson.type == type).all()

@app.route('/person/<personid>')
def person(personid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    app.logger.debug("personid = " + personid)
    app.logger.debug(session.query(Person).filter(Person.id == personid))
    person = session.query(Person).filter(Person.id == personid).first()
    authored = books_for_person(session, personid, 'A')
    translated = books_for_person(session, personid, 'T')
    edited = books_for_person(session, personid, 'E')
    return render_template('person.html', person=person, authored=authored,
            translated=translated, edited=edited)
@app.route('/books')
def books():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).order_by(Person.name).all()
    return render_template('books.html', authors=authors)

@app.route('/book/<bookid>')
def book(bookid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    book = session.query(Book).filter(Book.id == bookid).first()
    authors = people_for_book(session, bookid, 'A')
    translators = people_for_book(session, bookid, 'T')
    s = ''
    for author in translators:
        s += author.name + ', '
    app.logger.debug("Authors: " + s)
    editors = people_for_book(session, bookid, 'E')
    return render_template('book.html', book=book, authors=authors,
            translators=translators, editors=editors)

@app.route('/publishers')
def publishers():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    publishers = session.query(Publisher).order_by(Publisher.name).all()
    return render_template('publishers.html', publishers=publishers)

@app.route('/publisher/<pubid>')
def publisher(pubid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    app.logger.debug(session.query(Publisher).filter(Publisher.id == pubid))
    publisher = session.query(Publisher).filter(Publisher.id == pubid).first()
    series = session.query(Pubseries).filter(Pubseries.publisher_id == pubid).all()
    return render_template('publisher.html', publisher=publisher,
            series=series)

@app.route('/bookseries/<seriesid>')
def bookseries(seriesid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Bookseries).filter(Bookseries.id ==
            seriesid).first()
    authors = session.query(Person).filter(Book.bookseries_id == seriesid).all()
    return render_template('bookseries.html', series=series, authors=authors)

@app.route('/pubseries/<seriesid>')
def pubseries(seriesid):
    app.logger.debug("seriesid = " + seriesid)
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    app.logger.debug(session.query(Pubseries).filter(Pubseries.id == seriesid))
    series = session.query(Pubseries).filter(Pubseries.id == seriesid).first()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.pubseries_id ==
                            seriesid).order_by(Person.name).all()
        #session.query(Person, BookPerson, Book).filter(Person.id == BookPerson.person_id).filter(BookPerson.book_id == Book.id).filter(Book.pubseries_id == seriesid).all()
    app.logger.debug(session.query(Person, BookPerson, Book).filter(Person.id == BookPerson.person_id).filter(BookPerson.book_id == Book.id).filter(Book.pubseries_id == seriesid))
    return render_template('pubseries.html', series=series, authors=authors)
