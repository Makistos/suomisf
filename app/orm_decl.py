import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from app import db

Base = declarative_base()


class Publisher(Base):
    __tablename__ = 'publisher'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True, index=True)
    fullname = Column(String(250), nullable=False, unique=True)

class BookPerson(Base):
    __tablename__ = 'bookperson'
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False,
            primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False,
            primary_key=True)
    type = Column(String(1), nullable=False)
    book = relationship("Book", backref=backref("book_assoc"))
    person = relationship("Person", backref=backref("person_assoc"))

class Pubseries(Base):
    __tablename__ = 'pubseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    publisher_id = Column(Integer, ForeignKey('publisher.id'), nullable=False)
    publisher = relationship("Publisher", backref=backref('publisher',
        uselist=False))

class Bookseries(Base):
    __tablename__ = 'bookseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True)
    dob = Column(Integer)
    dod = Column(Integer)
    birthplace = Column(String(250))
    books = relationship("Book", secondary='bookperson')

class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False, index=True)
    pubyear = Column(Integer)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    edition = Column(Integer)
    originalname = Column(String(250))
    origpubyear = Column(Integer)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'))
    pubseriesnum = Column(String(20))
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'))
    bookseriesnum = Column(String(20))
    genre = Column(String(30))
    misc = Column(String(250))
    fullstring = Column(String(500))
    persons = relationship("Person", secondary='bookperson')
    publisher = relationship("Publisher", backref=backref('publishers',
        uselist=False))
    pubseries = relationship("Pubseries", backref=backref('pubseries',
        uselist=False))
    bookseries = relationship("Bookseries", backref=backref('bookseries',
        uselist=False))

    def __repr__(self):
        pass
        #return('<b>{}</b>. {}. ({}, {}). {}. {} {}. {}.'.format(

engine = create_engine('sqlite:///suomisf.db')

Base.metadata.create_all(engine)
