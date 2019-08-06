
from flask import render_template, request, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import Person, BookPerson, Publisher, Book, Pubseries, Bookseries, User, UserBook
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.forms import LoginForm, RegistrationForm, PublisherForm, PubseriesForm, PersonForm
from app.forms import BookForm
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
        return {'pubseries' : [str(x.name) for x in
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
        engine = create_engine('sqlite:///suomisf.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        user = User(name=form.username.data)
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        flash('Rekisteröinti onnistui!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Tunnuksen luonti',
            form=form)

@app.route('/userpage/<userid>', methods=['GET', 'POST'])
def userpage(userid):
#    form = UserForm()
#    if form.validate_on_submit():
#        session = new_session()
#        user = session.query(User).filter(User.id = userid)
#        user.set_password(form.password.data)
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
    if bookid != 0:
        search_list = {**search_list, **pubseries_list(session,
            book.publisher.id)}
    else:
        search_list = {**search_list, **pubseries_list(session, 0)}

    form = BookForm()
    form.title.data = book.title
    form.authors.data = ', '.join([a.name for a in authors])
    form.translators.data = ', '.join([t.name for t in translators])
    form.editors.data = ', '.join([e.name for e in editors])
    form.pubyear.data = book.pubyear
    form.originalname.data = book.originalname
    form.origpubyear.data = book.origpubyear
    form.edition.data = book.edition
    form.publisher.data = publisher.name
    if pubseries:
        form.pubseries.data = pubseries.name
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
        book.title = form.title.data
        book.pubyear = form.pubyear.data
        book.originalname = form.originalname.data
        book.origpubyear = form.origpubyear.data
        book.edition = form.edition.data
        book.publisher_id = publisher.id
        if form.bookseries.data != '':
            bookseries = session.query(Bookseries).filter(Bookseries.name ==
                    form.bookseries.data).first()
            book.bookseries_id = bookseries.id
        if form.pubseries.data != '':
            pubseries = session.query(Pubseries).filter(Pubseries.name ==
                    form.pubseries.data).first()
            book.pubseries_id = pubseries.id
        book.genre = form.genre.data
        book.misc = form.misc.data
        session.add(book)
        session.commit()
        return redirect(url_for('book', bookid=book.id))
    return render_template('edit_book.html', id = book.id, form=form, search_lists =
            search_list, source = book.fullstring)

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

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

@app.route('/allbookseries')
def allbookseries():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Bookseries).order_by(Bookseries.name).all()
    return render_template('allbookseries.html', series=series)

@app.route('/bookseries/<seriesid>')
def bookseries(seriesid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Bookseries).filter(Bookseries.id ==
            seriesid).first()
    authors = \
            session.query(Person).join(BookPerson).filter(BookPerson.type ==
                    'A').join(Book).filter(Book.bookseries_id ==
                            seriesid).order_by(Person.name).all()
    return render_template('bookseries.html', series=series, authors=authors)

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
    app.logger.debug(session.query(Person, BookPerson, Book).filter(Person.id == BookPerson.person_id).filter(BookPerson.book_id == Book.id).filter(Book.pubseries_id == seriesid))
    return render_template('pubseries.html', series=series, authors=authors)

@app.route('/new_pubseries', methods=['GET', 'POST'])
def new_pubseries():
    form = PubseriesForm()
    session = new_session()
    search_lists = {'publisher' : [str(x.name) for x in
            session.query(Publisher).order_by(Publisher.name).all()]}
    #search_lists = {'publisher' : ['Karisto', 'WSOY']}
    if form.validate_on_submit():
        publisher = session.query(Publisher).filter(Publisher.name ==
                form.publisher.data).first()
        pubseries = Pubseries(name=form.name.data,publisher_id=publisher.id,
                important=form.important.data)
        session.add(pubseries)
        session.commit()
        return redirect(url_for('index'))
        #return redirect(url_for('pubseries', seriesid=pubseries.id))
    return render_template('new_pubseries.html', form=form,
            search_lists=search_lists)


@app.route('/print_books')
def print_books():
    type = request.args.get('type', None)
    id = request.args.get('id', None)

    if type is None or id is None:
        return redirect(url_for('index'))

    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()

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
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
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
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    q= ''
    searchword = request.args.get('search', '')
    for k, v in request.args.items():
        app.logger.debug(k + " : " + v)
    app.logger.debug("searchword: " + searchword)
    if request.method == 'POST':
        q = request.form
    #for key,val in request.form.items():
    #    app.logger.debug("key = " + key + " val = " + val)
    #q = PostForm().post.data
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
