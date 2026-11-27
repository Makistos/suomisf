# SuomiSF API Documentation

This document provides comprehensive documentation for the SuomiSF (Finnish Science Fiction Bibliography) API endpoints. The API follows RESTful conventions and returns JSON responses.

## Base URL
```
http://www.sf-bibliografia.fi/api
```

## Authentication

Most endpoints that modify data require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Response Format

All API responses follow this general structure:
```json
{
  "response": <data>,
  "status": <http_status_code>
}
```

## Endpoints

### Authentication

#### POST /api/login
Log in a user and receive JWT tokens.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": "string",
  "role": "string",
  "id": "number"
}
```

#### POST /api/register
Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "email": "string (optional)"
}
```

The password must be 8 to 128 characters (the same rule applies to
`POST /api/password/reset`). Errors: 400 with `{"msg": ...}` for a
password outside that range; 401 for missing credentials, an existing
username or an email already in use.

#### POST /api/refresh
Refresh an access token using a refresh token.

**Headers:** `Authorization: Bearer <refresh_token>`

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": "string",
  "role": "string",
  "id": "number"
}
```

### Front Page Data

#### GET /api/frontpagedata
Get statistics and data for the front page.

**Response:**
```json
{
  "works": "number",
  "editions": "number",
  "magazines": "number",
  "shorts": "number",
  "covers": "number",
  "latest": "array"
}
```

### Works

#### GET /api/works/{workid}
Get detailed information about a specific work.

**Parameters:**
- `workid` (string): The ID of the work

**Response:** Work object with details including title, authors, genres, editions, etc.

#### POST /api/works
Create a new work. Requires admin authentication.

**Request Body:** Work object with required fields

#### PUT /api/works
Update an existing work. Requires admin authentication.

**Request Body:** Work object with updated fields

#### DELETE /api/works/{workid}
Delete a work. Requires admin authentication.

#### GET /api/bookindex
One page of the book index: every work, filtered, sorted and paged on the server, with only what a list row shows. Public.
Used by the new book index page; `POST /api/searchworks` stays as it is for the current page and the book suggestions.

**Query parameters (all optional):**
- `author`, `title`, `orig_title`: from the start of the text (author: name or alternative name of a writer or the real person
  behind a pen name; titles: the start of any word too)
- `origyear_min`, `origyear_max`: the original's publication year
- `printyear_min`, `printyear_max`: any Finnish printing in the range
- `nationality`: a writer's country id
- `type`: comma-separated work type ids (any of them)
- `genre`: comma-separated genre abbreviations (any of them), e.g. `SF,F`
- `initial`: the first letter of the author string, e.g. `L` or `Ä`
- `sort`: `author` (default; author string, title), `title`, `year` (oldest first), `newest`; empty years last
- `page` (from 1, default 1), `rows` (50, 100 or 200; default 50)

**Response:** `{"total": int, "page": int, "rows": int, "works": [...]}`. Each work: `id`, `title`, `subtitle`, `orig_title`,
`pubyear`, `author_str`, `type`, `authors` (`id`, `name`, `alt_name`), `real_authors` (the real writers behind a pen name, same
fields), `translators` (of the first printing), `bookseries` (`id`, `name`, `partof` {`id`, `name`} or null; or null),
`bookseriesnum`, `genres` (`id`, `abbr`, `name`), `printings` (count), `first_edition` (`id`, `pubyear`, `publisher` and
`pubseries`, each {`id`, `name`} or null), `editions` (every printing, by laitos and then printing number: `id`, `title`, `pubyear`, `editionnum`, `version`,
`translators` (`id`, `name`, `alt_name`), `publisher` and `pubseries` (each {`id`, `name`} or null), `owned`, `wishlisted`). No covers: the list is text only. A page past the last is an empty list.

`owned` and `wishlisted` are the logged-in user's own marks (from their `userbook` rows); for a visitor, or a missing or
malformed token, they are false and the request still succeeds. An expired token gets 401 `Token has expired`, as on other
endpoints, so the frontend renews it and asks again (access tokens last a minute).
400 for a parameter that can't be used (rows other than 50/100/200, page below 1, unknown sort, non-numeric years or ids,
an initial longer than one letter).

#### PUT /api/works/{workid}/cover
Set which cover the work page shows. Requires admin authentication.

**Request Body:** `{"image_id": <id> | null}`: the id of an image of one of the
work's printings (`editions[].images[].id`), or `null` to let the page show
the first printing's cover.

**Response:** 200 on success, also when nothing changes; 400 for a bad work or
image id, or an image that isn't a cover of this work; 404 if the work
doesn't exist. A change is logged in the work's change history as the field
*Pääkuva* (old value: the previous cover's printing, or "oletus").

`GET /api/works/{workid}` returns the choice as `cover_image_id` (null = the
default). The column comes from migration 053; deleting the image clears it.

#### GET /api/works/{workid}/awards
Get awards associated with a work.

#### GET /api/works/shorts/{workid}
Get short stories in a work collection.

#### PUT /api/works/shorts
Update short stories in a work collection. Requires admin authentication.

#### POST /api/works/shorts
Add short stories to a work collection. Requires admin authentication.

#### GET /api/worktypes
Get available work types.

#### PUT /api/work/{workid}/tags/{tagid}
Add a tag to a work. Requires admin authentication.

#### DELETE /api/work/{workid}/tags/{tagid}
Remove a tag from a work. Requires admin authentication.

#### GET /api/worksbyinitial/{letter}
Get works by first letter of author name.

#### POST /api/searchworks
Search for works based on criteria.

#### GET /api/latest/works/{count}
Get the latest works added to the database.

### People

#### GET /api/people
Get a list of people with optional filtering.

#### POST /api/people
Create a new person. Requires admin authentication.

#### PUT /api/people
Update an existing person. Requires admin authentication.

#### GET /api/people/{person_id}
Get detailed information about a specific person.

#### DELETE /api/people/{person_id}
Delete a person. Requires admin authentication.

#### GET /api/people/{person_id}/articles
Get articles by a person.

#### GET /api/people/{person_id}/awarded
Get awards received by a person.

#### GET /api/people/{personid}/chiefeditor
Get issues where the person was chief editor.

#### GET /api/people/{personid}/shorts
Get short stories by a person.

#### PUT /api/person/{personid}/tags/{tagid}
Add a tag to a person. Requires admin authentication.

#### DELETE /api/person/{personid}/tags/{tagid}
Remove a tag from a person. Requires admin authentication.

#### GET /api/filter/people/{pattern}
Filter people by name pattern.

#### GET /api/latest/people/{count}
Get the latest people added to the database.

### Editions

#### GET /api/editions/{editionid}
Get detailed information about a specific edition.

#### POST /api/editions
Create a new edition. Requires admin authentication.

#### PUT /api/editions
Update an existing edition. Requires admin authentication.

#### DELETE /api/editions/{editionid}
Delete an edition. Requires admin authentication.

#### POST /api/editions/{editionid}/images
Upload images for an edition. Requires admin authentication.

#### DELETE /api/editions/{editionid}/images/{imageid}
Delete an image from an edition. Requires admin authentication.

#### GET /api/editions/{edition_id}/changes
Get change history for an edition.

#### GET /api/editions/{editionid}/owners
Get list of people who own this edition.

#### GET /api/editions/{editionid}/owner/{personid}
Check if a person owns this edition.

#### GET /api/editions/owned/{userid}
Get editions owned by a user.

#### DELETE /api/editions/{editionid}/owner/{personid}
Remove ownership of an edition. Requires admin authentication.

#### POST /api/editions/owner
Add edition ownership. Requires admin authentication.

#### PUT /api/editions/owner
Update edition ownership. Requires admin authentication.

#### GET /api/editions/{editionid}/shorts
Get short stories in an edition.

#### GET /api/latest/editions/{count}
Get the latest editions added to the database.

### Short Stories

#### POST /api/shorts
Create a new short story. Requires admin authentication.

#### PUT /api/shorts
Update an existing short story. Requires admin authentication.

#### GET /api/shorts/{shortid}
Get detailed information about a specific short story.

#### DELETE /api/shorts/{shortid}
Delete a short story. Requires admin authentication.

#### POST /api/searchshorts
Search for short stories based on criteria.

#### GET /api/shorttypes
Get available short story types.

#### PUT /api/story/{storyid}/tags/{tagid}
Add a tag to a short story. Requires admin authentication.

#### DELETE /api/story/{storyid}/tags/{tagid}
Remove a tag from a short story. Requires admin authentication.

#### GET /api/latest/shorts/{count}
Get the latest short stories added to the database.

### Articles

#### GET /api/articles/{articleid}
Get detailed information about a specific article.

#### GET /api/articles/{articleid}/tags
Get tags associated with an article.

#### PUT /api/articles/{articleid}/tags/{tagid}
Add a tag to an article. Requires admin authentication.

#### DELETE /api/articles/{articleid}/tags/{tagid}
Remove a tag from an article. Requires admin authentication.

### Magazines

#### POST /api/magazines
Create a new magazine. Requires admin authentication.

#### PUT /api/magazines
Update an existing magazine. Requires admin authentication.

#### DELETE /api/magazines/{magazineid}
Delete a magazine. Requires admin authentication.

#### GET /api/magazinetypes
Get available magazine types.

### Issues

#### GET /api/issues/{issueid}
Get detailed information about a specific issue.

#### POST /api/issues
Create a new issue. Requires admin authentication.

#### PUT /api/issues
Update an existing issue. Requires admin authentication.

#### DELETE /api/issues/{issueid}
Delete an issue. Requires admin authentication.

#### GET /api/issues/{issueid}/shorts
Get short stories in an issue.

#### PUT /api/issues/shorts
Update short stories in an issue. Requires admin authentication.

#### GET /api/issues/{issueid}/articles
Get articles in an issue.

#### PUT /api/issues/articles
Update articles in an issue. Requires admin authentication.

#### GET /api/issues/{issueid}/tags
Get tags associated with an issue.

#### PUT /api/issue/{issueid}/tags/{tagid}
Add a tag to an issue. Requires admin authentication.

#### DELETE /api/issue/{issueid}/tags/{tagid}
Remove a tag from an issue. Requires admin authentication.

#### GET /api/issues/sizes
Get available issue sizes.

#### POST /api/issues/{issueid}/covers
Upload covers for an issue. Requires admin authentication.

#### DELETE /api/issues/{issueid}/covers
Delete covers from an issue. Requires admin authentication.

### Awards

#### GET /api/awards
Get list of all awards.

#### GET /api/awards/{award_id}
Get detailed information about a specific award.

#### GET /api/works/{work_id}/awarded
Get awards for a specific work.

#### GET /api/people/{person_id}/awarded
Get awards for a specific person.

#### GET /api/shorts/{short_id}/awarded
Get awards for a specific short story.

#### PUT /api/awards/works/awards
Update work awards. Requires admin authentication.

#### PUT /api/awards/people/awards
Update person awards. Requires admin authentication.

#### GET /api/awards/type/{award_type}
Get awards by type.

#### GET /api/awards/categories/{award_type}
Get award categories by type.

#### GET /api/awards/categories/{award_id}
Get categories for a specific award.

#### GET /api/awards/filter/{filter}
Filter awards by criteria.

#### POST /api/awarded
Create award assignment. Requires admin authentication.

### Publishers

#### GET /api/publishers
Get list of publishers.

#### GET /api/publisherindex
The light publisher list for the new list page: every publisher, ordered by name, without its editions (GET /api/publishers
returns every edition of every publisher for the current page).

**Response:** `{"total": int, "publishers": [...]}`. Each publisher: `id`, `name`, `fullname`, `editions` (count), `first_year`
and `last_year` (null without editions), `magazines` (`id`, `name`, `issues`: the number of issues), ordered by name.

#### POST /api/publishers
Create a new publisher. Requires admin authentication.

#### PUT /api/publishers
Update an existing publisher. Requires admin authentication.

#### GET /api/publishers/{publisherid}/summary
The new publisher page's header and tables: `id`, `name`, `fullname`, `description`, `links` (`link`, `description`), `editions`
and `works` (counts), `first_year`, `last_year`, `series` (`id`, `name`, `editions`, `first_year`, `last_year`, by name) and
`magazines` (`id`, `name`, `type`, `issues`, `first_year`, `last_year`) and `genres` (`abbr`, `name`, `works`: distinct works the publisher
has published in the genre, most first). 400 for a non-numeric id, 404 for an unknown one.

#### GET /api/publishers/{publisherid}/editions
One page of the publisher's editions for the new publisher page (a publisher publishes editions, so the page lists them, not works).

**Query parameters** (all optional): `q` (from the start of a word of the author's name, the edition's or work's title or the original
title), `year_min`, `year_max` (the edition's year), `genre` (a genre's abbreviation: the editions of works in it), `first=1` (only first editions: laitos 1 or none, printing 1), `sort` (`oldest` default, `newest`, `title` (the title the row shows: the work's when the edition's is empty), `author`), `page` (from 1),
`rows` (50, 100 or 200; default 100).

**Response:** `{"total": int, "page": int, "rows": int, "editions": [...], "own": {"editions": int, "wishlisted": int} | null}`.
`own` counts the logged-in user's owned and wishlisted editions among all that the filters select (every page); null for a visitor.
Each edition: `id`, `title`, `subtitle`, `pubyear`,
`version`, `editionnum`, `pubseries` ({`id`, `name`} or null), `pubseriesnum`, `translators` (`id`, `name`, `alt_name`), `work`
(`id`, `title`, `orig_title`, `pubyear`, `author_str`, `type`, `authors`, `genres`, `bookseries` ({`id`, `name`, `partof`} or null),
`bookseriesnum`), `cover` (`image_src`, `thumb_src` or null),
`owned`, `wishlisted` (the logged-in user's own marks; an expired token gets 401 `Token has expired` so the frontend renews it).
400 for a parameter that can't be used, 404 for an unknown publisher.

#### GET /api/publishers/{publisherid}
Get detailed information about a specific publisher.

#### DELETE /api/publishers/{publisherid}
Delete a publisher. Requires admin authentication.

#### GET /api/filter/publishers/{pattern}
Filter publishers by name pattern.

### Book Series

#### GET /api/bookseries
Get list of book series.

#### POST /api/bookseries
Create a new book series. Requires admin authentication.

#### PUT /api/bookseries
Update an existing book series. Requires admin authentication.

#### GET /api/bookseries/{bookseriesid}
Get detailed information about a specific book series.

#### DELETE /api/bookseries/{bookseriesid}
Delete a book series. Requires admin authentication.

#### GET /api/filter/bookseries/{pattern}
Filter book series by name pattern.

### Publication Series

#### GET /api/pubseries
Get list of publication series.

#### POST /api/pubseries
Create a new publication series. Requires admin authentication.

#### PUT /api/pubseries
Update an existing publication series. Requires admin authentication.

#### DELETE /api/pubseries/{pubseriesid}
Delete a publication series. Requires admin authentication.

#### GET /api/filter/pubseries/{pattern}
Filter publication series by name pattern.

### Tags

#### GET /api/tags
Get list of all tags.

#### GET /api/tagsquick
Get a quick list of tags.

#### POST /api/tags
Create a new tag. Requires admin authentication.

#### GET /api/tags/{tag_id}
Get detailed information about a specific tag.

#### GET /api/tags/form/{tag_id}
Get tag form data.

#### PUT /api/tags
Update an existing tag. Requires admin authentication.

#### DELETE /api/tags/{tagid}
Delete a tag. Requires admin authentication.

#### GET /api/filter/tags/{pattern}
Filter tags by name pattern.

#### POST /api/tags/{source_id}/merge/{target_id}
Merge two tags. Requires admin authentication.

#### GET /api/tags/types
Get available tag types.

### Users

#### GET /api/users
Get list of users.

#### GET /api/users/{userid}
Get detailed information about a specific user.

#### GET /api/users/{userid}/stats/genres
Get genre statistics for a user.

### Countries

#### GET /api/countries
Get list of countries.

#### GET /api/filter/countries/{pattern}
Filter countries by name pattern.

### Roles

#### GET /api/roles
Get list of all roles.

#### GET /api/roles/{target}
Get roles for a specific target.

### Changes

#### GET /api/work/{workid}/changes
Get change history for a work.

#### GET /api/person/{personid}/changes
Get change history for a person.

#### GET /api/changes
Get list of all changes.

#### DELETE /api/changes/{changeid}
Delete a change record. Requires admin authentication.

### Wishlist

#### GET /api/editions/{editionid}/wishlist
Get wishlist status for an edition.

#### PUT /api/editions/{editionid}/wishlist/{userid}
Add edition to user's wishlist.

#### DELETE /api/editions/{editionid}/wishlist/{userid}
Remove edition from user's wishlist.

#### GET /api/editions/{editionid}/wishlist/{userid}
Check if edition is in user's wishlist.

#### GET /api/editions/wishlist/{userid}
Get user's complete wishlist.

### Utility Endpoints

#### GET /api/bindings
Get available binding types.

#### GET /api/genres
Get list of genres.

#### GET /api/filter/languages/{pattern}
Filter languages by pattern.

#### GET /api/filter/linknames/{pattern}
Filter link names by pattern.

#### GET /api/latest/covers/{count}
Get latest covers added to the database.

#### GET /api/firstlettervector/{target}
Get first letters for target type (works or stories).

## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

Error responses include a message describing the error:
```json
{
  "code": 400,
  "message": "Error description"
}
```

## Rate Limiting

No explicit rate limiting is currently implemented, but please be respectful with API usage.

## Data Formats

### Dates
All dates are in ISO 8601 format: `YYYY-MM-DD`

### IDs
All entity IDs are integers unless otherwise specified.

### Text
All text fields support UTF-8 encoding and may contain Finnish characters.
