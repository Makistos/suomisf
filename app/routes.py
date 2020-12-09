from flask import render_template, request, flash, redirect, url_for,\
    make_response, jsonify, Response
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import (Person, Author, Editor, Translator, Work,
                          Edition, Pubseries, Bookseries, User, UserBook, ShortStory, UserPubseries,
                          Alias, Genre, WorkGenre, Tag, Award, AwardCategory, Awarded,
                          Magazine, Issue, PublicationSize)
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from app.forms import (LoginForm, RegistrationForm,
                       PubseriesForm, BookseriesForm, UserForm,
                       SearchForm, IssueForm, MagazineForm)
from .route_helpers import *
# from app.forms import BookForm
from flask_sqlalchemy import get_debug_queries
import json
import logging
import pprint
import urllib


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
    story_count = session.query(func.count(ShortStory.id)).first()

    return render_template('index.html', work_count=work_count,
                           edition_count=edition_count,
                           author_count=author_count,
                           pub_count=pub_count, person_count=person_count,
                           pubseries_count=pubseries_count,
                           bookseries_count=bookseries_count,
                           story_count=story_count)


def redirect_url(default='index'):
    return request.args.get('next') or \
        request.referrer or \
        url_for(default)

# User related routes


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


@app.route('/award/<awardid>')
def award(awardid):
    session = new_session()

    award = session.query(Award).filter(Award.id == awardid).first()
    awards = session.query(Awarded)\
                    .filter(Awarded.award_id == awardid)\
                    .all()

    return render_template('award.html', award=award, awards=awards)


@app.route('/awards')
def awards():
    session = new_session()

    awards = session.query(Award).all()

    return render_template('awards.html', awards=awards)


@app.route('/stats')
def stats():
    session = new_session()

    counts = session.query(Genre.abbr, Genre.name.label('genre_name'),
                           func.count(Work.id).label('work_count'))\
        .join(Genre.works)\
        .group_by(Genre.abbr)\
        .order_by(func.count(Work.id).desc())\
        .all()

    genres = ['SF', 'F', 'K', 'nSF', 'nF', 'nK', 'kok']
    tops = {}
    for genre in genres:
        tops[genre] = session.query(Person.name,
                                    func.count(Person.id).label(
                                        'person_count'),
                                    Genre.abbr, Genre.name.label('genre_name'))\
            .join(Work.genres)\
            .join(Part)\
            .filter(Work.id == Part.work_id)\
            .join(Edition)\
            .filter(Part.edition_id == Edition.id)\
            .join(Author)\
            .filter(Author.part_id == Part.id)\
            .join(Person)\
            .filter(Author.person_id == Person.id)\
            .filter(Genre.abbr == genre)\
            .filter(Part.shortstory_id == None)\
            .filter(Edition.editionnum == 1)\
            .group_by(Person.id)\
            .order_by(func.count(Work.id).desc())\
            .limit(10)\
            .all()

    translators = session.query(Person.name, func.count(Translator.person_id))\
                         .join(Translator.parts)\
                         .join(Translator.person)\
                         .filter(Part.shortstory_id == None)\
                         .group_by(Person.id)\
                         .order_by(func.count(Translator.person_id).desc())\
                         .limit(20)\
                         .all()

    editors = session.query(Person.name, func.count(Editor.person_id))\
                     .join(Editor.person)\
                     .join(Editor.edits)\
                     .group_by(Person.id)\
                     .order_by(func.count(Editor.person_id).desc())\
                     .limit(20)\
                     .all()

    stories = session.query(Person.name, func.count(Person.id))\
        .join(Part.authors)\
        .join(Work)\
        .filter(Part.work_id == Work.id)\
        .filter(Part.shortstory_id != None)\
        .group_by(Person.id)\
        .order_by(func.count(Work.id).desc())\
        .limit(10)\
        .all()

    countries = session.query(Person.nationality,
                              func.count(Person.nationality).label('count'))\
        .group_by(Person.nationality)\
        .order_by(func.count(Person.nationality).desc())\
        .limit(10)\
        .all()

    return render_template('stats.html',
                           counts=counts,
                           topsf=tops['SF'], topf=tops['F'], topk=tops['K'],
                           topnsf=tops['nSF'], topnf=tops['nF'], topnk=tops['nK'],
                           topcoll=tops['kok'],
                           translators=translators,
                           editors=editors,
                           stories=stories,
                           countries=countries)



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
    # book = session.query(Book).filter(Book.id == bookid).first()
    userbook = UserBook(user_id=current_user.get_id(), edition_id=bookid)
    session.add(userbook)
    session.commit()
    app.logger.debug(request.url)
    return ""


@app.route('/add_work_to_owned/<workid>', methods=['POST'])
def add_work_to_owned(workid):
    first_edition = get_first_edition(workid)
    session = new_session()
    userbook = UserBook(user_id=current_user.get_id(),
                        edition_id=first_edition.id)
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



@app.route('/magazines')
def magazines():
    session = new_session()

    magazines = session.query(Magazine)\
                       .order_by(Magazine.name)\
                       .all()

    return render_template('magazines.html', magazines=magazines)



# Miscellaneous routes


@app.route('/tags')
def tags():
    session = new_session()

    tags = session.query(Tag).all()

    return render_template('tags.html', tags=tags)


@app.route('/tag/<tagid>')
def tag(tagid):
    session = new_session()

    if tagid.isdigit():
        tag = session.query(Tag)\
                     .filter(Tag.id == tagid)\
                     .first()
    else:
        tag = session.query(Tag)\
                     .filter(Tag.name == tagid)\
                     .first()

    return render_template('tag.html', tag=tag)


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
    return render_template('print_books.html', editions=editions, works=works, print=1,
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
    # app.logger.debug(session.query(Person).join(BookPerson).filter(BookPerson.type
    #    == 'A').join(Book).filter(Book.pubseries_id.in_(pubseriesids)).order_by(Person.name))
    return render_template('myseries.html', pubseries=pubseries,
                           authors=authors)


@app.route('/search', methods=['POST', 'GET'])
def search():
    session = new_session()
    q = ''
    searchword = request.args.get('search', '')
    for k, v in request.args.items():
        app.logger.debug(k + " : " + v)
    app.logger.info("searchword: " + searchword)
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


@app.route('/search_form', methods=["POST", "GET"])
def search_form():
    session = new_session()

    form = SearchForm(request.form)
    editionnum = ''

    if request.method == 'GET':
        form.name = ''

    if request.method == 'POST':
        query = session.query(Work)
        query = query.join(Part, Part.work_id == Work.id)\
                     .join(Edition, Part.edition_id == Edition.id)\
                     .filter(Part.shortstory_id == None)\
                     .join(Author, Author.part_id == Part.id)\
                     .join(Person, Person.id == Author.person_id)\
                     .join(WorkGenre, WorkGenre.work_id == Work.id)\
                     .join(Genre, Genre.id == WorkGenre.genre_id)
        if form.work_name.data != '':
            query = query.filter(Work.title.ilike(form.work_name.data))
        if form.work_origname.data != '':
            query = query.filter(
                Work.orig_title.ilike(form.work_origname.data))
        if form.work_pubyear_after.data is not None:
            query = query.filter(Work.pubyear >= form.work_pubyear_after.data)
        if form.work_pubyear_before.data is not None:
            query = query.filter(Work.pubyear <= form.work_pubyear_before.data)
        if (form.work_genre.data is not None and len(form.work_genre.data) > 0):
            app.logger.debug(form.work_genre.data)
            if (form.work_genre.data[0] != '' and
                    form.work_genre.data[0] != 'none'):
                query = query.filter(Genre.abbr.in_([x for x in
                                                     form.work_genre.data]))

        if form.edition_pubyear_after.data is not None:
            query = query.filter(
                Edition.pubyear >= form.edition_pubyear_after.data)
        if form.edition_pubyear_before.data is not None:
            query = query.filter(
                Edition.pubyear <= form.edition_pubyear_before.data)
        if form.edition_editionnum.data is not None:
            query = query.filter(Edition.editionnum ==
                                 form.edition_editionnum.data)
            editionnum = form.edition_editionnum.data

        if form.author_name.data != '':
            query = query.filter(Person.name.ilike(form.author_name.data))
        if form.author_dob_after.data is not None:
            query = query.filter(Person.dob >= form.author_dob_after.data)
        if form.author_dob_before.data is not None:
            query = query.filter(Person.dob <= form.author_dob_before.data)
        if (form.author_nationality.data is not None and
                len(form.author_nationality.data) > 0):
            if (form.author_nationality.data[0] != '' and
                    form.author_nationality.data[0] != 'none'):
                if form.author_nationality.data[0] == 'foreign':
                    query = query.filter(Person.nationality != 'Suomi')
                else:
                    query = query.filter(Person.nationality.in_([x for x in
                                                                 form.author_nationality.data]))
        query = query.order_by(Work.creator_str)
        works = query.all()

        return render_template('books.html',
                               works=works)

    form.work_genre.choices = [('none', ''),
                               ('F', 'Fantasia'),
                               ('K', 'Kauhu'),
                               ('nF', 'Nuorten fantasia'),
                               ('nK', 'Nuorten kauhu'),
                               ('nSF', 'Nuorten science fiction'),
                               ('Paleof', 'Paleofantasia'),
                               ('PF', 'Poliittinen fiktio'),
                               ('SF', 'Science Fiction'),
                               ('VEH', 'Vaihtoehtoishistoria'),
                               ('kok', 'Kokoelmat'),
                               ('rajatap', 'Rajatapaus'),
                               ('eiSF', 'Ei science fictionia')]

    nationalities = session.query(Person.nationality)\
                           .distinct(Person.nationality)\
                           .order_by(Person.nationality)\
                           .all()

    nat_choices = [('none', ''), ('foreign', 'Ulkomaiset')] + \
                  [(x.nationality, x.nationality) for x in
                   nationalities if x.nationality is not None]
    form.author_nationality.choices = nat_choices

    # form.author_nationality.choices = [(x.nationality, x.nationality) for x in
    #                                   nationalities if x.nationality is not
    #                                   None]

    return render_template('search_adv.html',
                           form=form,
                           nationalities=nat_choices,
                           editionnum=editionnum)


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


@app.route('/missing_nationality')
def missing_nationality():
    session = new_session()

    missing = session.query(Person)\
                     .filter(Person.nationality == None)\
                     .order_by(Person.name)\
                     .all()

    return render_template('people.html', people=missing)




# Routes for auto complete functionality in forms

@app.route('/autocomp_story', methods=['POST'])
def autocomp_story() -> Response:
    search = request.form['q']
    session = new_session()

    if search:
        stories = session.query(ShortStory)\
                         .filter(ShortStory.title.ilike('%' + search + '%'))\
                         .order_by(ShortStory.title)\
                         .all()
        return Response(json.dumps([x.title for x in stories]))
    else:
        return Response(json.dumps(['']))


@app.route('/autocomp_bookseries', methods=['POST'])
def autocomp_bookseries() -> Response:
    search = request.form['q']

    if search:
        session = new_session()
        series = session.query(Bookseries)\
                        .filter(Bookseries.name.ilike('%' + search + '%'))\
                        .order_by(Bookseries.name)\
                        .all()
        return Response(json.dumps([x.name for x in series]))
    else:
        return Response(json.dumps(['']))


@app.route('/autocomp_pubseries', methods=['POST'])
def autocomp_pubseries() -> Response:
    search = request.form['q']

    if search:
        session = new_session()
        series = session.query(Pubseries)\
                        .filter(Pubseries.name.ilike('%' + search + '%'))\
                        .order_by(Pubseries.name)\
                        .all()
        return Response(json.dumps([x.name for x in series]))
    else:
        return Response(json.dumps(['']))


@app.route('/autocomp_publisher', methods=['POST'])
def autocomp_publisher() -> Response:
    search = request.form['q']

    if search:
        session = new_session()
        publishers = session.query(Publisher)\
                            .filter(Publisher.name.ilike('%' + search + '%'))\
                            .order_by(Publisher.name)\
                            .all()
        return Response(json.dumps([x.name for x in publishers]))
    else:
        return Response(json.dumps(['']))


@app.route('/autocomp_work', methods=['POST'])
def autocomp_work() -> Response:
    search = request.form['q']

    if search:
        session = new_session()
        works = session.query(Work)\
                       .filter(Work.title.ilike('%' + search + '%'))\
                       .order_by(Work.title)\
                       .all()
        return Response(json.dumps([x.title for x in works]))
    else:
        return Response(json.dumps(['']))


@app.route('/autocomp_edition', methods=['POST'])
def autocomp_edition() -> Response:
    search = request.form['q']

    if search:
        session = new_session()
        editions = session.query(Edition)\
            .filter(Edition.title.ilike('%' + search + '%'))\
            .order_by(Edition.title)\
            .all()
        return Response(json.dumps([x.title for x in editions]))
    else:
        return Response(json.dumps(['']))
