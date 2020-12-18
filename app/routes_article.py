import logging

from flask import (redirect, render_template, request, url_for, Response, session, abort)
from flask_login import login_required, current_user
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
@login_required
def edit_article(id):
    if not current_user.is_admin:
        abort(401)

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
    if form.validate_on_submit():
        article.title = form.title.data
        session.add(article)
        session.commit()
        return redirect(url_for('article', id=article.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_article.html', form=form)


@app.route('/add_article/<article_id>/<issue_id>')
@login_required
def add_article(article_id, issue_id):
    if not current_user.is_admin:
        abort(401)

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
    if not current_user.is_admin:
        return redirect(url_for('article', id=articleid))

    author = session.query(Person)\
                    .filter(Person.name == authorname)\
                    .first()
    if author:
        auth = ArticleAuthor(article_id=articleid, author_id=author.id)
        session.add(auth)
        session.commit()


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
    

def save_person_to_article(session, articleid, personname):
    if not current_user.is_admin:
        return redirect(url_for('article', id=articleid))

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
@login_required
def save_article_authors() -> Response:

    if ('items' not in request.form or 'article' not in request.form):
        abort(400)

    articleid = json.loads(request.form['article'])
    
    if not current_user.is_admin:
        abort(401)
    
    author_ids = json.loads(request.form['items'])
    if len(author_ids) == 0:
        # Required field
        return Response(json.dumps(['']))
    author_ids = [int(x['id']) for x in author_ids]
    
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
        author_article = ArticleAuthor(article_id=articleid, person_id=person.id)
        session.add(author_article)


    session.commit()

    return Response(json.dumps(['OK']))


@app.route ('/save_article_people/', methods=["POST"])
@login_required
def save_article_people() -> Response:

    if not 'items' in request.form or 'article' not in request.form:
        return abort(400)

    articleid = json.loads(request.form['article'])

    if not current_user.is_admin:
        abort(401)

    people_ids = json.loads(request.form['items'])
    people_ids = [int(x['id']) for x in people_ids]

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

def create_new_tags(session, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    retval: List[Dict[str, Any]] = []

    for tag in tags:
        id = int(tag['id'])
        name = tag['text']
        if id == 0:
            new_tag = Tag(name=name)
            session.add(new_tag)
            session.commit()
            id = new_tag.id
            name = new_tag.name
        retval.append({'id': id, 'text': name})
    
    return retval

@app.route('/save_article_tags/', methods=["POST"])
@login_required
def save_article_tags() -> Response:

    if not 'items' in request.form or 'article' not in request.form:
        return abort(400)
    articleid = json.loads(request.form['article'])
    if not current_user.is_admin:
        abort(401)

    tag_ids = json.loads(request.form['items'])
    session = new_session()
    tag_ids = create_new_tags(session, tag_ids)


    existing_tags = session.query(ArticleTag)\
                             .filter(ArticleTag.article_id == articleid)\
                             .all()
    if existing_tags:
        for existing in existing_tags:
            if existing.tag_id in tag_ids:
                # Exists in db, exists in selection
                tag_ids.remove(existing.tag_id)
            else:
                # Exists in db, not in selection so remove from db.
                session.delete(existing)
    for new_tag in tag_ids:
        tag = session.query(Tag)\
                        .filter(Tag.id == new_tag['id'])\
                        .first()
        article_tag = ArticleTag(article_id=articleid, tag_id=tag.id)
        session.add(article_tag)

    session.commit()

    return Response(json.dumps(['OK']))