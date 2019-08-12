
from flask import render_template, request, flash, redirect, url_for, make_response
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import Person, BookPerson, Publisher, Book, Pubseries, Bookseries, User, UserBook
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.forms import LoginForm, RegistrationForm, PublisherForm,\
PubseriesForm, PersonForm, BookseriesForm, UserForm
from app.forms import BookForm
import json
import logging
import pprint

def new_session():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def publisher_list(session):
    return {'publisher' : [str(x.name) for x in
            session.query(Publisher).order_by(Publisher.name).all()]}

def author_list(session):
    return {'author' : [str(x.name) for x in
            session.query(Person).order_by(Person.name).all()]}

def pubseries_list(session, pubid):
    if pubid != 0:
        return {'pubseries' : [(str(x.id), str(x.name)) for x in
                session.query(Pubseries).filter(Pubseries.publisher_id == pubid).order_by(Pubseries.name).all()]}
    else:
        return {'pubseries' : [str(x.name) for x in
                session.query(Pubseries).order_by(Pubseries.name).all()]}


def bookseries_list(session):
    return {'bookseries' : [str(x.name) for x in
            session.query(Bookseries).order_by(Bookseries.name).all()]}

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

### User related routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        engine = create_engine('sqlite:///suomisf.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        user = session.query(User).filter_by(name=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Väärä käyttäjätunnus tai salasana')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect('/index')
    return render_template('login.html', title='Kirjaudu', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        session = new_session()
        user = User(name=form.username.data)
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        flash('Rekisteröinti onnistui!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form, title='Tunnuksen luonti')

@app.route('/user/<userid>')
def user(userid):
    session = new_session()
    user = session.query(User).filter(User.id == userid).first()
    book_count = session.query(UserBook).filter(UserBook.user_id ==
            userid).count()
    return render_template('user.html', user=user, book_count=book_count)

@app.route('/user/edit/<userid>', methods=['GET', 'POST'])
def edit_user(userid):
    session = new_session()
    form = UserForm()
    user = session.query(User).filter(User.id == userid).first()
    form.name.data = user.name
    form.is_admin.data = user.is_admin
    if form.validate_on_submit():
        if form.password.data != '':
            user.set_password(form.password.data)
        user.name = form.name.data
        user.is_admin = form.is_admin.data
        session.add(user)
        session.commit()
        return redirect(url_for('user', userid=user.id))
    return render_template('edit_user.html', form=form)

@app.route('/add_to_owned/<bookid>')
def add_to_owned(bookid):
    session = new_session()
    #book = session.query(Book).filter(Book.id == bookid).first()
    userbook = UserBook(user_id = current_user.get_id(), book_id = bookid)
    session.add(userbook)
    session.commit()
    app.logger.debug(request.url)
    return redirect(redirect_url())

@app.route('/remove_from_owned/<bookid>')
def remove_from_owned(bookid):
    session = new_session()
    userbook = session.query(UserBook).filter(UserBook.user_id == current_user.get_id(),
            UserBook.book_id == bookid).first()
    session.delete(userbook)
    session.commit()
    return redirect(redirect_url())


### People related routes

@app.route('/people')
def people():
    session = new_session()
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
    session = new_session()
    person = session.query(Person).filter(Person.id == personid).first()
    authored = books_for_person(session, personid, 'A')
    translated = books_for_person(session, personid, 'T')
    edited = books_for_person(session, personid, 'E')
    return render_template('person.html', person=person, authored=authored,
            translated=translated, edited=edited)

@app.route('/new_person', methods=['POST', 'GET'])
def new_person():
    session = new_session()
    form = PersonForm()
    session = new_session()
    if form.validate_on_submit():
        person = Person(name=form.name.data, first_name=form.firstname.data,
                last_name=form.lastname.data, dob=form.dob.data,
                dod=form.dod.data, birthplace=form.birthplace.data)
        session.add(person)
        session.commit()
        return redirect(url_for('person', personid=person.id))
    return render_template('new_person.html', form=form)


# Book related routes

@app.route('/books')
def books():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).order_by(Person.name).all()
    return render_template('books.html', authors=authors)

@app.route('/booksX/<letter>')
def booksX(letter):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    app.logger.debug(session.query(Person).join(BookPerson).filter(Person.id ==
                    BookPerson.person_id).filter(BookPerson.type ==
                    'A').filter(Person.name.ilike('A%')).order_by(Person.name))
    authors = \
            session.query(Person).join(BookPerson).filter(Person.id ==
                    BookPerson.person_id).filter(BookPerson.type ==
                    'A').filter(Person.name.ilike(letter + '%')).order_by(Person.name).all()
    return render_template('books.html', authors=authors, letter=letter)

@app.route('/book/<bookid>')
def book(bookid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    book = session.query(Book).filter(Book.id == bookid).first()
    authors = people_for_book(session, bookid, 'A')
    translators = people_for_book(session, bookid, 'T')
    s = ''
    editors = people_for_book(session, bookid, 'E')
    return render_template('book.html', book=book, authors=authors,
            translators=translators, editors=editors)

@app.route('/edit_book/<bookid>', methods=["POST", "GET"])
def edit_book(bookid):
    session = new_session()
    if bookid != 0:
        book = session.query(Book).filter(Book.id == bookid).first()
        publisher = session.query(Publisher).filter(Publisher.id ==
                book.publisher_id).first()
        authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.person_id ==
                    Person.id, BookPerson.book_id == book.id, BookPerson.type == 'A').all()
        translators = \
            session.query(Person).join(BookPerson).filter(BookPerson.person_id ==
                    Person.id, BookPerson.book_id == book.id, BookPerson.type == 'T').all()
        editors = \
            session.query(Person).join(BookPerson).filter(BookPerson.person_id ==
                    Person.id, BookPerson.book_id == book.id, BookPerson.type == 'E').all()
        pubseries = \
                session.query(Pubseries).filter(Pubseries.id == book.pubseries_id).first()
        bookseries = \
                session.query(Bookseries).filter(Bookseries.id ==
                        book.bookseries_id).first()
    else:
        book = Book()

    search_list = publisher_list(session)
    search_list = {**search_list, **author_list(session)}
    publisher_series = pubseries_list(session, book.publisher.id)

    form = BookForm(request.form)
    selected_pubseries = '0'
    if publisher_series:
        form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
    else:
        form.pubseries.choices = [('0', "Ei sarjaa")]
    if request.method == 'GET':
        if pubseries:
            i = 0
            for idx, s in enumerate(publisher_series['pubseries']):
                if s[1] == pubseries.name:
                    i = s[0]
                    break
            form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
            form.pubseries.default = str(i)
            selected_pubseries = str(i)
        form.id.data = book.id
        form.title.data = book.title
        form.authors.data = ', '.join([a.name for a in authors])
        form.translators.data = ', '.join([t.name for t in translators])
        form.editors.data = ', '.join([e.name for e in editors])
        form.pubyear.data = book.pubyear
        form.originalname.data = book.originalname
        form.origpubyear.data = book.origpubyear
        form.edition.data = book.edition
        form.publisher.data = publisher.name

        if bookseries:
            form.bookseries.data = bookseries.name
        form.genre.data = book.genre
        form.misc.data = book.misc
        form.source.data = book.fullstring

    if form.validate_on_submit():
        author = session.query(Person).filter(Person.name ==
                form.authors.data).first()
        translator = session.query(Person).filter(Person.name ==
                form.translators.data).first()
        editor = session.query(Person).filter(Person.name ==
                form.editors.data).first()
        publisher = session.query(Publisher).filter(Publisher.name ==
                form.publisher.data).first()
        book.id = form.id.data
        book.title = form.title.data
        book.pubyear = form.pubyear.data
        book.originalname = form.originalname.data
        if book.origpubyear != '':
            book.origpubyear = int(form.origpubyear.data)
        book.edition = form.edition.data
        book.publisher_id = publisher.id
        if form.bookseries.data != '':
            bookseries = session.query(Bookseries).filter(Bookseries.name ==
                    form.bookseries.data).first()
            book.bookseries_id = bookseries.id
        if form.pubseries.data == '0':
            book.pubseries_id = None
        else:
            book.pubseries_id = form.pubseries.data
        book.genre = form.genre.data
        book.misc = form.misc.data
        if book.id == 0:
            session.add(book)
        session.commit()
        return redirect(url_for('book', bookid=book.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_book.html', id = book.id, form=form, search_lists =
            search_list, source = book.fullstring,
            selected_pubseries=selected_pubseries)


### Publisher related routes

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
    book_count = session.query(Book).filter(Book.publisher_id == pubid).count()
    oldest = session.query(Book).filter(Book.publisher_id ==
            pubid).order_by(Book.pubyear).first()
    newest = session.query(Book).filter(Book.publisher_id ==
            pubid).order_by(desc(Book.pubyear)).first()
    series = session.query(Pubseries).filter(Pubseries.publisher_id == pubid).all()
    return render_template('publisher.html', publisher=publisher,
            series=series, book_count=book_count, oldest=oldest, newest=newest)

@app.route('/new_publisher', methods=['GET', 'POST'])
def new_publisher():
    form = PublisherForm()
    session = new_session()
    if form.validate_on_submit():
        publisher = Publisher(name=form.name.data, fullname=form.fullname.data)
        session.add(publisher)
        session.commit()
        return redirect(url_for('publisher', pubid=publisher.id))
    return render_template('new_publisher.html', form=form)


### Bookseries related routes

@app.route('/allbookseries')
def allbookseries():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Bookseries).order_by(Bookseries.name).all()
    return render_template('allbookseries.html', series=series)

@app.route('/bookseries/<seriesid>')
def bookseries(seriesid):
    session = new_session()
    series = session.query(Bookseries).filter(Bookseries.id ==
            seriesid).first()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.bookseries_id ==
                            seriesid).order_by(Person.name).all()
    return render_template('bookseries.html', series=series, authors=authors)

@app.route('/new_bookseries', methods=['POST', 'GET'])
def new_bookseries():
    session = new_session()
    form = BookseriesForm()
    if form.validate_on_submit():
        bookseries = Bookseries(name=form.name.data,
                important=form.important.data)
        session.add(bookseries)
        session.commit()
        return redirect(url_for('bookseries', seriesid=bookseries.id))
    return render_template('new_bookseries.html', form=form)


# Publisher series related routes

@app.route('/allpubseries')
def allpubseries():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Pubseries).order_by(Pubseries.name).all()
    app.logger.debug(session.query(Pubseries).order_by(Pubseries.name))
    return render_template('allpubseries.html', series=series)

@app.route('/pubseries/<seriesid>')
def pubseries(seriesid):
    session = new_session()
    app.logger.debug(session.query(Pubseries).filter(Pubseries.id == seriesid))
    series = session.query(Pubseries).filter(Pubseries.id == seriesid).first()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.pubseries_id ==
                            seriesid).order_by(Person.name).all()
    app.logger.debug(session.query(Person, BookPerson, Book).filter(Person.id == BookPerson.person_id).filter(BookPerson.book_id == Book.id).filter(Book.pubseries_id == seriesid))
    return render_template('pubseries.html', series=series, authors=authors)

@app.route('/new_pubseries', methods=['GET', 'POST'])
def new_pubseries():
    form = PubseriesForm()
    session = new_session()
    search_lists = {'publisher' : [str(x.name) for x in
            session.query(Publisher).order_by(Publisher.name).all()]}
    if form.validate_on_submit():
        publisher = session.query(Publisher).filter(Publisher.name ==
                form.publisher.data).first()
        pubseries = Pubseries(name=form.name.data,publisher_id=publisher.id,
                important=form.important.data)
        session.add(pubseries)
        session.commit()
        return redirect(url_for('index'))
    return render_template('new_pubseries.html', form=form,
            search_lists=search_lists)

@app.route('/list_pubseries/<pubname>', methods=['GET', 'POST'])
def list_pubseries(pubname):
    session = new_session()
    series = session.query(Pubseries).join(Publisher).filter(Publisher.name ==
            pubname).all()
    data = []
    for s in series:
        data.append((str(s.id), s.name))
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response


# Miscellaneous routes

@app.route('/print_books')
def print_books():
    type = request.args.get('type', None)
    id = request.args.get('id', None)

    if type is None or id is None:
        return redirect(url_for('index'))

    session = new_session()

    if type == 'pubseries':
        authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.pubseries_id ==
                            id).order_by(Person.name).all()
        series = session.query(Pubseries).filter(Pubseries.id == id).first()
        title = series.name
    elif type == 'bookseries':
        authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.bookseries_id ==
                            id).order_by(Person.name).all()
        series = session.query(Bookseries).filter(Bookseries.id == id).first()
        title = series.name
    return render_template('print_books.html', authors=authors, print = 1,
            title=title, series=series, type=type)

@app.route('/mybooks')
def mybooks():
    session = new_session()

    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
            'A').join(Book).filter(Book.id ==
                    BookPerson.book_id).join(UserBook).filter(UserBook.user_id
                            == current_user.get_id()).all()

    return render_template('mybooks.html', authors=authors, print=1)

@app.route('/myseries')
def myseries():
    session = new_session()
    pubseries = session.query(Pubseries).filter(Pubseries.important == True)
    pubseriesids = [x.id for x in pubseries]
    app.logger.debug("IDs = " + str(pubseriesids))
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.pubseries_id.in_(pubseriesids)).order_by(Person.name).all()
    app.logger.debug("Count = " + str(len(authors)))
    app.logger.debug(session.query(Person).join(BookPerson).filter(BookPerson.type
        == 'A').join(Book).filter(Book.pubseries_id.in_(pubseriesids)).order_by(Person.name))
    return render_template('myseries.html', pubseries=pubseries,
            authors=authors)


@app.route('/search', methods = ['POST', 'GET'])
def search():
    session = new_session()
    q= ''
    searchword = request.args.get('search', '')
    for k, v in request.args.items():
        app.logger.debug(k + " : " + v)
    app.logger.debug("searchword: " + searchword)
    if request.method == 'POST':
        q = request.form
    app.logger.debug("q = " + q)
    books = \
        session.query(Book).filter(Book.title.ilike('%' + searchword + '%')).all()
    people = \
            session.query(Person).filter(Person.name.ilike('%' + searchword +
                '%')).all()
    publishers = \
            session.query(Publisher).filter(Publisher.name.ilike('%' +
                searchword + '%')).all()
    bookseries = \
            session.query(Bookseries).filter(Bookseries.name.ilike('%' +
                searchword + '%')).all()
    pubseries = \
            session.query(Pubseries).filter(Pubseries.name.ilike('%' +
                searchword + '%')).all()
    return render_template('search_results.html', books=books, people=people,
            publishers=publishers, bookseries=bookseries, pubseries=pubseries,
            searchword=searchword)
