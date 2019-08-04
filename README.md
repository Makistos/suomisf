# SuomiSF

This is Flask-based collection manager for Finnish Science Fiction, Fantasy and Horror books.
Contents and database schema is based on "The Bibliography of of Finnish Sf-, Fantasy- and Horror Literature". 
This is why interface is also only in Finnish. There are errors in the data as
it was impossible to import everything correctly.

There is an importer (bib_import.py) which can fill the database with the data
from the bibliography. Because it will be possible to add and edit everything
in the database it could also be possible to add books by hand in the future.

Application uses Flask framework and SQLAlchemy ORM. Bootstrap css files are
missing from this package at the moment.

## To-Do
* Adding and modifying of data for all tables in the database.
* Separation of admin and regular user rights.
* Making "important publisher series" specific to each user.
* Some Ajax-based stuff would be useful, e.g. when adding or modifying a book,
  if publisher is changed list of publisher series to choose from should also
  update.
* Looks could be improved a lot. Especially long lists are not very readable
  at the moment.
* Authors, translators and editors only have a 1:m mapping to books at the
  moment. Meaning any collaborators are listed as a single author, translator or
  editor. This is because original data was too complex to handle properly.
* Some popups would be nice, e.g. for books.
* People do have dob, dod and birthplace but these are not used anywhere. Not
  sure if I want to either.
* Exporting and importing a collection.
* Option to change password and a user page. Plus stuff related to this like
  a user list.
