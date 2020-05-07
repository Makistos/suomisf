
from flask import render_template, request, flash, redirect, url_for, make_response
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import Person, Author, Editor, Translator, Publisher, Work,\
Edition, Pubseries, Bookseries, User, UserBook, ShortStory, UserPubseries,\
Alias, Genre
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from app.forms import LoginForm, RegistrationForm, PublisherForm,\
PubseriesForm, PersonForm, BookseriesForm, UserForm
from .route_helpers import *
#from app.forms import BookForm
from flask_sqlalchemy import get_debug_queries
import json
import logging
import pprint

@app.route('/')
@app.route('/index')
def index():
    session = new_session()
    work_count = session.query(func.count(Work.id)).first()
    edition_count = session.query(func.count(Edition.id)).first()
    author_count = session.query(Author.person_id.distinct()).all()
    pub_count = session.query(func.count(Publisher.id)).first()
    person_count = session.query(func.count(Person.id)).first()
    pubseries_count = session.query(func.count(Pubseries.id)).first()
    bookseries_count = session.query(func.count(Bookseries.id)).first()

    return render_template('index.html', work_count=work_count,
                           edition_count=edition_count,
                           author_count=author_count,
                           pub_count=pub_count, person_count=person_count,
                           pubseries_count=pubseries_count,
                           bookseries_count=bookseries_count)

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
        pubseries = session.query(Pubseries)\
                           .filter(Pubseries.important == True)\
                           .all()
        session.commit()
        for series in pubseries:
            ups = UserPubseries(user_id=user.id,
                    series_id=series.id)
            session.add(ups)
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
        if current_user.is_admin:
            user.is_admin = form.is_admin.data
        session.add(user)
        session.commit()
        return redirect(url_for('user', userid=user.id))
    return render_template('edit_user.html', form=form)


@app.route('/users')
def users():
    session = new_session()
    users = session.query(User).all()
    return render_template('users.html', users=users)


@app.route('/add_to_owned/<bookid>', methods=['POST'])
def add_to_owned(bookid):
    app.logger.debug("bookid = " + bookid)
    session = new_session()
    #book = session.query(Book).filter(Book.id == bookid).first()
    userbook = UserBook(user_id = current_user.get_id(), edition_id = bookid)
    session.add(userbook)
    session.commit()
    app.logger.debug(request.url)
    return ""

@app.route('/add_work_to_owned/<workid>', methods=['POST'])
def add_work_to_owned(workid):
    first_edition = get_first_edition(workd)
    session = new_session()
    userbook = UserBook(user_id = current_user.get_id(),
                        edition_id = first_edition.id)
    session.add(userbook)
    session.commit()
    app.logger.debug(request.url)
    return ""

@app.route('/remove_from_owned/<bookid>', methods=['POST'])
def remove_from_owned(bookid):
    session = new_session()
    userbook = session.query(UserBook)\
                      .filter(UserBook.user_id == current_user.get_id(),
                       UserBook.edition_id == bookid).first()
    session.delete(userbook)
    session.commit()
    return ""


### People related routes

@app.route('/people')
def people():
    session = new_session()
    people = session.query(Person).order_by(Person.name).all()
    return render_template('people.html', people=people,
                            header='Kannassa olevat henkilöt')

@app.route('/authors')
def authors():
    session = new_session()
    people = session.query(Person)\
                    .join(Author)\
                    .filter(Author.person_id == Person.id)\
                    .order_by(Person.name).all()
    return render_template('people.html', people=people,
                            header='Kannassa olevat kirjailijat')

@app.route('/translators')
def translators():
    session = new_session()
    people = session.query(Person)\
                    .join(Translator)\
                    .filter(Translator.person_id == Person.id)\
                    .order_by(Person.name).all()
    return render_template('people.html', people=people,
                            header='Kannassa olevat kääntäjät')

@app.route('/editors')
def editors():
    session = new_session()
    people = session.query(Person)\
                    .join(Editor)\
                    .filter(Editor.person_id == Person.id)\
                    .order_by(Person.name).all()
    return render_template('people.html', people=people,
                            header='Kannassa olevat toimittajat')

@app.route('/person/<personid>')
def person(personid):
    session = new_session()
    if personid.isdigit():
        person = session.query(Person).filter(Person.id == personid).first()
    else:
        person = session.query(Person).filter(Person.name == personid).first()

    authored = books_for_person(session, personid, 'A')
    translated = books_for_person(session, personid, 'T')
    edited = books_for_person(session, personid, 'E')
    #aliases = session.query(Person)\
    #                 .join(Alias)\
    #                 .filter(Alias.realname == person.id)\
    #                 .all()
    #real_names = session.query(Person)\
    #                    .join(Alias)\
    #                    .filter(Alias.alias == person.id)\
    #                    .all()
    return render_template('person.html', person=person, authored=authored,
            translated=translated, edited=edited)

@app.route('/edit_person/<personid>', methods=['POST', 'GET'])
def edit_person(personid):
    session = new_session()
    if personid != 0:
        person = session.query(Person).filter(Person.id == personid).first()
    else:
        person = Person()
    form = PersonForm(request.form)
    if request.method == 'GET':
        form.name.data = person.name
        form.first_name.data = person.first_name
        form.last_name.data = person.last_name
        if person.dob:
            form.dob.data = person.dob
        else:
            form.dob.data = 0
        if person.dod:
            form.dod.data = person.dod
        else:
            form.dod.data = 0
        form.birthplace.data = person.birthplace
        form.image_src.data = person.image_src
    if form.validate_on_submit():
        person.name = form.name.data
        person.first_name = form.first_name.data
        person.last_name = form.last_name.data
        if form.dob.data != 0:
            person.dob = form.dob.data
        if form.dod.data != 0:
            person.dod = form.dod.data
        person.birthplace = form.birthplace.data
        person.image_src = form.image_src.data
        session.add(person)
        session.commit()
        return redirect(url_for('person', personid=person.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_person.html', form=form, personid=personid)

### Publisher related routes

@app.route('/publishers')
def publishers():
    session = new_session()
    publishers = session.query(Publisher)\
                        .order_by(Publisher.name)\
                        .all()
    return render_template('publishers.html', publishers=publishers)

@app.route('/publisher/<pubid>')
def publisher(pubid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    #app.logger.debug(session.query(Publisher).filter(Publisher.id == pubid))
    publisher = session.query(Publisher).filter(Publisher.id == pubid).first()
    book_count = session.query(Edition)\
                        .filter(Edition.publisher_id == pubid)\
                        .count()
    oldest = session.query(Edition)\
                    .filter(Edition.publisher_id == pubid)\
                    .order_by(Edition.pubyear)\
                    .first()
    newest = session.query(Edition)\
                    .filter(Edition.publisher_id == pubid)\
                    .order_by(desc(Edition.pubyear))\
                    .first()
    series = session.query(Pubseries).filter(Pubseries.publisher_id == pubid).all()
    g = session.query(Genre).all()
    genres = session.query(Genre, func.count(Genre.genre_name))\
                    .join(Work)\
                    .filter(Work.id == Genre.workid)\
                    .join(Part)\
                    .filter(Part.work_id == Work.id)\
                    .join(Edition)\
                    .filter(Edition.id == Part.edition_id)\
                    .filter(Edition.publisher_id == pubid)\
                    .group_by(Genre.genre_name)\
                    .order_by(func.count(Genre.genre_name).desc())\
                    .all()

    for g in genres:
        app.logger.debug(str(g[0]) + ", {g[1]}")
    #app.logger.debug(list(genres))
    editions = session.query(Edition)\
                      .order_by(Edition.pubyear)\
                      .filter(Edition.publisher_id == pubid).all()
    return render_template('publisher.html', publisher=publisher,
            series=series, book_count=book_count, oldest=oldest,
            newest=newest, editions=editions, genres=genres)

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
    series = session.query(Bookseries)\
                    .filter(Bookseries.id == seriesid)\
                    .first()
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Part)\
                     .filter(Part.id == Author.part_id)\
                     .join(Edition)\
                     .filter(Edition.id == Part.edition_id)\
                     .join(Work)\
                     .filter(Part.work_id == Work.id)\
                     .filter(Work.bookseries_id == seriesid)\
                     .order_by(Person.name, Work.bookseriesnum)\
                     .all()
    editions = session.query(Edition)\
                      .join(Part)\
                      .filter(Edition.id == Part.edition_id)\
                      .join(Work)\
                      .filter(Part.work_id == Work.id)\
                      .filter(Work.bookseries_id == seriesid)\
                      .order_by(Work.bookseriesnum, Edition.pubyear)\
                      .all()
    return render_template('bookseries.html', series=series, editions=editions)

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
    series = session.query(Pubseries)\
                    .filter(Pubseries.id == seriesid)\
                    .first()
    #authors = session.query(Person)\
    #                 .join(Author)\
    #                 .join(Work)\
    #                 .join(Edition)\
    #                 .filter(Work.id == Edition.work_id)\
    #                 .filter(Edition.pubseries_id == seriesid)\
    #                 .order_by(Person.name)\
    #                 .all()
    books = session.query(Edition)\
                   .filter(Edition.pubseries_id == seriesid)\
                   .join(Part)\
                   .filter(Part.edition_id == Edition.id)\
                   .join(Work)\
                   .filter(Part.work_id == Work.id)\
                   .order_by(Work.creator_str, Edition.title)\
                   .all()
    favorite = session.query(UserPubseries)\
                        .filter(UserPubseries.series_id == seriesid,
                                UserPubseries.user_id == current_user.get_id())\
                        .count()
    return render_template('pubseries.html', series=series, books=books,
            favorite=favorite)

@app.route('/new_pubseries', methods=['GET', 'POST'])
def new_pubseries():
    form = PubseriesForm()
    session = new_session()
    search_lists = {'publisher' : [str(x.name) for x in
                    session.query(Publisher)\
                           .order_by(Publisher.name)\
                           .all()]}
    if form.validate_on_submit():
        publisher = session.query(Publisher)\
                           .filter(Publisher.name == form.publisher.data)\
                           .first()
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
    series = session.query(Pubseries)\
                    .join(Publisher)\
                    .filter(Publisher.name == pubname)\
                    .all()
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
    letter = request.args.get('letter', None)

    if type is None:
        return redirect(url_for('index'))

    session = new_session()

    if type == 'pubseries':
        works = None
        editions = session.query(Edition)\
                          .filter(Edition.pubseries_id == id)\
                          .order_by(Edition.pubyear)\
                          .all()
        series = session.query(Pubseries).filter(Pubseries.id == id).first()
        title = series.name
    elif type == 'bookseries':
        editions = None
        works = session.query(Work)\
                       .filter(Work.bookseries_id == id)\
                       .order_by(Work.creator_str)\
                       .all()
        series = session.query(Bookseries).filter(Bookseries.id == id).first()
        title = series.name
    elif type == 'books':
        editions = None
        series = None
        if letter:
            works = session.query(Work)\
                           .filter(Work.creator_str.like(letter + '%'))\
                           .order_by(Work.creator_str)\
                           .all()
            title = letter
        else:
            works = session.query(Work)\
                           .order_by(Work.creator_str)\
                           .all()
            title = 'Kaikki kirjat'
    return render_template('print_books.html', editions=editions, works=works, print = 1,
            title=title, series=series, type=type, letter=letter)

@app.route('/mybooks')
@app.route('/mybooks/<userid>')
def mybooks(userid=0):
    session = new_session()

    if userid == 0:
        userid = current_user.get_id()

    works = session.query(Work)\
                     .join(Part)\
                     .filter(Part.work_id == Work.id)\
                     .join(Author)\
                     .filter(Author.part_id == Part.id)\
                     .join(Edition)\
                     .filter(Part.edition_id == Edition.id)\
                     .join(UserBook)\
                     .filter(UserBook.user_id == userid) \
                     .filter(UserBook.edition_id == Edition.id)\
                     .all()

    return render_template('mybooks.html', works=works, print=1)

@app.route('/myseries')
def myseries():
    session = new_session()
    pubseries = session.query(Pubseries)\
                       .join(UserPubseries)\
                       .filter(Pubseries.id == UserPubseries.series_id)\
                       .filter(UserPubseries.user_id == current_user.get_id())\
                       .all()
    pubseriesids = [x.id for x in pubseries]
    app.logger.debug("IDs = " + str(pubseriesids))
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Author.person_id == Person.id)\
                     .join(Part)\
                     .filter(Author.part_id == Part.id)\
                     .join(Edition)\
                     .filter(Edition.pubseries_id.in_(pubseriesids))\
                     .filter(Edition.id == Part.edition_id)\
                     .order_by(Person.name)\
                     .all()
    app.logger.debug("Count = " + str(len(authors)))
    #app.logger.debug(session.query(Person).join(BookPerson).filter(BookPerson.type
    #    == 'A').join(Book).filter(Book.pubseries_id.in_(pubseriesids)).order_by(Person.name))
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
    works = \
        session.query(Work)\
               .filter(Work.title.ilike('%' + searchword + '%'))\
               .order_by(Work.title)\
               .all()
    editions = \
            session.query(Edition)\
                   .filter(Edition.title.ilike('%' + searchword + '%'))\
                   .order_by(Edition.title)\
                   .all()
    stories = \
            session.query(ShortStory)\
                   .filter(ShortStory.title.ilike('%' + searchword + '%'))\
                   .order_by(ShortStory.title)\
                   .all()
    people = \
            session.query(Person)\
                   .filter(Person.name.ilike('%' + searchword + '%'))\
                   .order_by(Person.name)\
                   .all()
    publishers = \
            session.query(Publisher)\
                   .filter(Publisher.name.ilike('%' + searchword + '%'))\
                   .order_by(Publisher.name)\
                   .all()
    bookseries = \
            session.query(Bookseries)\
                   .filter(Bookseries.name.ilike('%' + searchword + '%'))\
                   .order_by(Bookseries.name)\
                   .all()
    pubseries = \
            session.query(Pubseries)\
                   .filter(Pubseries.name.ilike('%' + searchword + '%'))\
                   .order_by(Pubseries.name)\
                   .all()
    return render_template('search_results.html', works=works,
            editions=editions, people=people, stories=stories,
            publishers=publishers, bookseries=bookseries, pubseries=pubseries,
            searchword=searchword)

@app.route('/addfavpubcol/<pubseriesid>', methods=["POST", "GET"])
def addfavpubcol(pubseriesid):
    session = new_session()

    upubseries = UserPubseries(series_id=pubseriesid,
                               user_id=current_user.get_id())
    session.add(upubseries)
    session.commit()
    return redirect(url_for('pubseries', seriesid=pubseriesid))

@app.route('/removefavpubcol/<pubseriesid>', methods=["POST", "GET"])
def removefavpubcol(pubseriesid):
    session = new_session()

    upubseries = session.query(UserPubseries)\
                        .filter(UserPubseries.series_id == pubseriesid,
                                UserPubseries.user_id ==
                                current_user.get_id())\
                        .first()
    session.delete(upubseries)
    session.commit()
    return redirect(url_for('myseries'))

