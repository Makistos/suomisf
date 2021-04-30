import logging

from flask import (redirect, render_template, request,
                   url_for, make_response, jsonify, Response)
from flask.globals import session
from flask_login import login_required, current_user
from sqlalchemy.util.langhelpers import ellipses_string

from app import app
from app.forms import IssueForm
from app.orm_decl import (
    Issue, IssueContent, IssueEditor, IssueTag, Magazine, Person, Tag, Editor,
    Article, ShortStory)

from .route_helpers import *
from typing import Any, List, Dict
import json


@app.route('/issue/<id>', methods=['POST', 'GET'])
def issue(id: Any) -> Any:

    session = new_session()

    issue = session.query(Issue)\
                   .filter(Issue.id == id)\
                   .first()

    form = IssueForm(request.form)

    if request.method == 'GET':
        form.id.data = issue.id
        form.number.data = issue.number
        form.number_extra.data = issue.number_extra
        form.count.data = issue.count
        form.year.data = issue.year
        form.link.data = issue.link
        form.notes.data = issue.notes
        form.title.data = issue.title
    elif form.validate_on_submit():
        issue.number = form.number.data
        issue.number_extra = form.number_extra.data
        issue.count = form.count.data
        issue.year = form.year.data
        issue.link = form.link.data
        issue.notes = form.notes.data
        issue.title = form.title.data
        session.add(issue)
        session.commit()
        log_change(session, 'Issue', issue.id)
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')

    return render_template('issue.html', issue=issue, form=form)


@app.route('/add_issue/<magazine_id>', methods=['GET', 'POST'])
def add_issue(magazine_id):
    session = new_session()

    issue = Issue()

    form = IssueForm(request.form)
    sizes = size_list(session)
    form.size.choices = sizes
    form.size.default = "0"

    magazine = session.query(Magazine)\
                      .filter(Magazine.id == magazine_id)\
                      .first()

    if form.validate_on_submit():
        issue.magazine_id = magazine_id
        issue.number = form.number.data
        issue.number_extra = form.number_extra.data
        issue.count = form.count.data
        issue.year = form.year.data
        issue.image_src = form.image_src.data
        issue.pages = form.pages.data
        issue.link = form.link.data
        issue.notes = form.notes.data
        if form.size.data != '':
            issue.size_id = int(form.size.data)
        else:
            issue.size = None

        session.add(issue)
        session.commit()

        if form.editor.data != '':
            person = session.query(Person)\
                            .filter(Person.name == form.editor.data)\
                            .first()
            ie = session.query(IssueEditor)\
                        .filter(IssueEditor.issue_id == issue.id)\
                        .first()
            if not ie:
                ie = IssueEditor(person_id=person.id,
                                 issue_id=issue.id)
            else:
                ie.person_id = person.id
            session.add(ie)
            session.commit()

        return redirect(url_for('issue', id=issue.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_issue.html',
                           form=form,
                           magazine_name=magazine.name,
                           issueid=0,
                           selected_size='0')


@app.route('/edit_issue/<id>', methods=['GET', 'POST'])
def edit_issue(id):
    session = new_session()

    if id != '0':
        issue = session.query(Issue).filter(Issue.id == id).first()
    else:
        issue = Issue()

    form = IssueForm(request.form)
    sizes = size_list(session)
    form.size.choices = sizes
    form.size.default = "0"

    magazine = session.query(Magazine)\
                      .join(Issue)\
                      .filter(Magazine.id == Issue.magazine_id,
                              Issue.id == id)\
                      .first()
    if magazine:
        magazine_name = magazine.name
    else:
        magazine_name = ''

    if request.method == 'GET':
        if issue.size_id:
            size = str(issue.size_id)
        else:
            size = ''
        editors = session.query(Person)\
                         .join(IssueEditor)\
                         .filter(IssueEditor.issue_id == id)\
                         .all()
        editor_str = ', '.join([x.name for x in editors])
        form.editor.data = editor_str
        form.number.data = issue.number
        form.number_extra.data = issue.number_extra
        form.count.data = issue.count
        form.year.data = issue.year
        form.image_src.data = issue.image_src
        form.pages.data = issue.pages
        form.link.data = issue.link
        form.notes.data = issue.notes

    if form.validate_on_submit():
        # if len(form.size.data) > 0:
        #    size = session.query(PublicationSize.id)\
        #                  .filter(PublicationSize.name == form.size.data)\
        #                  .first()
        # else:
        #    size = None
        issue.number = form.number.data
        issue.number_extra = form.number_extra.data
        issue.count = form.count.data
        issue.year = form.year.data
        issue.image_src = form.image_src.data
        issue.pages = form.pages.data
        issue.link = form.link.data
        issue.notes = form.notes.data
        if form.size.data != '':
            issue.size_id = int(form.size.data)
        else:
            issue.size = None

        session.add(issue)
        session.commit()

        if form.editor.data != '':
            person = session.query(Person)\
                            .filter(Person.name == form.editor.data)\
                            .first()
            ie = session.query(IssueEditor)\
                        .filter(IssueEditor.issue_id == issue.id)\
                        .first()
            if not ie:
                ie = IssueEditor(person_id=person.id,
                                 issue_id=issue.id)
            else:
                ie.person_id = person.id
            session.add(ie)
            session.commit()

        return redirect(url_for('issue', id=issue.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_issue.html',
                           form=form,
                           magazine_name=magazine_name,
                           issueid=issue.id,
                           selected_size=size)


def save_newarticle_to_issue(session, issueid, form):
    pass


def save_article_to_issue(session, issueid, form):
    pass


def remove_article_from_issue(session, articleid, issueid):
    pass


@app.route('/save_magazine_to_issue', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_magazine_to_issue() -> Response:
    session = new_session()
    (issueid, magazine_ids) = get_select_ids(request.form)
    issue = session.query(Issue).filter(Issue.id == issueid).first()
    if issue:
        issue.magazine_id = magazine_ids[0]
        session.add(issue)
        session.commit()
        msg = 'Tallennus onnistui'
        category = 'success'
        resp = {'feedback': msg, 'category': category}
        return make_response(jsonify(resp), 200)
    msg = 'Tallennus epäonnistui'
    category = 'failure'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 418)


@app.route('/magazine_for_issue/<issue_id>')
def magazine_for_issue(issue_id: Any) -> Response:
    session = new_session()
    magazine = session.query(Magazine)\
                      .join(Issue)\
                      .filter(Magazine.id == Issue.magazine_id)\
                      .filter(Issue.id == issue_id)\
                      .first()
    retval: List[Dict[str, str]] = []
    if magazine:
        obj: Dict[str, str] = {'id': magazine.id, 'text': magazine.name}
        retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_tags_to_issue', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_tags_to_issue() -> Response:
    session = new_session()
    (issueid, tag_ids) = get_select_ids(request.form)
    existing_tags = session.query(IssueTag)\
                           .filter(IssueTag.issue_id == issueid)\
                           .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_if for x in existing_tags], [int(x['id']) for x in tag_ids])

    for id in to_remove:
        it = session.query(IssueTag)\
                    .filter(IssueTag.issue_id == issueid, IssueTag.tag_id == id)\
                    .first()
        session.delete(it)
    for id in to_add:
        it = IssueTag(issue_id=issueid, tag_id=id)
        session.add(it)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/tags_for_issue/<issueid>')
def tags_for_issue(issueid: Any) -> Response:
    session = new_session()
    tags = session.query(Tag)\
                  .join(IssueTag)\
                  .filter(Tag.id == IssueTag.tag_id)\
                  .filter(IssueTag.issue_id == issueid)\
                  .all()
    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {'id': tag.id, 'text': tag.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_editors_to_issue', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_editors_to_issue() -> Response:
    session = new_session()
    (issueid, person_ids) = get_select_ids(request.form)
    existing_editors = session.query(IssueEditor)\
        .filter(IssueEditor.issue_id == issueid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_if for x in existing_editors], [int(x['id']) for x in person_ids])

    for id in to_remove:
        it = session.query(IssueEditor)\
                    .filter(IssueEditor.issue_id == issueid, IssueEditor.person_id == id)\
                    .first()
        session.delete(it)
    for id in to_add:
        it = IssueEditor(issue_id=issueid, person_id=id)
        session.add(it)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/editors_for_issue/<issueid>')
def editors_for_issue(issueid: Any) -> Response:
    session = new_session()
    editors = session.query(Person)\
                     .join(IssueEditor)\
                     .filter(IssueEditor.issue_id == issueid)\
                     .filter(IssueEditor.person_id == Person.id)\
                     .all()

    retval: List[Dict[str, str]] = []
    if editors:
        for person in editors:
            obj: Dict[str, str] = {'id': person.id, 'text': person.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_size_to_issue', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_size_to_issue() -> Response:
    session = new_session()
    (issueid, size_ids) = get_select_ids(request.form)

    issue = session.query(Issue).filter(Issue.id == issueid).first()
    issue.size = size_ids[0]
    session.add(issue)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/articles_for_issue/<issueid>')
def articles_for_issue(issueid: Any) -> Response:
    session = new_session()

    articles = session.query(Article)\
                      .join(IssueContent)\
                      .filter(IssueContent.issue_id == issueid)\
                      .filter(IssueContent.article_id == Article.id)\
                      .all()
    retval: List[Dict[str, str]] = []

    if articles:
        for article in articles:
            obj: Dict[str, str] = {'id': article.id, 'text': article.title}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_article_to_story', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_article_to_story() -> Response:
    session = new_session()
    (issueid, article_ids) = get_select_ids(request.form)

    issue = session.query(Issue).filter(Issue.id == issueid).first()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/save_stories_to_story', methods=['POST'])
@admin_required
@login_required  # type: ignore
def save_stories_to_story() -> Response:
    session = new_session()
    (issueid, story_ids) = get_select_ids(request.form)

    issue = session.query(Issue).filter(Issue.id == issueid).first()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/stories_for_issue/<issueid>')
def stories_for_issue(issueid: Any) -> Response:
    session = new_session()

    stories = session.query(ShortStory)\
                     .join(IssueContent)\
                     .filter(IssueContent.issue_id == issueid)\
                     .filter(IssueContent.shortstory_id == ShortStory.id)\
                     .all()

    retval: List[Dict[str, str]] = []
    if stories:
        for story in stories:
            txt = story.creator_str + ':' + story.title
            obj: Dict[str, str] = {'id': story.id, 'text': txt}
            retval.append(obj)
    return Response(json.dumps(retval))
