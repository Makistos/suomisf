import logging

from flask import redirect, render_template, request, url_for, Response

from app import app
from app.forms import ArticleForm
from app.orm_decl import (Article, ArticleAuthor, ArticleLink, ArticlePerson,
                          ArticleTag, Person, Tag)

from .route_helpers import *
import json

@app.route('/article/<id>')
def article(id):
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
    return render_template('article.html',
                           article=article,
                           authors=authors,
                           people=people)


@app.route('/edit_article/<id>', methods=['GET', 'POST'])
def edit_article(id):
    session = new_session()

    article = session.query(Article)\
                     .filter(Article.id == id)\
                     .first()

    form = ArticleForm(request.form)

    if request.method == 'GET':
        tags = session.query(Tag.name)\
                      .join(ArticleTag)\
                      .filter(Tag.id == ArticleTag.tag_id)\
                      .filter(ArticleTag.article_id == id)\
                      .all()

        form.title.data = article.title
        form.tags.data = ','.join([x.name for x in tags])
    if form.validate_on_submit():
        article.title = form.title.data
        session.add(article)
        session.commit()
        save_tags(session, form.tags.data, "Article", article.id)
        return redirect(url_for('article', id=article.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_article.html', form=form)


@app.route('/add_article/<article_id>/<issue_id>')
def add_article(article_id, issue_id):
    session = new_session()

    article = Article()

    form = ArticleForm()

    if form.validate_on_submit():
        article.title = form.title.data
        article.creator_str = form.author.data
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


def save_author_to_article(session, articleid, authorname):
    author = session.query(Person)\
                    .filter(Person.name == authorname)\
                    .first()
    if author:
        auth = ArticleAuthor(article_id=articleid, author_id=author.id)
        session.add(auth)
        session.commit()


def remove_author_from_article(session, articleid, authorname):
    author = session.query(ArticleAuthor)\
                    .join(Person)\
                    .filter(Person.name == authorname)\
                    .filter(ArticleAuthor.article_id == articleid)\
                    .filter(ArticleAuthor.person_id == Person.id)\
                    .first()
    if author:
        session.delete(author)
        session.commit()
    

def save_person_to_article(session, articleid, personname):
    person = session.query(Person)\
                    .filter(Person.name == personname)\
                    .first()

    if person:
        pers = ArticlePerson(article_id=articleid, person_id=person.id)
        session.add(pers)
        session.commit()
    

def remove_person_from_article(session, articleid, personname):
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
    link = ArticleLink(article_id=articleid, link=form.link.data, description=form.description.data)

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

@app.route('/save_article_authors/', methods=["POST"])
def save_article_authors() -> Response:
    if 'items' not in request.form or 'article' not in request.form:
        return Response(json.dumps(['']))

    author_ids = json.loads(request.form['items'])
    author_ids = [int(x) for x in author_ids]
    articleid = json.loads(request.form['article'])
    
    session = new_session()
    
    existing_people = session.query(ArticleAuthor)\
                             .filter(ArticleAuthor.article_id == articleid)\
                             .all()
    if existing_people:
        for existing in existing_people:
            if existing.person_id in author_ids:
                # Exists in db, exists in selection
                author_ids.remove(existing.person_id)
            else:
                # Exists in db, not in selection so remove from db.
                session.delete(existing)
    for new_person in author_ids:
        person = session.query(Person)\
                        .filter(Person.id == new_person)\
                        .first()
        author_article = ArticleAuthor(article_id=articleid, author_id=person.id)
        session.add(author_article)


    session.commit()

    return Response(json.dumps(['OK']))


@app.route ('/save_article_people/', methods=["POST"])
def save_article_people() -> Response:
    if not 'items' in request.form or 'article' not in request.form:
        return Response(json.dumps(['']))
    people_ids = json.loads(request.form['items'])
    people_ids = [int(x) for x in people_ids]
    articleid = json.loads(request.form['article'])
    app.logger.debug(people_ids)
    app.logger.debug(articleid)

    session = new_session()

    existing_people = session.query(ArticlePerson)\
                             .filter(ArticlePerson.article_id == articleid)\
                             .all()
    if existing_people:
        for existing in existing_people:
            if existing.person_id in people_ids:
                # Exists in db, exists in selection
                people_ids.remove(existing.person_id)
            else:
                # Exists in db, not in selection so remove from db.
                session.delete(existing)
    for new_person in people_ids:
        person = session.query(Person)\
                        .filter(Person.id == new_person)\
                        .first()
        person_article = ArticlePerson(article_id=articleid, person_id=person.id)
        session.add(person_article)

    session.commit()

    return Response(json.dumps(['OK']))