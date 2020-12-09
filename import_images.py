import csv
from app.orm_decl import (Work, Edition, Part, Author, Person)
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import List
db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///suomisf.db'

just_check: bool = False

img_dir = '/static/images/books/'
def add_image(s, image: List[str]) -> None:
    image_src = img_dir + image[0]
    author_str = image[1]
    title_str = image[2]

    editions = s.query(Edition)\
                .filter(Edition.title == title_str)\
                .join(Part)\
                .filter(Part.edition_id == Edition.id)\
                .join(Author)\
                .filter(Author.part_id == Part.id)\
                .join(Person)\
                .filter(Person.id == Author.person_id)\
                .filter(Person.name.like(author_str + '%'))\
                .all()

    if not editions:
        print(f'Not found: {author_str}: {title_str}.')
        return
    else:
        print(f'Found: {author_str}: {title_str}')
    if just_check == False:
        for edition in editions:
            edition.image_src = image_src
            s.add(edition)
        s.commit()

def import_images(params) -> None:
    engine = create_engine(db_url)
    session = sessionmaker()
    session.configure(bind=engine)
    s = session()

    if len(params) > 0:
        just_check = True

    with open('bibfiles/covers.csv') as csvfile:
        imagescsv = csv.reader(csvfile, delimiter=';', quotechar='"')
        for image in imagescsv:
            add_image(s, image)

if __name__ == '__main__':
    import_images(sys.argv[1:])
