import time
from flask import render_template, request, flash, redirect, url_for,\
    make_response, jsonify, Response
from flask_login import current_user, login_user, logout_user
from app import app
from app.orm_decl import (Person, Work,
                          Edition, Pubseries, Bookseries, User, UserBook, ShortStory, UserPubseries,
                          Genre, WorkGenre, Tag, Award, Awarded,
                          Magazine, Issue, PublicationSize, Publisher, Part, ArticleTag,
                          Language, Country, Article, Contributor)
from sqlalchemy import func, text
from sqlalchemy.orm import sessionmaker
from app.forms import (LoginForm, RegistrationForm,
                       UserForm,
                       SearchForm, SearchBooksForm, SearchStoryForm)
from .route_helpers import *
# from app.forms import BookForm
from flask_sqlalchemy import get_debug_queries
import json
import logging
import pprint
import urllib
from typing import Dict, List, Any, Tuple


@app.route('/')
@app.route('/index')
def index():
    session = new_session()
    work_count = session.query(func.count(Work.id)).first()
    edition_count = session.query(func.count(Edition.id)).first()
    author_count = session.query(Contributor.person_id.distinct()).filter(
        Contributor.role_id == 1).all()
    pub_count = session.query(func.count(Publisher.id)).first()
    person_count = session.query(func.count(Person.id)).first()
    pubseries_count = session.query(func.count(Pubseries.id)).first()
    bookseries_count = session.query(func.count(Bookseries.id)).first()
    story_count = session.query(func.count(ShortStory.id)).first()
    magazine_count = session.query(func.count(Magazine.id)).first()
    issue_count = session.query(func.count(Issue.id)).first()
    article_count = session.query(func.count(Article.id)).first()
    return render_template('index.html', work_count=work_count,
                           edition_count=edition_count,
                           author_count=author_count,
                           pub_count=pub_count, person_count=person_count,
                           pubseries_count=pubseries_count,
                           bookseries_count=bookseries_count,
                           story_count=story_count,
                           magazine_count=magazine_count,
                           issue_count=issue_count,
                           article_count=article_count)


def redirect_url(default='index'):
    return request.args.get('next') or \
        request.referrer or \
        url_for(default)


@app.route('/bookindex', methods=['POST', 'GET'])
def bookindex() -> Any:
    session = new_session()
    times: List[float] = []
    times.append(time.time())

    form = SearchBooksForm(request.form)

    genres = session.query(Genre).all()
    form.genre.choices = [(0, '')]
    form.genre.choices += [(x.id, x.name) for x in genres]

    nationalities = session.query(Country).order_by(Country.name).all()
    form.nationality.choices = [(0, '')]
    form.nationality.choices += [(x.id, x.name) for x in nationalities]

    types = [(0, ''), (1, 'Romaani'), (2, 'Kokoelma')]
    form.type.choices = types

    if form.validate_on_submit():
        stmt = 'SELECT DISTINCT work.* FROM '
        tables = 'work, part'
        where = 'WHERE work.id = part.work_id '
        if form.title.data:
            where += " and work.title like '%" + form.title.data + "%' "
        if form.orig_title.data:
            where += " and work.orig_title like '%" + form.orig_title.data + "%' "
        if form.pubyear_start is not None or form.pubyear_end is not None:
            tables += ', edition '
            where += ' and part.edition_id = edition.id '
        if form.pubyear_start.data is not None:
            where += " and edition.pubyear >= " + str(form.pubyear_start.data)
        if form.pubyear_end.data is not None:
            where += " and edition.pubyear <= " + str(form.pubyear_end.data)
        if form.origyear_start.data is not None:
            where += " and work.pubyear >= " + str(form.origyear_start.data)
        if form.origyear_end.data is not None:
            where += " and work.pubyear <= " + str(form.origyear_end.data)
        if form.genre.data > 0:
            tables += ', workgenre '
            where += ' and workgenre.work_id = work.id '
            where += " and workgenre.genre_id = " + str(form.genre.data)
        if form.nationality.data > 0:
            tables += ', contributor, person '
            where += ' and part.id = contributor.part_id and contributor.person_id = person.id '
            where += ' and person.nationality_id = ' + \
                str(form.nationality.data)
        if form.type.data > 0:
            where += " and work.type = " + str(form.type.data)
        stmt += tables + where
        works_db = session.query(Work)\
            .from_statement(text(stmt))\
            .all()
        times.append(time.time())
        (works, count) = make_book_list(works_db, form.authorname.data)
        page = create_booklisting(works)
        times.append(time.time())
        for i in range(len(times)):
            app.logger.debug('Perf for bookindex:')
            app.logger.debug(f'Time {i}: {times[i] - times[0]}.')
            print(f'Time {i}: {times[i] - times[0]}.')
        return render_template('books.html', books=page, count=count)

    return render_template('bookindex.html', form=form)


@ app.route('/shortstoryindex', methods=['POST', 'GET'])
def shortstoryindex() -> Any:
    session = new_session()

    form = SearchStoryForm(request.form)

    if form.validate_on_submit():
        stmt = "SELECT DISTINCT shortstory.* FROM shortstory WHERE 1=1 "
        # if form.authorname.data:
        #     stmt += " AND shortstory.creator_str like '%" + form.authorname.data + "%'"
        if form.title.data:
            stmt += " AND shortstory.title like '%" + form.title.data + "%'"
        if form.orig_title.data:
            stmt += " AND shortstory.orig_title like '%" + form.orig_title.data + "&'"
        if form.origyear_start.data:
            stmt += " AND shortstory.pubyear >= " + \
                str(form.origyear_start.data)
        if form.origyear_end.data:
            stmt += " AND shortstory.pubyear <= " + str(form.origyear_end.data)
        stmt += " ORDER BY shortstory.title"
        stories = session.query(ShortStory)\
                         .from_statement(text(stmt))\
                         .all()
        if form.authorname.data:
            stories = [
                x for x in stories if form.authorname.data.lower() in x.author_str.lower()]

        return render_template('shortstories.html', stories=stories)

    return render_template('shortstoryindex.html', form=form)


# User related routes


@ app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session = new_session()
        user = session.query(User).filter_by(name=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Väärä käyttäjätunnus tai salasana')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect('/index')
    return render_template('login.html', title='Kirjaudu', form=form)


@ app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@ app.route('/register', methods=['GET', 'POST'])
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


@ app.route('/award/<awardid>')
def award(awardid: Any) -> Any:
    session = new_session()

    award = session.query(Award).filter(Award.id == awardid).first()
    awards = session.query(Awarded)\
        .filter(Awarded.award_id == awardid)\
        .all()

    return render_template('award.html', award=award, awards=awards)


@ app.route('/awards')
def awards() -> Any:
    session = new_session()

    awards = session.query(Award).all()

    return render_template('awards.html', awards=awards)


@ app.route('/stats')
def stats() -> Any:
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
            .join(Contributor)\
            .filter(Contributor.part_id == Part.id, Contributor.role_id == 1)\
            .join(Person, Person.id == Contributor.person_id)\
            .filter(Contributor.person_id == Person.id)\
            .filter(Genre.abbr == genre)\
            .filter(Part.shortstory_id == None)\
            .filter(Edition.editionnum == 1)\
            .group_by(Person.id)\
            .order_by(func.count(Work.id).desc())\
            .limit(10)\
            .all()

    translators = session.query(Person.name, func.count(Contributor.person_id).label('count'))\
                         .filter(Contributor.role_id == 2)\
                         .join(Contributor.parts)\
                         .join(Contributor.person)\
                         .filter(Part.shortstory_id == None)\
                         .group_by(Person.id)\
                         .order_by(func.count(Contributor.person_id).desc())\
                         .limit(20)\
                         .all()

    editors = session.query(Person.name, func.count(Contributor.person_id))\
                     .filter(Contributor.role_id == 3)\
                     .join(Contributor.parts)\
                     .join(Contributor.person)\
                     .filter(Part.shortstory_id == None)\
                     .group_by(Person.id)\
                     .order_by(func.count(Contributor.person_id).desc())\
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

    countries = session.query(Country.name, Person.nationality_id,
                              func.count(Person.nationality_id).label('count'))\
        .filter(Country.id == Person.nationality_id)\
        .group_by(Person.nationality_id)\
        .order_by(func.count(Person.nationality_id).desc())\
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
def magazines() -> Any:
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


@app.route('/tags_for_article/<articleid>')
def tags_for_article(articleid) -> Response:
    session = new_session()
    tags = session.query(Tag)\
        .join(ArticleTag)\
        .filter(Tag.id == ArticleTag.tag_id)\
        .filter(ArticleTag.article_id == articleid)\
        .all()

    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {}
            obj['id'] = str(tag.id)
            obj['text'] = tag.name
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/create_tag/<tagname>', methods=["GET"])
def create_tag(tagname) -> Response:

    session = new_session()

    tag = Tag(name=tagname)
    session.add(tag)
    session.commit()

    return Response(json.dumps([tag.id]))


@app.route('/select_tags', methods=["GET"])
def select_tags() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        tags = session.query(Tag)\
            .filter(Tag.name.ilike('%' + search + '%'))\
            .order_by(Tag.name)\
            .all()

        retval['results'] = []
        for tag in tags:
            retval['results'].append({'id': str(tag.id), 'text': tag.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


# @app.route('/save_tags_to_article/', methods=["POST", "GET"])
# @login_required
# @admin_required
# def save_tags_to_article():
#     articleid, tag_ids = get_select_ids(request.form, 'article')
#     # if ('items' not in request.form or 'article' not in request.form):
#     #     abort(400)

#     # articleid = json.loads(request.form['article'])
#     # tag_ids = json.loads(request.form['items'])

#     # tag_ids = [int(x['id']) for x in tag_ids]

#     session = new_session()

#     existing_tags  = session.query(ArticleTag)\
#                             .filter(ArticleTag.article_id == articleid)\
#                             .all()
#     (to_add, to_delete) = get_join_changes([str(x.id) for x in existing_tags], tag_ids)

#     for tag in to_delete:
#         old_tag = session.query(ArticleTag)\
#                          .filter(articleid=articleid, tag_id=tag)\
#                          .first()
#         session.delete(old_tag)

#     for tag in to_add:
#         new_tag = ArticleTag(articleid=articleid, tag_id=tag)
#         session.add(new_tag)

#     session.commit()

#     msg = 'Tallennus onnistui'
#     category = 'success'
#     resp = {'feedback': msg, 'category': category}
#     return make_response(jsonify(resp), 200)


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
                       .order_by(Work.author_str)\
                       .all()
        series = session.query(Bookseries).filter(Bookseries.id == id).first()
        title = series.name
    elif type == 'books':
        editions = None
        series = None
        if letter:
            works = session.query(Work)\
                           .filter(Work.author_str.like(letter + '%'))\
                           .order_by(Work.author_str)\
                           .all()
            title = letter
        else:
            works = session.query(Work)\
                           .order_by(Work.author_str)\
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
        .join(Contributor, Contributor.role_id == 1)\
        .filter(Contributor.part_id == Part.id)\
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
                     .join(Contributor, Contributor.role_id == 1)\
                     .filter(Contributor.person_id == Person.id)\
                     .join(Part)\
                     .filter(Contributor.part_id == Part.id)\
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
def search_form() -> Any:
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
                     .join(Contributor, Contributor.part_id == Part.id, Contributor.role_id == 1)\
                     .join(Person, Person.id == Contributor.person_id)\
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
                    query = query.filter(Person.nationality_id != 'Suomi')
                else:
                    query = query.filter(Person.nationality_id.in_([x for x in
                                                                    form.author_nationality.data]))
        query = query.order_by(Work.author_str)
        works_db = query.all()

        (works, count) = make_book_list(works_db, form.authorname.data)
        page = create_booklisting(works)
        return render_template('books.html',
                               books=page, count=count)

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

    nationalities = session.query(Person.nationality_id)\
                           .distinct(Person.nationality_id)\
                           .order_by(Person.nationality_id)\
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
                     .filter(Person.nationality_id == None)\
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


@app.route('/select_size', methods=['GET'])
def select_size() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        sizes = session.query(PublicationSize)\
            .filter(PublicationSize.name.ilike('%' + search + '%'))\
            .order_by(PublicationSize.name)\
            .all()

        retval['results'] = []
        if sizes:
            for size in sizes:
                retval['results'].append({'id': size.id, 'text': size.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/select_pubseries', methods=['GET'])
def select_pubseries() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        pubseries = session.query(Pubseries)\
                           .filter(Pubseries.name.ilike('%' + search + '%'))\
                           .order_by(Pubseries.name)\
                           .first()

        retval['results'] = []
        if pubseries:
            retval['results'].append(
                {'id': pubseries.id, 'text': pubseries.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/select_bookseries', methods=['GET'])
def select_bookseries() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        bookseries = session.query(Bookseries)\
            .filter(Bookseries.name.ilike('%' + search + '%'))\
            .order_by(Bookseries.name)\
            .first()

        retval['results'] = []
        if bookseries:
            retval['results'].append(
                {'id': bookseries.id, 'text': bookseries.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/select_genre', methods=['GET'])
def select_genre() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        genres = session.query(Genre)\
                        .filter(Genre.name.ilike('%' + search + '%'))\
                        .order_by(Genre.name)\
                        .all()
        retval['results'] = []
        if genres:
            for genre in genres:
                retval['results'].append({'id': genre.id, 'text': genre.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/select_language', methods=['GET'])
def select_language() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        languages = session.query(Language)\
                           .filter(Language.name.ilike('%' + search + '%'))\
                           .order_by(Language.name)\
                           .all()
        retval['results'] = []
        if languages:
            for language in languages:
                retval['results'].append(
                    {'id': language.id, 'text': language.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/select_country', methods=['GET'])
def select_country() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        countries = session.query(Country)\
            .filter(Country.name.ilike('%' + search + '%'))\
            .order_by(Country.name)\
            .all()

        retval['results'] = []
        if countries:
            for country in countries:
                retval['results'].append(
                    {'id': str(country.id), 'text': country.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))
