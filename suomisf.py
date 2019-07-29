from app import app, db
from app.orm_decl import Book, Person, BookPerson, Publisher, Pubseries, Bookseries

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Person': Person, 'Book': Book, 'BookPerson': BookPerson}
