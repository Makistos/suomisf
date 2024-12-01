"""
Script for moving data from article table to shortstory table
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import dotenv
directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(directory_path)
import app.orm_decl as db

dotenv.load_dotenv(os.path.join(directory_path, '../.env'))

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

articles = session.query(db.Article).all()

for article in articles:
    try:
        story = db.ShortStory()
        story.title = article.title
        story.excerpt = article.excerpt
        story.story_type = 7

        # Save new story, flush only so we can rollback if needed
        session.add(story)
        session.flush()

        part = db.Part()
        part.shortstory_id = story.id
        session.add(part)
        session.flush()

        authors = session.query(db.ArticleAuthor)\
            .filter_by(article_id=article.id).all()

        for author in authors:
            contrib = db.Contributor()
            contrib.person_id = author.person_id
            contrib.role_id = 1
            contrib.part_id = part.id
            session.add(contrib)

        people = session.query(db.ArticlePerson)\
            .filter_by(article_id=article.id).all()

        for person in people:
            contrib = db.Contributor()
            contrib.person_id = person.person_id
            contrib.role_id = 6
            contrib.part_id = part.id
            session.add(contrib)

        tags = session.query(db.ArticleTag)\
            .filter_by(article_id=article.id).all()

        for tag in tags:
            story_tag = db.StoryTag()
            story_tag.shortstory_id = story.id
            story_tag.tag_id = tag.tag_id
            session.add(story_tag)

        # Get issue
        ic = session.query(db.IssueContent)\
            .filter_by(article_id=article.id).first()

        if ic:
            ic.shortstory_id = story.id
            ic.article_id = None
            session.add(ic)

        # session.delete(article)
        print("Adding shortstory {} ({})", story.title, story.id)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        print(exp)
