
from flask import render_template, request, flash, redirect, url_for, make_response
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import Person, Author, Editor, Translator, Publisher, Work, Edition, Pubseries, Bookseries, User, UserBook
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.forms import LoginForm, RegistrationForm, PublisherForm,\
PubseriesForm, PersonForm, BookseriesForm, UserForm
from .route_helpers import *
from app.forms import BookForm
import json
import logging
import pprint

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


@app.route('/add_to_owned/<bookid>', methods=['POST'])
def add_to_owned(bookid):
    app.logger.debug("bookid = " + bookid)
    session = new_session()
    #book = session.query(Book).filter(Book.id == bookid).first()
    userbook = UserBook(user_id = current_user.get_id(), book_id = bookid)
    session.add(userbook)
    session.commit()
    app.logger.debug(request.url)
    return ""


@app.route('/remove_from_owned/<bookid>', methods=['POST'])
def remove_from_owned(bookid):
    session = new_session()
    userbook = session.query(UserBook).filter(UserBook.user_id == current_user.get_id(),
            UserBook.book_id == bookid).first()
    session.delete(userbook)
    session.commit()
    return ""


### People related routes

@app.route('/people')
def people():
    session = new_session()
    people = session.query(Person).order_by(Person.name).all()
    return render_template('people.html', people=people)


@app.route('/person/<personid>')
def person(personid):
    session = new_session()
    person = session.query(Person).filter(Person.id == personid).first()
    authored = books_for_person(session, personid, 'A')
    translated = books_for_person(session, personid, 'T')
    edited = books_for_person(session, personid, 'E')
    return render_template('person.html', person=person, authored=authored,
            translated=translated, edited=edited)

@app.route('/edit_person/<personid>', methods=['POST', 'GET'])
def edit_person(personid):
    person = Person()
    session = new_session()
    if request.method == 'GET':
        if personid != 0:
            person = session.query(Person).filter(Person.id == personid).first()
        form = PersonForm(obj=person)
    else:
        form = PersonForm(request.form)
    if form.validate_on_submit():
        form.populate_obj(person)
        #person = Person(name=form.name.data, first_name=form.first_name.data,
        #        last_name=form.last_name.data, dob=form.dob.data,
        #        dod=form.dod.data, birthplace=form.birthplace.data)
        session.add(person)
        session.commit()
        return redirect(url_for('person', personid=person.id))
    return render_template('edit_person.html', form=form, personid=personid)

# Book related routes

@app.route('/books/lang')
def books_by_lang(lang):
    """ Returns a list of books such that each work is only represented by the
        first edition for given work in this language. """
    retval = []
    engine = create_engine('sqlite://suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Work)\
                     .filter(Work.id == Author.work_id)\
                     .order_by(Person.name)\
                     .all()

    for author in authors:
        for work in author.works:
            first_ed = sorted([x for x in work.editions if x.lang == lang],
                        key=lambda x: x['edition_num'])[0]
            #retval += {



@app.route('/books')
def books():
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Work)\
                     .filter(Work.id == Author.work_id)\
                     .order_by(Person.name)\
                     .all()
    return render_template('books.html', authors=authors)


@app.route('/booksX/<letter>')
def booksX(letter):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    #app.logger.debug(session.query(Person).join(BookPerson).filter(Person.id ==
    #                BookPerson.person_id).filter(BookPerson.type ==
    #                'A').filter(Person.name.ilike('A%')).order_by(Person.name))
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .filter(Person.name.ilike(letter + '%')).order_by(Person.name).all()
    return render_template('books.html', authors=authors, letter=letter)


@app.route('/work/<workid>')
def work(workid):
    engine = create_engine('sqlite:///suomisf.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    work = session.query(Work).filter(Work.id == workid).first()
    editions = session.query(Edition).filter(Edition.work_id == workid).all()
    authors = people_for_book(session, workid, 'A')
    translators = people_for_book(session, workid, 'T')
#    s = ''
    editors = people_for_book(session, workid, 'E')
    return render_template('work.html', work=work, authors=authors,
            translators=translators, editors=editors)

@app.route('/edit_work/<workid>', methods=["POST", "GET"])
def edit_work(workid):
    session = new_session()
    if workid != 0:
        work = session.query(Work)\
                      .filter(Work.id == workid)\
                      .first()
        editions = session.query(Edition)\
                          .join(Work)\
                          .filter(Edition.work_id == Work.id)\
                          .all()
        publisher = session.query(Publisher)\
                           .filter(Publisher.id == book.publisher_id)\
                           .first()
        authors = session.query(Person)\
                         .join(Author)\
                         .filter(Author.person_id == Person.id,\
                                 Author.book_id == work.id)\
                         .all()
        translators = session.query(Person)\
                             .join(Translator)\
                             .filter(Translator.person_id == Person.id)\
                             .join(Edition)\
                             .join(Translator.edition_id == edition.id)\
                             .join(Work)\
                             .filter(Edition.work_id == Work.id)\
                             .all()
        editors = session.query(Person)\
                         .join(Editor)\
                         .filter(Editor.person_id == Person.id)\
                         .join(Edition)\
                         .join(Editor.edition_id == edition.id)\
                         .join(Work)\
                         .filter(Edition.work_id == Work.id)\
                         .all()
#        pubseries = \
#                session.query(Pubseries)
#                       .join(Edition)
#                       .filter(Pubseries.id == edition.pubseries_id,
#                               Edition.work_id == workid)
#                       .all()
        bookseries = session.query(Bookseries)\
                            .join(Work)\
                            .filter(Bookseries.id == work.bookseries_id,\
                                    Work.id == workid)\
                            .first()
    else:
        work = Work()

    search_list = publisher_list(session)
    search_list = {**search_list, **author_list(session)}
#    publisher_series = pubseries_list(session, .publisher.id)

    form = WorkForm(request.form)
#    selected_pubseries = '0'
#    if publisher_series:
#        form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
#    else:
#        form.pubseries.choices = [('0', "Ei sarjaa")]
    if request.method == 'GET':
 #       if pubseries:
 #           i = 0
 #           for idx, s in enumerate(publisher_series['pubseries']):
 #               if s[1] == pubseries.name:
#                    i = s[0]
#                    break
#            form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
#            form.pubseries.default = str(i)
#            selected_pubseries = str(i)
        form.id.data = work.id
        form.title.data = work.title
        form.authors.data = ', '.join([a.name for a in authors])
#        form.translators.data = ', '.join([t.name for t in translators])
#        form.editors.data = ', '.join([e.name for e in editors])
        form.pubyear.data = work.pubyear
        form.title.data = work.title
#        form.origpubyear.data = book.origpubyear
#        form.edition.data = book.edition
#        form.publisher.data = publisher.name

        if bookseries:
            form.bookseries.data = bookseries.name
        form.bookseriesnum.data = work.bookseriesnum
        form.genre.data = work.genre
        form.misc.data = work.misc
        form.source.data = work.fullstring

    if form.validate_on_submit():
        author = session.query(Person).filter(Person.name ==
                form.authors.data).first()
        translator = session.query(Person).filter(Person.name ==
                form.translators.data).first()
        editor = session.query(Person).filter(Person.name ==
                form.editors.data).first()
        publisher = session.query(Publisher).filter(Publisher.name ==
                form.publisher.data).first()
        work.id = form.id.data
        work.title = form.title.data
        work.pubyear = form.pubyear.data
#        book.originalname = form.originalname.data
#        if book.origpubyear != '':
#            book.origpubyear = int(form.origpubyear.data)
#        book.edition = form.edition.data
#        book.publisher_id = publisher.id
        if form.bookseries.data != '':
            bookseries = session.query(Bookseries).filter(Bookseries.name ==
                    form.bookseries.data).first()
            work.bookseries_id = bookseries.id
        work.bookseriesnum = form.bookseriesnum.data
#        if form.pubseries.data == '0':
#            book.pubseries_id = None
#        else:
#            book.pubseries_id = form.pubseries.data
        work.genre = form.genre.data
        work.misc = form.misc.data
        if work.id == 0:
            session.add(work)
        session.commit()
        return redirect(url_for('work', bookid=work.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_work.html', id = work.id, form=form, search_lists =
            search_list, source = book.fullstring)


@app.route('/edit_edition/<editionid>', methods=["POST", "GET"])
def edit_edition(editionid):
    if editionid != 0:
        pass
    return render_template('edit_edition.html')


@app.route('/edition/<editionid>')
def edition(editionid):
    session = new_session()
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()

    return render_template('edition.html', edition = edition)


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
    app.logger.debug(session.query(Publisher).filter(Publisher.id == pubid))
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
    editions = session.query(Edition).filter(Edition.publisher_id == pubid).all()
    return render_template('publisher.html', publisher=publisher,
            series=series, book_count=book_count, oldest=oldest,
            newest=newest, editions=editions)

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
                     .join(Work)\
                     .filter(Work.bookseries_id == seriesid)\
                     .order_by(Person.name)\
                     .all()
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
                   .order_by(Edition.editionnum, Edition.pubyear)\
                   .all()
    #app.logger.debug(session.query(Person, BookPerson, Book).filter(Person.id == BookPerson.person_id).filter(BookPerson.book_id == Book.id).filter(Book.pubseries_id == seriesid))
    return render_template('pubseries.html', series=series, books=books)

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

    if type is None or id is None:
        return redirect(url_for('index'))

    session = new_session()

    if type == 'pubseries':
        authors = session.query(Person)\
                         .join(Author)\
                         .join(Work)\
                         .join(Edition)\
                         .filter(Edition.work_id == Work.id)\
                         .filter(Edition.pubseries_id == id)\
                         .order_by(Person.name)\
                         .all()
        series = session.query(Pubseries).filter(Pubseries.id == id).first()
        title = series.name
    elif type == 'bookseries':
        authors = session.query(Person)\
                         .join(Author)\
                         .join(Work)\
                         .filter(Work.bookseries_id == id)\
                         .order_by(Person.name)\
                         .all()
        series = session.query(Bookseries).filter(Bookseries.id == id).first()
        title = series.name
    return render_template('print_books.html', authors=authors, print = 1,
            title=title, series=series, type=type)

@app.route('/mybooks')
def mybooks():
    session = new_session()

    authors = session.query(Person)\
                     .join(Author)\
                     .join(Work)\
                     .filter(Work.id == Author.work_id)\
                     .join(Edition)\
                     .filter(Edition.work_id == Work.id)\
                     .join(UserBook)\
                     .filter(UserBook.user_id == current_user.get_id())\
                     .filter(UserBook.edition_id == Edition.id)\
                     .order_by(Person.name)\
                     .all()

    return render_template('mybooks.html', authors=authors, print=1)

@app.route('/myseries')
def myseries():
    session = new_session()
    pubseries = session.query(Pubseries).filter(Pubseries.important == True)
    pubseriesids = [x.id for x in pubseries]
    app.logger.debug("IDs = " + str(pubseriesids))
    authors = session.query(Person)\
                     .join(Author)\
                     .join(Work)\
                     .join(Edition)\
                     .filter(Author.work_id == Work.id)\
                     .filter(Edition.work_id == Work.id)\
                     .filter(Edition.pubseries_id.in_(pubseriesids))\
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
