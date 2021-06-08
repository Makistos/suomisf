# -*- coding: utf-8 -*-
from app.orm_decl import (Work, Edition, Part, Person, Award,
                          AwardCategory, Awarded)
from app import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import os
import csv
from typing import Dict, List, Tuple
from importbib import missing_from_db


db_url = app.config['SQLALCHEMY_DATABASE_URI']

categories = {}
awards = {}


def get_categories(s):
    cats = s.query(AwardCategory).all()

    for cat in cats:
        categories[cat.name] = cat.id


def get_awards(s):
    aws = s.query(Award).all()

    for award in aws:
        awards[award.name] = award.id


def save_personal_award(s, line):
    award = line[1]
    name = line[4]

    if line[2]:
        year = int(line[2])
    else:
        year = None

    person = s.query(Person)\
              .filter(Person.name == name).first()

    if not person:
        print(f'Awarded person not found: {name}')
        return

    if award not in awards:
        print(f'Award not found: {award}')
        return

    awarded = Awarded(award_id=awards[award],
                      person_id=person.id,
                      year=year)

    try:
        s.add(awarded)
        s.commit()
    except Exception as e:
        print(f'Could not add personal award: {e}.')


def save_novel_award(s, line):
    award = line[1]
    cat = line[3]
    title = line[4]

    if line[2]:
        year = int(line[2])
    else:
        year = None

    work = s.query(Work)\
            .filter(Work.orig_title == title).first()

    if not work:
        print(f'Work not found: {title}')
        return

    if award not in awards:
        print(f'Award not found: {award}')
        return

    if cat not in categories:
        print(f'Category not found: {cat}')
        return

    awarded = Awarded(award_id=awards[award],
                      category_id=categories[cat],
                      year=year,
                      work_id=work.id)

    try:
        s.add(awarded)
        s.commit()
    except Exception as e:
        print(f'Could not add novel award: {e}.')


def save_story_award(s, line):
    pass


def import_awards():

    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)
    s = session()

    get_categories(s)
    get_awards(s)

    with open('bibfiles/awards.csv') as csvfile:
        awardscsv = csv.reader(csvfile, delimiter=';', quotechar='"')
        for award in awardscsv:
            if int(award[0]) == 0:
                save_personal_award(s, award)
            elif int(award[0]) == 1:
                save_novel_award(s, award)
            elif int(award[0]) == 2:
                save_story_award(s, award)
            else:
                print(f'Skipped {award}')


if __name__ == '__main__':
    import_awards()
