import logging

from flask import (redirect, render_template, request, url_for,
                   Response, session, abort, make_response, jsonify)
from flask_login import login_required, current_user
from flask_wtf import csrf
from app import app
from app.forms import ArticleForm
from app.orm_decl import (Article, ArticleAuthor, ArticleLink, ArticlePerson,
                          ArticleTag, Person, Tag)

from .route_helpers import *
import json
from typing import List, Dict, Any

# @app.route('/article/<id>', methods=['GET'])
# def article(id):
#     session = new_session()

#     article = session.query(Article)\
#                      .filter(Article.id == id)\
#                      .first()

#     authors = session.query(Person)\
#                      .join(ArticleAuthor)\
#                      .filter(ArticleAuthor.article_id == id)\
#                      .all()

#     people = session.query(Person)\
#                     .join(ArticlePerson)\
#                     .filter(ArticlePerson.article_id == id)\
#                     .all()

#     form = ArticleForm(request.form)

#     if request.method == 'GET':
#         form.title.data = article.title

#     return render_template('article.html',
#                            article=article,
#                            authors=authors,
#                            people=people,
#                            form=form)


@app.route('/article/<id>', methods=['POST', 'GET'])
def article(id: Any) -> Any:
    session = new_session()

    article = session.query(Article)\
                     .filter(Article.id == id)\
                     .first()

    authors = session.query(Person)\
                     .join(ArticleAuthor)\
                     .filter(ArticleAuthor.article_id == id)\
                     .all()

    people = session.query(Person)\
                    .join(ArticlePerson)\
                    .filter(ArticlePerson.article_id == id)\
                    .all()
    links = session.query(ArticleLink)\
                   .filter(ArticleLink.article_id == id)\
                   .all()

    form = ArticleForm(request.form)

    if request.method == 'GET':
        form.id.data = article.id
        form.title.data = article.title

    elif form.validate_on_submit():
        article.title = form.title.data
        session.add(article)
        session.commit()
        log_change(session, 'Article', article.id)
    else:
        app.logger.debug("Errors: {}".format(form.errors))
        print("Errors: {}".format(form.errors))

    return render_template('article.html',
                           article=article,
                           authors=authors,
                           people=people,
                           links=links,
                           form=form)


@app.route('/edit_article/<id>', methods=['GET', 'POST'])
@login_required  # type: ignore
def edit_article(id: Any) -> Any:
    if not current_user.is_admin:
        abort(401)

    session = new_session()

    article = session.query(Article)\
                     .filter(Article.id == id)\
                     .first()

    authors = session.query(Person)\
                     .join(ArticleAuthor)\
                     .filter(ArticleAuthor.article_id == id)\
                     .all()

    people = session.query(Person)\
                    .join(ArticlePerson)\
                    .filter(ArticlePerson.article_id == id)\
                    .all()
    links = session.query(ArticleLink)\
                   .filter(ArticleLink.article_id == id)\
                   .all()

    form = ArticleForm(request.form)

    if request.method == 'GET':
        tags = session.query(Tag.name)\
                      .join(ArticleTag)\
                      .filter(Tag.id == ArticleTag.tag_id)\
                      .filter(ArticleTag.article_id == id)\
                      .all()

        form.title.data = article.title
    if form.validate_on_submit():
        article.title = form.title.data
        session.add(article)
        session.commit()
        return redirect(url_for('article', id=article.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('article.html',
                           form=form,
                           article=article,
                           authors=authors,
                           people=people,
                           links=links)


@app.route('/add_article/<article_id>/<issue_id>')
@login_required  # type: ignore
def add_article(article_id, issue_id):
    if not current_user.is_admin:
        abort(401)

    session = new_session()

    article = Article()

    form = ArticleForm()

    if form.validate_on_submit():
        article.title = form.title.data
        session.add(article)
        session.commit()

        author = session.query(Person)\
                        .filter(Person.name == form.author.data)\
                        .first()
        auth = ArticleAuthor(article_id=article.id, person_id=author.id)
        session.add(auth)
        session.commit()

        save_tags(session, form.tags.data, "Article", article.id)

        return render_template('article', article_id=article.id)
    else:
        app.logger.debug("pubid={}".format(form.pubseries.data))
        app.logger.debug("Errors: {}".format(form.errors))

    return render_template('edit_article.html', form=form)


# def save_author_to_article(session, articleid, authorname):
#     if not current_user.is_admin:
#         return redirect(url_for('article', id=articleid))

#     author = session.query(Person)\
#                     .filter(Person.name == authorname)\
#                     .first()
#     if author:
#         auth = ArticleAuthor(article_id=articleid, author_id=author.id)
#         session.add(auth)
#         session.commit()


def remove_author_from_article(session, articleid, authorname):
    if not current_user.is_admin:
        return redirect(url_for('article', id=articleid))

    author = session.query(ArticleAuthor)\
                    .join(Person)\
                    .filter(Person.name == authorname)\
                    .filter(ArticleAuthor.article_id == articleid)\
                    .filter(ArticleAuthor.person_id == Person.id)\
                    .first()
    if author:
        session.delete(author)
        session.commit()


@login_required  # type: ignore
@admin_required
def save_person_to_article(session, articleid, personname):

    person = session.query(Person)\
                    .filter(Person.name == personname)\
                    .first()

    if person:
        pers = ArticlePerson(article_id=articleid, person_id=person.id)
        session.add(pers)
        session.commit()


def remove_person_from_article(session, articleid, personname):
    if not current_user.is_admin:
        return redirect(url_for('article', id=articleid))

    person = session.query(ArticlePerson)\
                    .join(Person)\
                    .filter(Person.name == personname)\
                    .filter(ArticlePerson.article_id == articleid)\
                    .filter(ArticlePerson.person_id == Person.id)\
                    .first()

    if person:
        session.delete(person)
        session.commit()


def add_link_to_article(session, articleid, form):
    link = ArticleLink(article_id=articleid, link=form.link.data,
                       description=form.description.data)

    session.add(link)
    session.commit()


def remove_link_from_article(session, linkid):
    link = session.query(ArticleLink)\
                  .filter(ArticleLink.id == linkid)\
                  .first()
    session.delete(link)
    session.commit()


def update_article_creators(session, articleid):
    pass


@app.route('/save_authors_to_article', methods=["POST", "GET"])
@login_required  # type: ignore
@admin_required
def save_authors_to_article() -> Any:

    (articleid, author_ids) = get_select_ids(request.form)

    session = new_session()

    existing_people = session.query(ArticleAuthor)\
                             .filter(ArticleAuthor.article_id == articleid)\
                             .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people], [int(x['id']) for x in author_ids])

    for id in to_remove:
        aa = session.query(ArticleAuthor)\
                    .filter(ArticleAuthor.article_id == articleid, ArticleAuthor.person_id == id)\
                    .first()
        session.delete(aa)
    for id in to_add:
        aa = ArticleAuthor(article_id=articleid, person_id=id)
        session.add(aa)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/save_people_to_article', methods=["POST"])
@login_required  # type: ignore
@admin_required
def save_people_to_article() -> Any:

    (articleid, people_ids) = get_select_ids(request.form)

    session = new_session()

    existing_people = session.query(ArticlePerson)\
                             .filter(ArticlePerson.article_id == articleid)\
                             .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people], [int(x['id']) for x in people_ids])

    for id in to_remove:
        aa = session.query(ArticlePerson)\
                    .filter(ArticlePerson.article_id == articleid, ArticlePerson.person_id == id)\
                    .first()
        session.delete(aa)
    for id in to_add:
        aa = ArticlePerson(article_id=articleid, person_id=id)
        session.add(aa)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/save_tags_to_article', methods=["POST"])
@login_required  # type: ignore
@admin_required
def save_tags_to_article() -> Any:

    (articleid, tag_ids) = get_select_ids(request.form)

    session = new_session()
    tag_ids = create_new_tags(session, tag_ids)

    existing_tags = session.query(ArticleTag)\
        .filter(ArticleTag.article_id == articleid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_id for x in existing_tags], [int(x['id']) for x in tag_ids])

    for id in to_remove:
        at = session.query(ArticleTag)\
                    .filter(ArticleTag.article_id == articleid, ArticleTag.tag_id == id)\
                    .first()
        session.delete(at)
    for id in to_add:
        at = ArticleTag(article_id=articleid, tag_id=id)
        session.add(at)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/authors_for_article/<articleid>')
def authors_for_article(articleid: Any) -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(ArticleAuthor)\
                    .filter(Person.id == ArticleAuthor.person_id)\
                    .filter(ArticleAuthor.article_id == articleid)\
                    .all()

    retval: List[Dict[str, str]] = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/people_for_article/<articleid>')
def people_for_article(articleid: Any) -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(ArticlePerson)\
                    .filter(Person.id == ArticlePerson.person_id)\
                    .filter(ArticlePerson.article_id == articleid)\
                    .all()

    retval: List[Dict[str, str]] = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))
