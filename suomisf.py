from app import app, db
from app.orm_decl import Work, Edition, Person, Author, Translator, Editor, Publisher, Pubseries, Bookseries
from typing import Dict, Any


@app.shell_context_processor
def make_shell_context() -> Dict[str, Any]:
    return {'db': db, 'Person': Person, 'Work': Work, 'Author': Author}
