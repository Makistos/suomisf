from app import app, db
from app.orm_decl import Work, Edition, Person, Author, Translator, Editor, Publisher, Pubseries, Bookseries

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Person': Person, 'Work': Work, 'Author': Author}
