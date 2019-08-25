import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

Base = declarative_base()

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

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
    important = Column(Boolean, default=False)
    publisher = relationship("Publisher", backref=backref('publisher',
        uselist=False))
    books = relationship("Book", backref=backref('book'), uselist=True)

class Bookseries(Base):
    __tablename__ = 'bookseries'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    important = Column(Boolean, default=False)


class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(150))
    dob = Column(Integer)
    dod = Column(Integer)
    birthplace = Column(String(250))
    source = Column(String(500))
    books = relationship("Book", secondary='bookperson')

class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    pubyear = Column(Integer)
    publisher_id = Column(Integer, ForeignKey('publisher.id'))
    edition = Column(Integer)
    originalname = Column(String(250))
    origpubyear = Column(Integer)
    pubseries_id = Column(Integer, ForeignKey('pubseries.id'))
    pubseriesnum = Column(String(20))
    bookseries_id = Column(Integer, ForeignKey('bookseries.id'))
    bookseriesnum = Column(String(20))
    genre = Column(String(100))
    misc = Column(String(500))
    fullstring = Column(String(500))
    persons = relationship("Person", secondary='bookperson')
    publisher = relationship("Publisher", backref=backref('publishers',
        uselist=False))
    pubseries = relationship("Pubseries", backref=backref('pubseries',
        uselist=False))
    bookseries = relationship("Bookseries", backref=backref('bookseries',
        uselist=False))
    owners = relationship("User", secondary='userbook')

    def __repr__(self):
        pass
        #return('<b>{}</b>. {}. ({}, {}). {}. {} {}. {}.'.format(

class User(UserMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, unique=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    books = relationship("Book", secondary="userbook")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}'.format(self.name)

class UserBook(Base):
    __tablename__ = 'userbook'
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False,
            primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False,
            primary_key=True)
    book = relationship("Book", backref=backref("book2_assoc"))
    user = relationship("User", backref=backref("user2_assoc"))


@login.user_loader
def load_user(id):
    engine = create_engine(os.environ.get('DATABASE_URL'))
    Session = sessionmaker(bind=engine)
    session = Session()
    return session.query(User).get(int(id))

engine = create_engine(os.environ.get('DATABASE_URL'))

Base.metadata.create_all(engine)
