import logging

from flask import redirect, render_template, request, url_for

from app import app
from app.forms import MagazineForm
from app.orm_decl import (Magazine, Publisher, Issue)

from .route_helpers import *


@app.route('/magazine/<id>')
def magazine(id):
    session = new_session()
    magazine = session.query(Magazine)\
                      .filter(Magazine.id == id)\
                      .first()

    issues = session.query(Issue)\
                    .filter(Issue.magazine_id == id)\
                    .all()

    return render_template('magazine.html', magazine=magazine, issues=issues)


@app.route('/edit_magazine/<id>', methods=['GET', 'POST'])
def edit_magazine(id):
    session = new_session()

    form = MagazineForm(request.form)

    magazine = session.query(Magazine)\
                      .filter(Magazine.id == id)\
                      .first()

    publisher = session.query(Publisher)\
                       .filter(Publisher.id == magazine.publisher_id)\
                       .first()

    if request.method == 'GET':
        form.id.data = magazine.id
        form.name.data = magazine.name
        form.issn.data = magazine.issn
        form.description.data = magazine.description
        form.publisher.data = publisher.name
        form.link.data = magazine.link

    if form.validate_on_submit():
        publisher = session.query(Publisher)\
                           .filter(Publisher.name == form.publisher.data)\
                           .first()
        magazine.id = id
        magazine.name = form.name.data
        magazine.publisher_id = publisher.id
        magazine.issn = form.issn.data
        magazine.description = form.description.data
        magazine.link = form.link.data

        session.add(magazine)
        session.commit()

        return redirect(url_for('magazine', id=magazine.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_magazine.html', id=id, form=form)
