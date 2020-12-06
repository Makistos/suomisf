import logging

from flask import redirect, render_template, request, url_for

from app import app
from app.forms import IssueForm
from app.orm_decl import (Issue, IssueContent, IssueEditor, IssueTag, Magazine)

from .route_helpers import *


@app.route('/issue/<id>')
def issue(id):

    session = new_session()

    issue = session.query(Issue)\
                   .filter(Issue.id == id)\
                   .first()

    return render_template('issue.html', issue=issue)


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
