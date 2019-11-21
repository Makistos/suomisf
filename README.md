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

## Examples on how to store books
The database has been designed in such a way it can store different kinds of
books but this might also make the structure less obvious. As the import data
includes Finnish books only (original and translations) I will use those as
examples on how to deal with some situations. This chapter talks mainly about
the trinity of Work, Edition and Part.

Work is the original work and does not really represent anything concrete.
It's the work done by one or several authors and covers every version printed.

Edition is a single edition of the book in one language. So for instance,
every edition in English has their own row in this table.

Part is whatever parts an edition and/or work contains. Short stories can be
listed as parts allowing collections where some edition is not based strictly
on some work but could be either a combination or just part of one. Sometimes
works are also split into several volumes and in some cases multiple works
are combined into one book. This table allows expressing these cases. Title is
always the name in the edition.

There must always be at least one row in each of these three tables for any
book.

1. The simple case: First edition of a book: There should be one row in each
   of Work, Edition and Part and nothing else.
2. Another edition of a book: There should be another row in Edition and Part
   but only the original row in Work.
3. A work split into multiple parts. For example Frank Herbert's Dune was
   split into three parts in Finland. This would be represented as one row in
   Work and three rows in Edition and Part.
4. Two works combined into one edition, e.g. a compendum of Shakespeare's
   plays. This should have one Work and Part row for each play and one row in
   Edition for the compendum.
5. A collection translated into another language. Edition and Work both have
   one row while every short story has a row in Part and also the ShortStory
   table. Title in the Part row has the translated name while Title in
   ShortStory holds the original name of the story. 

## To-Do
* Adding and modifying of data for all tables in the database.
* ~Separation of admin and regular user rights.~
* Making "important publisher series" specific to each user.
* Some Ajax-based stuff would be useful, e.g. when adding or modifying a book,
  ~~if publisher is changed list of publisher series to choose from should also
  update~~.
* Looks could be improved a lot. Especially long lists are not very readable
  at the moment.
* Authors, translators and editors only have a 1:m mapping to books at the
  moment. Meaning any collaborators are listed as a single author, translator or
  editor. This is because original data was too complex to handle properly.
* Some popups would be nice, e.g. for books.
* People do have dob, dod and birthplace but these are not used anywhere. Not
  sure if I want to either.
* Exporting and importing a collection.
* ~~Option to change password and a user page~~. Plus stuff related to this like
  a user list.
* Adding a new edition of an existing book.


## API Design

This is not implemented yet. Also very WIP anyways and lacks descriptions for
return values.

Strings used as search parameters are always used with ilike operator. So to
search using a part of a string, you can use the percentage sign, e.g. using
"Asimov%" as the person's full name will find all the names starting with
Asimov (case independent).

All replies are in JSON.

### Authentication

POST /api/1.0/auth

Parameters: 
* *username*
* *password*

### Getting list of works

GET /api/works

Parameters:
* workid
* title
* authorid
* language

Returns works that match the search criteria which can be any of the
parameters.

### Getting list of editions

GET /api/editions

Parameters_
* workid
* editionid
* title
* authorid
* language

### Getting info for a work

GET /api/work/{workid}

#### Getting info for an edition

GET /api/edition/{editionid}

### Getting a list of persons

GET /api/persons

Parameters:
* fullname
* last_name
* first_name
* dob
* dod
* birthplace
* type (A = author, T = translator, E = editor)

### Getting info on a person

GET /api/person/{personid}

### Getting your collection 

Requires authentication.

GET /api/collection
