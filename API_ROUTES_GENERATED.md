# SuomiSF API Routes Documentation

Auto-generated documentation from API routes.

## Table of Contents

- [Articles](#articles)
- [Awarded](#awarded)
- [Awards](#awards)
- [Bindings](#bindings)
- [Bookseries](#bookseries)
- [Changes](#changes)
- [Countries](#countries)
- [Editions](#editions)
- [Filter](#filter)
- [Firstlettervector](#firstlettervector)
- [Frontpagedata](#frontpagedata)
- [Genres](#genres)
- [Issue](#issue)
- [Issues](#issues)
- [Latest](#latest)
- [Login](#login)
- [Magazines](#magazines)
- [Magazinetypes](#magazinetypes)
- [People](#people)
- [Person](#person)
- [Publishers](#publishers)
- [Pubseries](#pubseries)
- [Refresh](#refresh)
- [Register](#register)
- [Roles](#roles)
- [Search](#search)
- [Searchshorts](#searchshorts)
- [Searchworks](#searchworks)
- [Shorts](#shorts)
- [Shorttypes](#shorttypes)
- [Story](#story)
- [Tags](#tags)
- [Tagsquick](#tagsquick)
- [Users](#users)
- [Work](#work)
- [Works](#works)
- [Worksbyinitial](#worksbyinitial)
- [Worktypes](#worktypes)

## Articles

### GET /api/articles/<articleid>

**Function:** `api_getarticle`

**File:** `api_articles.py`

**Description:**
```
Retrieves an article from the API based on the provided article ID.

    Parameters:
        articleId (str): The ID of the article to retrieve.

    Returns:
        Response: The response object containing the article data.

    Raises:
        ValueError: If the provided article ID is invalid.

    Example:
        api_getarticle('123')
```

---

### GET /api/articles/<articleid>/tags

**Function:** `api_getarticletags`

**File:** `api_articles.py`

**Description:**
```
Get the tags associated with a specific article.

    Parameters:
        articleId (int): The ID of the article.

    Returns:
        Response: The response object containing the tags associated with the
                  article.
```

---

### PUT DELETE /api/articles/<articleid>/tags/<tagid>

**Function:** `api_tagtoarticle`

**File:** `api_articles.py`

**Description:**
```
API endpoint for adding or removing a tag from an article.

    Args:
        id (int): The ID of the article.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response containing the result of the operation.
```

---

## Awarded

### POST /api/awarded

**Function:** `api_awarded`

**File:** `api_awards.py`

**Description:**
```
Get all awards that match a given filter.

    Args:
        filter (str): The filter to apply to the awards.

    Returns:
        Response: The response object containing the awards that match the
        given filter.
```

---

## Awards

### GET /api/awards

**Function:** `api_listawards`

**File:** `api_awards.py`

**Description:**
```
This function is a route handler for the '/api/awards' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the list of awards.
```

---

### GET /api/awards/<award_id>

**Function:** `api_getaward`

**File:** `api_awards.py`

**Description:**
```
This function is a route handler for the '/api/awards/<award_id>' endpoint.
    It accepts GET requests and returns a Response object.

    Parameters:
        award_id (int): The ID of the award to retrieve.

    Returns:
        Response: The response object containing the award data.
```

---

### GET /api/awards/categories/<award_id>

**Function:** `api_get_award_categories`

**File:** `api_awards.py`

**Description:**
```
Get all categories for a given award.

    Args:
        award_id (int): The ID of the award to get the categories for.

    Returns:
        Response: The response object containing the categories for the given
        award.
```

---

### GET /api/awards/categories/<string:award_type>

**Function:** `api_get_all_award_categories`

**File:** `api_awards.py`

**Description:**
```
Get all award categories.

    Returns:
        Response: The response object containing all award categories.
```

---

### GET /api/awards/filter/<string:filter>

**Function:** `api_get_awards_by_filter`

**File:** `api_awards.py`

**Description:**
```
Get all awards that match a given filter.

    Args:
        filter (str): The filter to apply to the awards.

    Returns:
        Response: The response object containing the awards that match the
        given filter.
```

---

### PUT /api/awards/people/awards

**Function:** `api_add_awards_to_person`

**File:** `api_awards.py`

**Description:**
```
Add awards to a person.

    Args:
        person_id (int): The ID of the person to add the awards to.

    Returns:
        Response: The response object containing the status of the request.
```

---

### GET /api/awards/type/<string:award_type>

**Function:** `api_get_awards_by_type`

**File:** `api_awards.py`

**Description:**
```
Get all awards of a given type.

    Args:
        award_type (str): The type of award to get.

    Returns:
        Response: The response object containing the awards of the given type.
```

---

### PUT /api/awards/works/awards

**Function:** `api_add_awards_to_work`

**File:** `api_awards.py`

**Description:**
```
Add awards to a work.

    Args:
        work_id (int): The ID of the work to add the awards to.

    Returns:
        Response: The response object containing the status of the request.
```

---

## Bindings

### GET /api/bindings

**Function:** `api_bindings`

**File:** `api.py`

**Description:**
```
This function is a route handler for the '/api/bindings' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.
```

---

## Bookseries

### GET /api/bookseries

**Function:** `api_listbookseries`

**File:** `api_bookseries.py`

**Description:**
```
This function is a route handler for the '/api/bookseries' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the list of book series.
```

---

### POST PUT /api/bookseries

**Function:** `api_bookseriescreateupdate`

**File:** `api_bookseries.py`

**Description:**
```
Create or update a book series.

    This function is responsible for handling the '/api/bookseries' endpoint
    with both 'POST' and 'PUT' methods. It expects a JSON payload containing
    the book series data.

    Parameters:
        None

    Returns:
        Response: The API response containing the result of the operation.

    Raises:
        None
```

---

### DELETE /api/bookseries/<bookseriesid>

**Function:** `api_bookseriesdelete`

**File:** `api_bookseries.py`

**Description:**
```
Delete a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series to be deleted.

    Returns:
        Response: The API response indicating the success or failure of the
                  deletion.
```

---

### GET /api/bookseries/<bookseriesid>

**Function:** `api_getbookseries`

**File:** `api_bookseries.py`

**Description:**
```
Get a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series.

    Returns:
        Response: The response object containing the book series data.

    Raises:
        TypeError: If the book series ID is not a valid integer.
        ValueError: If the book series ID is not a valid integer.

    Example:
        >>> api_GetBookseries('123')
        <Response [200]>
```

---

## Changes

### GET /api/changes

**Function:** `api_changes`

**File:** `api_changes.py`

**Description:**
```
Get changes done to the data from the Log table.

    Parameters:
        None

    Returns:
        A tuple containing the response string and the HTTP status code.
```

---

### DELETE /api/changes/<changeid>

**Function:** `api_change_delete`

**File:** `api_changes.py`

**Description:**
```
Delete a change.

    Args:
        changeid (int): The ID of the change to be deleted.

    Returns:
        Response: The API response containing the result of the deletion.
```

---

## Countries

### GET /api/countries

**Function:** `countries`

**File:** `api_countries.py`

**Description:**
```
Returns a list of all of the countries in the system ordered by name.
```

---

## Editions

### POST PUT /api/editions

**Function:** `api_editioncreateupdate`

**File:** `api_editions.py`

**Description:**
```
Create or update an edition using the provided API endpoint.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API request.
```

---

### GET /api/editions/<edition_id>/changes

**Function:** `api_editionchanges`

**File:** `api_editions.py`

**Description:**
```
Get changes for an edition.

    Args:
        edition_id (int): The ID of the edition.

    Returns:
        Response: The API response containing the changes.
```

---

### GET /api/editions/<editionid>

**Function:** `api_getedition`

**File:** `api_editions.py`

**Description:**
```
Get an edition by its ID.

    Args:
        editionId (str): The ID of the edition.

    Returns:
        Response: The response object containing the edition data.

    Raises:
        TypeError: If the edition ID is not a valid integer.
        ValueError: If the edition ID is not a valid integer.

    Example:
        >>> api_GetEdition('123')
        <Response [200]>
```

---

### DELETE /api/editions/<editionid>

**Function:** `api_editiondelete`

**File:** `api_editions.py`

**Description:**
```
Delete an edition.

    Parameters:
        editionId (str): The ID of the edition to be deleted.

    Returns:
        Response: The API response.
```

---

### POST /api/editions/<editionid>/images

**Function:** `api_uploadeditionimage`

**File:** `api_editions.py`

**Description:**
```
Uploads an image for a specific edition.

    Args:
        id (str): The ID of the edition.

    Returns:
        Response: The response object containing the result of the image
                  upload.
```

---

### DELETE /api/editions/<editionid>/images/<imageid>

**Function:** `api_deleteeditionimage`

**File:** `api_editions.py`

**Description:**
```
Delete an edition image.

    Args:
        id (str): The ID of the edition.
        imageid (str): The ID of the image.

    Returns:
        Response: The response object containing the result of the deletion.
```

---

### GET /api/editions/<editionid>/owner/<personid>

**Function:** `api_editionownerperson`

**File:** `api_editions.py`

**Description:**
```
Get the owner info of an edition.

    Args:
        editionid (str): The ID of the edition.
        personid (str): The ID of the person.

    Returns:
        Response: The API response containing the owner information.
```

---

### DELETE /api/editions/<editionid>/owner/<personid>

**Function:** `api_deleteowner`

**File:** `api_editions.py`

**Description:**
```
Delete the owner of an edition.

    Parameters:
        editionid (str): The ID of the edition.
        personid (str): The ID of the person.

    Returns:
        Response: The response object containing the result of the operation.
```

---

### GET /api/editions/<editionid>/owners

**Function:** `api_editionowners`

**File:** `api_editions.py`

**Description:**
```
Get the owners of an edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the owners of the edition.
```

---

### GET /api/editions/<editionid>/shorts

**Function:** `api_editionshorts`

**File:** `api_editions.py`

**Description:**
```
Get the shorts for a specific edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the shorts for the edition.
```

---

### GET /api/editions/<editionid>/wishlist

**Function:** `api_editionwishlist`

**File:** `api_wishlist.py`

**Description:**
```
Get the wishlist for a specific edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the wishlist for the edition.
```

---

### PUT /api/editions/<editionid>/wishlist/<userid>

**Function:** `api_editionwishlist_add`

**File:** `api_wishlist.py`

**Description:**
```
Add an edition to a user's wishlist.

    Args:
        editionid (str): The ID of the edition.
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the result of the operation.
```

---

### DELETE /api/editions/<editionid>/wishlist/<userid>

**Function:** `api_editionwishlist_remove`

**File:** `api_wishlist.py`

**Description:**
```
Remove an edition from a user's wishlist.

    Args:
        editionid (str): The ID of the edition.
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the result of the operation.
```

---

### GET /api/editions/<editionid>/wishlist/<userid>

**Function:** `api_editionwishlist_user_status`

**File:** `api_wishlist.py`

**Description:**
```
Checks if given user (userid) has given edition (editionid) in their
    wishlist.

    Args:
    editionid (str): The id of the edition.
    userid (str): The id of the user.

    Returns:
    Response: A JSON response containing a boolean value indicating if the
    edition is in the users wishlist.
```

---

### GET /api/editions/owned/<userid>

**Function:** `api_editionsowned`

**File:** `api_editions.py`

**Description:**
```
Get the owner info of an edition.

    Args:
        userid (str): The ID of the person.

    Returns:
        Response: The API response containing the owner information.
```

---

### POST PUT /api/editions/owner

**Function:** `api_addeditionowner`

**File:** `api_editions.py`

**Description:**
```
Add or update the owner of an edition.

    Parameters:
        editionid (str): The ID of the edition.
        params (dict): A dictionary containing the owner information.

    Returns:
        Response: The response object containing the result of the operation.
```

---

### GET /api/editions/wishlist/<userid>

**Function:** `api_editionwishlist_user_list`

**File:** `api_wishlist.py`

**Description:**
```
Gets the wishlist for a specific user.

    Args:
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the wishlist for the user.
```

---

## Filter

### GET /api/filter/alias/<id>

**Function:** `api_filteralias`

**File:** `api.py`

**Description:**
```
This function is a Flask route that handles GET requests to the
    '/api/filter/alias/<id>' endpoint. It takes a string parameter 'personid'
    which represents the id of the person. The function tries to convert the
    'personid' to an integer. If the conversion fails, it logs an error message
    and returns a Response object with a 400 status code and an error message.
    If the conversion is successful, the function calls the 'filter_aliases'
    function with the converted 'personid' and returns the result as a Response
    object. The function returns the Response object.
```

---

### GET /api/filter/bookseries/<pattern>

**Function:** `api_filterbookseries`

**File:** `api_bookseries.py`

**Description:**
```
Filters book series based on a given pattern.

    Args:
        pattern (str): The pattern to filter the book series.

    Returns:
        Response: The response object containing the filtered book series.

    Raises:
        None
```

---

### GET /api/filter/countries/<pattern>

**Function:** `api_filtercountries`

**File:** `api_countries.py`

**Description:**
```
Filter countries based on a given pattern.

    Args:
        pattern (str): The pattern to filter the countries.

    Returns:
        Response: The response object containing the filtered countries.

    Raises:
        None
```

---

### GET /api/filter/languages/<pattern>

**Function:** `api_filterlanguages`

**File:** `api.py`

**Description:**
```
Filter languages based on a given pattern.

    Args:
        pattern (str): The pattern to filter languages.

    Returns:
        Response: The response object containing the filtered languages.

    Raises:
        None
```

---

### GET /api/filter/linknames/<pattern>

**Function:** `api_filterlinknames`

**File:** `api.py`

**Description:**
```
This function is a Flask route that handles GET requests to the
    '/api/filter/linknames/<pattern>' endpoint. It takes a single parameter
    'pattern' of type string. The function cleans the 'pattern' using the
    'bleach' library and then calls the 'filter_link_names' function
    with the cleaned 'pattern' as an argument. The return type of this function
    is 'Response'.
```

---

### GET /api/filter/people/<pattern>

**Function:** `api_filterpeople`

**File:** `api_people.py`

**Description:**
```
Filter people list.

    Pattern has to be at least three characters long. Matching is done
    from start of the name field.

    Parameters
    ----------
    pattern: str
        Pattern to search for.

    Returns
    -------
```

---

### GET /api/filter/publishers/<pattern>

**Function:** `api_filterpublishers`

**File:** `api_publishers.py`

**Description:**
```
Filter publishers based on a given pattern.

    Args:
        pattern (str): The pattern to filter publishers.

    Returns:
        Response: The response containing the filtered publishers.

    Raises:
        None
```

---

### GET /api/filter/pubseries/<pattern>

**Function:** `api_filterpubseries`

**File:** `api_pubseries.py`

**Description:**
```
This function is a Flask route that filters publications based on a given
    pattern. It takes a string parameter `pattern` which is used to filter the
    publications. The function returns a Flask Response object.
```

---

### GET /api/filter/tags/<pattern>

**Function:** `api_filtertags`

**File:** `api_tags.py`

**Description:**
```
Filter tags based on a given pattern.

    Args:
        pattern (str): The pattern to filter the tags.

    Returns:
        Response: The response object containing the filtered tags.

    Raises:
        None
```

---

## Firstlettervector

### GET /api/firstlettervector/<target>

**Function:** `firstlettervector`

**File:** `api.py`

**Description:**
```
Get first letters for for target type.

    This function is used internally by the UI to create
    links to various pages, e.g. a list for choosing books
    based on the first letter of the author.

    Parameters
    ----------
    target: str
        Either "works" or "stories".

    Returns
    -------
    List[str, int]
        str is the return value in JSON. int is http return code.
        Str contains a dictionary where each item's key is a letter and
        value is the count of items (e.g. works).
```

---

## Frontpagedata

### GET /api/frontpagedata

**Function:** `frontpagestats`

**File:** `api.py`

**Description:**
```
@api {get} /api/frontpagedata Front page data
    @apiName Front page data
    @apiGroup Front page
    @apiPermission none
    @apiDescription Get data for the front page. This includes various
    statistics and the latest additions to the database.
    @apiSuccess {Number} works Number of works in the database
    @apiSuccess {Number} editions Number of editions in the database
    @apiSuccess {Number} magazines Number of magazines in the database
    @apiSuccess {Number} shorts Number of short stories in the database
    @apiSuccess {Number} covers Number of covers in the database
    @apiSuccess {Edition[]} latest Latest additions to the database (4)
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "response": [
            {
            "works": 1000,
            "editions": 2000,
            "magazines": 3000,
            "shorts": 4000,
            "magazines": 50,
            "covers": 1500,
            "latest": [
                {
                    }
                ]
            }
        ]
        }
    @apiError (Error 400) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad request
        {
        "code": 400,
        "message": "GetFrontpageData: Tietokantavirhe."
        }
```

---

## Genres

### GET /api/genres

**Function:** `genres`

**File:** `api.py`

**Description:**
```
Returns a list of all of the genres in the system in the order
    they are in the database (i.e. by id).
```

---

## Issue

### PUT DELETE /api/issue/<issueid>/tags/<tagid>

**Function:** `api_tagtoissue`

**File:** `api_issues.py`

**Description:**
```
API endpoint for adding or removing a tag from an issue.

    Args:
        id (int): The ID of the issue.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        None
```

---

## Issues

### POST PUT /api/issues

**Function:** `api_createupdateissue`

**File:** `api_issues.py`

**Description:**
```
Create or update an issue in the API.

    This function is responsible for handling the '/api/issues' endpoint with
    both 'POST' and 'PUT' methods. It expects a JSON payload containing the
    issue data.

    Parameters:
        None

    Returns:
        Response: The API response containing the result of the operation.

    Raises:
        None
```

---

### GET /api/issues/<issueid>

**Function:** `api_getissueformagazine`

**File:** `api_issues.py`

**Description:**
```
Get the issue for a magazine.

    Args:
        issueId (str): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
```

---

### DELETE /api/issues/<issueid>

**Function:** `api_deleteissue`

**File:** `api_issues.py`

**Description:**
```
API endpoint for deleting an issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The API response.

    Raises:
        None
```

---

### GET /api/issues/<issueid>/articles

**Function:** `api_getissuearticles`

**File:** `api_issues.py`

**Description:**
```
Get the issue for an article.

    Args:
        issueId (int): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
```

---

### POST /api/issues/<issueid>/covers

**Function:** `api_uploadissueimage`

**File:** `api_issues.py`

**Description:**
```
Uploads an image for a specific issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The response object containing the result of the image
                  upload.
```

---

### DELETE /api/issues/<issueid>/covers

**Function:** `api_deleteissueimage`

**File:** `api_issues.py`

**Description:**
```
API endpoint for deleting an issue image.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The API response.

    Raises:
        None
```

---

### GET /api/issues/<issueid>/shorts

**Function:** `api_getissueshorts`

**File:** `api_issues.py`

**Description:**
```
Get the issue for a short story.

    Args:
        issueId (int): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
```

---

### GET /api/issues/<issueid>/tags

**Function:** `api_getissuetags`

**File:** `api_issues.py`

**Description:**
```
Get the tags associated with a specific issue.

    Parameters:
        issueId (str): The ID of the issue.

    Returns:
        Response: The response containing the tags associated with the issue.
```

---

### PUT /api/issues/articles

**Function:** `api_addissuearticles`

**File:** `api_issues.py`

**Description:**
```
Add issues to an article.

    This function is an API endpoint that handles 'PUT' requests to
    '/api/issues/articles'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
```

---

### PUT /api/issues/shorts

**Function:** `api_addissueshorts`

**File:** `api_issues.py`

**Description:**
```
Add issues to a short story.

    This function is an API endpoint that handles 'PUT' requests to
    '/api/issues/shorts'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
```

---

### GET /api/issues/sizes

**Function:** `api_getissuesizes`

**File:** `api_issues.py`

**Description:**
```
Get the issue sizes.
```

---

## Latest

### GET /api/latest/covers/<count>

**Function:** `api_latestcovers`

**File:** `api.py`

**Description:**
```
Get the latest covers.

    Args:
        count (int): The number of covers to return.

    Returns:
        Response: The response object containing the list of latest covers.

    Raises:
        ValueError: If the count is not an integer.
```

---

### GET /api/latest/editions/<count>

**Function:** `api_latesteditions`

**File:** `api_editions.py`

**Description:**
```
Get the latest editions.

    Args:
        count (int): The number of editions to return.

    Returns:
        Response: The response object containing the list of latest editions.

    Raises:
        ValueError: If the count is not an integer.
```

---

### GET /api/latest/people/<count>

**Function:** `api_latestpeople`

**File:** `api_people.py`

**Description:**
```
Get the latest people.

    Args:
        count (int): The number of people to return.

    Returns:
        Response: The response object containing the list of latest people.

    Raises:
        ValueError: If the count is not an integer.
```

---

### GET /api/latest/shorts/<count>

**Function:** `api_latestshorts`

**File:** `api_shorts.py`

**Description:**
```
Get the latest shorts.

    Args:
        count (int): The number of shorts to return.

    Returns:
        Response: The response object containing the list of latest shorts.

    Raises:
        None
```

---

### GET /api/latest/works/<count>

**Function:** `api_latestworks`

**File:** `api_works.py`

**Description:**
```
Get the latest works.

    Args:
        count (int): The number of works to return.

    Returns:
        Response: The response object containing the list of latest works.

    Raises:
        ValueError: If the count is not an integer.
```

---

## Login

### POST /api/login

**Function:** `api_login`

**File:** `api.py`

**Description:**
```
@api {post} /api/login Login
    @apiName Login
    @apiGroup User
    @apiPermission none
    @apiDescription Log in the user. The user must be registered in the system.
    @apiBody {String} username Username
    @apiBody {String} password Password
    @apiSuccess {String} access_token Access token
    @apiSuccess {String} refresh_token Refresh token
    @apiSuccess {String} user Username
    @apiSuccess {String} role User role
    @apiSuccess {String} id User id
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "access_token": <access_token>,
        "refresh_token": <refresh_token>,
        "user": "exampleuser",
        "role": "user",
        "id": 1
        }
    @apiError (Error 401) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 401 Unauthorized
        {
        "code": 401,
        "message": "Kirjautuminen ei onnistunut"
        }
```

---

## Magazines

### POST PUT /api/magazines

**Function:** `api_magazinecreateupdate`

**File:** `api_magazines.py`

**Description:**
```
Create or update a magazine.

    This function is responsible for handling the '/api/magazines' endpoint
    requests with both 'POST' and 'PUT' methods. It expects the request data
    to be in JSON format and performs input validation using the `bleach`
    library.

    Parameters:
    - None

    Returns:
    - A `Response` object representing the API response.

    Raises:
    - None

    Tests:
    - create_magazine: Create new magazine
    - update_magazine: Update existing magazine
    - update_magazine_invalid_type: Type is not 0 or 1
    - update_magazine_type_not_number: Type is not a number
```

---

### DELETE /api/magazines/<magazineid>

**Function:** `api_deletemagazine`

**File:** `api_magazines.py`

**Description:**
```
Delete a magazine.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        value.

    Raises:
        ValueError: If the magazine ID is invalid.

    Tests:
        delete_magazine: Delete existing magazine
        delete_magazine_unknown_id: Try id not existing in db
        delete_magazine_invalid_id: Try id which is not a number
```

---

## Magazinetypes

### GET /api/magazinetypes

**Function:** `api_getmagazinetypes`

**File:** `api_magazines.py`

**Description:**
```
Get the magazine types.

    Returns:
        Response: The response object containing the magazine types.

    Tests:
        get_magazine_types: Get magazine types
```

---

## People

### GET /api/people/

**Function:** `api_getpeople`

**File:** `api_people.py`

**Description:**
```
This function receives parameters in the form of
    first=50&...filters_name_operator=1&filters_name_constraints_value=null..
    I.e. the original dictionary has been translated into variables. The
    Javascript dictionary looks like this:
    {
        first: 0,
        rows: 50,
        page: 0,
        sortField: "name",
        sortOrder: 1,
        multiSortMeta: null,
        filters: {
            global: { value: null, matchMode: FilterMatchMode.CONTAINS },
            name: { operator: FilterOperator.AND,
                    constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.STARTS_WITH
                      }
                    ]
                  },
            dob: { operator: FilterOperator.AND,
                   constraints: [
                     { value: null,
                       matchMode: FilterMatchMode.EQUALS
                     }
                   ]
                  },
            dod: { operator: FilterOperator.AND,
                   constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.EQUALS
                      }
                   ]
                 },
            nationality: { value: null, matchMode: FilterMatchMode.EQUALS },
            work_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            story_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            roles: { value: null, matchMode: FilterMatchMode.EQUALS }
        }
    }
    This function will translate the parameter list back to a similar Python
    dict.
    Those constants in the list are explained in the implementation function,
    but they are simple self-explaining strings.
```

---

### GET /api/people/<int:person_id>/awarded

**Function:** `api_get_awards_for_person`

**File:** `api_awards.py`

**Description:**
```
Get all awards for a given person.

    Args:
        person_id (int): The ID of the person to get the awards for.

    Returns:
        Response: The response object containing the awards for the given
        person.
```

---

### DELETE /api/people/<person_id>

**Function:** `api_deleteperson`

**File:** `api_people.py`

**Description:**
```
Delete a person from the API.

    Args:
        person_id (str): The ID of the person to be deleted.

    Returns:
        Response: The response object containing the result of the deletion.

    Tests:
        delete_author: Delete an existing person
        delete_editor: Delete an existing person
        delete_translator: Delete an existing person
        delete_person_bad_id: Try id which is not a number
        delete_person_unknown_id: Try id not existing in db
        delete_person_not_authorized: Try to delete without authorization
```

---

### GET /api/people/<person_id>/articles

**Function:** `api_personarticles`

**File:** `api_people.py`

**Description:**
```
Retrieves a list of articles for a specific person.

    Args:
        person_id (str): The ID of the person.

    Returns:
        Response: The response object containing the list of articles.
```

---

### GET /api/people/<person_id>/awarded

**Function:** `api_personawards`

**File:** `api_people.py`

**Description:**
```
Retrieves a list of awards for a specific person.

    Args:
        person_id (str): The ID of the person.

    Returns:
        Response: The response object containing the list of awards.
```

---

### GET /api/people/<personid>/chiefeditor

**Function:** `api_chiefeditor`

**File:** `api_people.py`

**Description:**
```
Retrieves issues person is editor in chief.

    Args:
        id (int): The ID of the person.

    Returns:
        Response: The response object containing the issues.
```

---

### GET /api/people/<personid>/shorts

**Function:** `api_listshorts`

**File:** `api_people.py`

**Description:**
```
Retrieves a list of shorts for a specific person.

    Args:
        id (int): The ID of the person.

    Returns:
        Response: The response object containing the list of shorts.
```

---

## Person

### GET /api/person/<personid>/changes

**Function:** `api_personchanges`

**File:** `api_changes.py`

**Description:**
```
Get changes for a person.

    Args:
        personid (int): The ID of the person.

    Returns:
        Response: The API response containing the changes.
```

---

### PUT DELETE /api/person/<personid>/tags/<tagid>

**Function:** `api_tagtoperson`

**File:** `api_people.py`

**Description:**
```
Handles the API endpoint for adding or removing a tag from a person.

    Args:
        id (int): The ID of the person.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        None
```

---

## Publishers

### POST PUT /api/publishers

**Function:** `api_publishercreateupdate`

**File:** `api_publishers.py`

**Description:**
```
Create or update a publisher.

    This function is responsible for handling the '/api/publishers/' endpoint
    requests with both 'POST' and 'PUT' methods. It expects the request data to
    be in JSON format and performs input validation using the `bleach` library.

    Parameters:
    - None

    Returns:
    - A `Response` object representing the API response.

    Raises:
    - None

    Tests:
        publisher_create: Create a new publisher
        publisher_similar_name: Create a new publisher with same name as
                                an existing publisher
        publisher_similar_fullname: Create a new publisher with same fullname
                                    as an existing publisher
        publisher_missing_name: Create a new publisher with missing name
        publisher_update: Update an existing publisher
        publisher_update_missing_id: Update a publisher with missing ID
```

---

### GET /api/publishers

**Function:** `api_listpublishers`

**File:** `api_publishers.py`

**Description:**
```
This function is a route handler for the '/api/publishers' endpoint. It
    accepts GET requests and returns a tuple containing the response data and
    the HTTP status code.

    Parameters:
        None

    Returns:
        A tuple containing the response data and the HTTP status code.

    Tests:
        publisher_list_all: Get all publishers
```

---

### DELETE /api/publishers/<publisherid>

**Function:** `api_deletepublisher`

**File:** `api_publishers.py`

**Description:**
```
Delete a publisher.

    Parameters:
        publisherId (str): The ID of the publisher to be deleted.

    Returns:
        Response: The API response.

    Tests:
        publisher_delete: Delete an existing publisher
        publisher_invalid_id: Try to delete a publisher with invalid id
```

---

### GET /api/publishers/<publisherid>

**Function:** `api_getpublisher`

**File:** `api_publishers.py`

**Description:**
```
Retrieves a publisher from the API based on the provided publisher ID.

    Parameters:
        publisherid (str): The ID of the publisher to retrieve.

    Returns:
        ResponseType: The response object containing the publisher data or an
        error message.

    Tests:
        publisher_get: Get an existing publisher
        publisher_invalid_id: Try to get a publisher with invalid id
```

---

## Pubseries

### GET /api/pubseries

**Function:** `api_listpubseries`

**File:** `api_pubseries.py`

**Description:**
```
This function is a route handler for the '/api/pubseries' endpoint. It
    accepts GET requests and returns a tuple containing a string and an
    integer. The string is the response body, and the integer is the HTTP
    status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and an integer.
```

---

### PUT POST /api/pubseries

**Function:** `api_createupdatepubseries`

**File:** `api_pubseries.py`

**Description:**
```
This function is a route handler for the '/api/pubseries' endpoint. It
    accepts PUT and POST requests and returns a tuple containing a string and
    an integer. The string is the response body, and the integer is the HTTP
    status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and a Http response code.
```

---

### DELETE /api/pubseries/<pubseriesid>

**Function:** `api_deletepubseries`

**File:** `api_pubseries.py`

**Description:**
```
This function is a route handler for the '/api/pubseries/<pubseriesid>'
    endpoint. It accepts DELETE requests and returns a tuple containing a
    string and an integer. The string is the response body, and the integer is
    the HTTP status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and an integer.
```

---

## Refresh

### POST /api/refresh

**Function:** `api_refresh`

**File:** `api.py`

**Description:**
```
@api {post} /api/refresh Refresh token
    @apiName Refresh Token
    @apiGroup User
    @apiPermission user
    @apiDescription Refresh the access token.
    @apiHeader {String} Authorization Bearer token
    @apiSuccess {String} access_token Access token
    @apiSuccess {String} refresh_token Refresh token
    @apiSuccess {String} user Username
    @apiSuccess {String} role User role
    @apiSuccess {String} id User id
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "access_token": <access_token>,
        "refresh_token": <refresh_token>,
        "user": "exampleuser",
        "role": "user",
        "id": 1
        }
    @apiError (Error 401) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 401 Unauthorized
        {
        "code": 401,
        "message": "Kirjautuminen ei onnistunut"
        }
```

---

## Register

### POST /api/register

**Function:** `api_register`

**File:** `api.py`

**Description:**
```
@api {post} /api/refresh Refresh token
    @apiName Refresh Token
    @apiGroup User
    @apiPermission user
    @apiDescription Refresh the access token.
    @apiHeader {String} Authorization Bearer token
    @apiSuccess {String} access_token Access token
    @apiSuccess {String} refresh_token Refresh token
    @apiSuccess {String} user Username
    @apiSuccess {String} role User role
    @apiSuccess {String} id User id
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "access_token": <access_token>,
        "refresh_token": <refresh_token>,
        "user": "exampleuser",
        "role": "user",
        "id": 1
        }
    @apiError (Error 401) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 401 Unauthorized
        {
        "code": 401,
        "message": "Kirjautuminen ei onnistunut"
        }
```

---

## Roles

### GET /api/roles/

**Function:** `api_roles`

**File:** `api_roles.py`

**Description:**
```
Returns a list of contributor roles in the system in the order they are
    in the database (i.e. by id).
```

---

### GET /api/roles/<target>

**Function:** `api_role`

**File:** `api_roles.py`

**Description:**
```
Return a list of roles for a given target.

    Parameters:
        target (str): Target to request roles for, either 'work', 'short'
                      or 'edition'.

    Returns:
        Response: Requested roles.
```

---

## Search

### GET POST /api/search/<pattern>

**Function:** `api_search`

**File:** `api.py`

**Description:**
```
Searches for a pattern in the API and returns the results.

    Args:
        pattern (str): The pattern to search for.

    Returns:
        Tuple[str, int]: A tuple containing the search results as a JSON string
                         and the HTTP status code.
```

---

## Searchshorts

### POST /api/searchshorts

**Function:** `api_searchshorts`

**File:** `api_shorts.py`

**Description:**
```
A function that handles the '/api/searchshorts' endpoint for the API.

    This function is triggered when a POST request is made to the
    '/api/searchshorts' endpoint. It expects a JSON payload in the request body
    containing search parameters.

    Parameters:
        None

    Returns:
        Response: The response object containing the search results.

    Raises:
        None
```

---

## Searchworks

### POST /api/searchworks

**Function:** `api_searchworks`

**File:** `api_works.py`

**Description:**
```
A function that handles the '/api/searchworks' endpoint.

    Parameters:
    - None

    Returns:
    - Response: The API response containing the search results.

    Description:
    - This function is responsible for handling the '/api/searchworks'
      endpoint, which is used to search for works.
    - It expects a POST request with JSON data containing the search
      parameters.
    - The function retrieves the search parameters from the request data and
      passes them to the 'search_books' function.
    - The 'search_books' function performs the actual search and returns the
      search results.
    - Finally, the function creates an API response using the
      'make_api_response' function and returns it.

    Note:
    - This function assumes that the 'search_books' and 'make_api_response'
      functions are defined elsewhere in the codebase.
```

---

## Shorts

### POST PUT /api/shorts

**Function:** `api_shortcreateupdate`

**File:** `api_shorts.py`

**Description:**
```
Create or update a short story.

    This function is an API endpoint that handles both POST and PUT requests to
    '/api/shorts'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
```

---

### GET /api/shorts/<int:short_id>/awarded

**Function:** `api_get_awards_for_short`

**File:** `api_awards.py`

**Description:**
```
Get all awards for a given short.

    Args:
        short_id (int): The ID of the short to get the awards for.

    Returns:
        Response: The response object containing the awards for the given
        short.
```

---

### DELETE /api/shorts/<shortid>

**Function:** `api_shortdelete`

**File:** `api_shorts.py`

**Description:**
```
Delete a short by its ID.

    Parameters:
        id (int): The ID of the short to be deleted.

    Returns:
        Response: The response object containing the result of the deletion.
```

---

### GET /api/shorts/<shortid>

**Function:** `api_getshort`

**File:** `api_shorts.py`

**Description:**
```
Retrieves a short by its ID.

    Args:
        shortid (str): The ID of the short.

    Returns:
        Response: The response object containing the short.
```

---

## Shorttypes

### GET /api/shorttypes

**Function:** `api_shorttypes`

**File:** `api_shorts.py`

**Description:**
```
Retrieves the short types from the API.

    Returns:
        Response: The API response containing the short types.
```

---

## Story

### PUT DELETE /api/story/<storyid>/tags/<tagid>

**Function:** `api_tagtostory`

**File:** `api_shorts.py`

**Description:**
```
API endpoint for adding or removing a tag from a story.

    Args:
        id (int): The ID of the story.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        TypeError: If the ID or tag ID is not an integer.
        ValueError: If the ID or tag ID is not a valid integer.
```

---

## Tags

### GET /api/tags

**Function:** `api_tags`

**File:** `api_tags.py`

**Description:**
```
Handles the GET request to '/api/tags' endpoint.

    Returns:
        Response: The response object containing the tags.
```

---

### POST /api/tags

**Function:** `api_tagcreate`

**File:** `api_tags.py`

**Description:**
```
Create a new tag.
```

---

### PUT /api/tags

**Function:** `api_tagupdate`

**File:** `api_tags.py`

**Description:**
```
Rename given tag. Cannot be named to an existing tag. tagMerge is used
    for combining tags.

    Parameters
    ----------
    id : int
        Id of tag to rename.
    name: str
        New name for tag.

    Returns
    -------
    200 - Request succeeded.
    400 - Bad Request. Either a tag by that name already exists of not tag
          with given id found or parameters are faulty.
```

---

### POST /api/tags/<source_id>/merge/<target_id>

**Function:** `api_tagmerge`

**File:** `api_tags.py`

**Description:**
```
Merge items of two tags into one and delete the obsolete tag.

    Parameters
    ----------
    id: int
        Id of tag to merge into.
    id2: int
        Id of tag to merge from.

    Returns
    -------
    200 - Request succeeded
    400 - Request failed because one of the ids was invalid.
```

---

### GET /api/tags/<tag_id>

**Function:** `api_tag`

**File:** `api_tags.py`

**Description:**
```
Retrieves information about a tag with the specified ID.

    Parameters:
        tag_id (str): The ID of the tag to retrieve information for.

    Returns:
        Response: The API response containing the tag information.
```

---

### DELETE /api/tags/<tagid>

**Function:** `api_tagdelete`

**File:** `api_tags.py`

**Description:**
```
Delete selected tag. Tag is only deleted if it isn't used anywhere.

    Parameters
    ----------
    id : int
        Id of tag to delete.

    Returns
    -------
    200 - Request succeeded
    400 - Request failed. Either id was not a number or tag with given id was
          not found.
```

---

### GET /api/tags/form/<tag_id>

**Function:** `api_tagform`

**File:** `api_tags.py`

**Description:**
```
Retrieves the form for a tag with the specified ID.

    Parameters:
        tag_id (str): The ID of the tag to retrieve the form for.

    Returns:
        Response: The API response containing the tag form.
```

---

### GET /api/tags/types

**Function:** `api_tagtypes`

**File:** `api_tags.py`

**Description:**
```
Get all tag types.

    Parameters
    ----------
    None

    Returns
    -------
    200 - Request succeeded
    400 - Request failed
```

---

## Tagsquick

### GET /api/tagsquick

**Function:** `api_tagsquick`

**File:** `api_tags.py`

**Description:**
```
Get tags for quick search.

    Returns:
        Response: The response object containing the tags.
```

---

## Users

### GET /api/users

**Function:** `api_listusers`

**File:** `api_users.py`

**Description:**
```
This function is an API endpoint that returns a list of users. It is
    decorated with the `@app.route` decorator, which maps the URL `/api/users`
    to this function. The function accepts GET requests and returns a tuple
    containing a string and an integer. The string represents the response
    body, and the integer represents the HTTP status code. The function calls
    the `make_api_response` function, passing the result of the `list_users`
    function as an argument.
```

---

### GET /api/users/<userid>

**Function:** `api_getuser`

**File:** `api_users.py`

**Description:**
```
Get a user by their ID.

    Args:
        userId (str): The ID of the user.

    Returns:
        Response: The response object containing the user information.
```

---

### GET /api/users/<userid>/stats/genres

**Function:** `api_userstatsgenres`

**File:** `api_users.py`

**Description:**
```
Retrieves the genre counts associated with the specified user.

    Parameters:
        userid (str): The ID of the user whose genres to retrieve.

    Returns:
        Response: The response object containing the list of genres if
                  successful, or an error message and status code if an
                  error occurs.
```

---

## Work

### GET /api/work/<workid>/changes

**Function:** `api_workchanges`

**File:** `api_changes.py`

**Description:**
```
Get changes for a work.

    Args:
        workid (int): The ID of the work.

    Returns:
        Response: The API response containing the changes.
```

---

### PUT DELETE /api/work/<workid>/tags/<tagid>

**Function:** `api_tagtowork`

**File:** `api_works.py`

**Description:**
```
Endpoint for adding or removing a tag from a work item.

    Args:
        id (int): The ID of the work item.
        tagid (int): The ID of the tag to be added or removed.

    Returns:
        Response: The API response containing the result of the operation.
```

---

## Works

### POST PUT /api/works

**Function:** `api_workcreateupdate`

**File:** `api_works.py`

**Description:**
```
Create or update a work in the API.

    This function handles the '/api/works' endpoint and supports both POST and
    PUT methods. The function expects a JSON payload in the request data.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
```

---

### GET /api/works/<int:work_id>/awarded

**Function:** `api_get_work_awards`

**File:** `api_awards.py`

**Description:**
```
Get all awards for a given work.

    Args:
        work_id (int): The ID of the work to get the awards for.

    Returns:
        Response: The response object containing the awards for the given work.
```

---

### GET /api/works/<workid>

**Function:** `api_getwork`

**File:** `api_works.py`

**Description:**
```
@api {get} /api/works/:id Get work
    @apiName Get Work
    @apiGroup Work
    @apiDescription Get work by id.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} work Work object.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response":
                {
                "misc": "",
                "work_type": {
                    "id": 1,
                    "name": "Romaani"
                },
                "title": "Kivineitsyt",
                "id": 1,
                "bookseriesorder": 0,
                "links": [],
                "bookseries": null,
                "tags": [],
                "genres": [
                    {
                    "abbr": "F",
                    "id": 1,
                    "name": "Fantasia"
                    }
                ],
                "contributions": [
                    {
                    "real_person": null,
                    "description": null,
                    "role": {
                        "id": 1,
                        "name": "Kirjoittaja"
                    },
                    "person": {
                        "id": 1,
                        "alt_name": "Barry Unsworth",
                        "name": "Unsworth, Barry"
                    }
                    }
                ],
                "language_name": null,
                "bookseriesnum": "",
                "awards": [],
                "subtitle": "",
                "descr_attr": null,
                "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin, 1985).
                                    Suom Aira Buffa. WSOY 1986. [F].",
                "author_str": "Unsworth, Barry",
                "pubyear": 1985,
                "orig_title": "Stone Virgin",
                "editions": [
                    {
                    "size": null,
                    "misc": "",
                    "title": "Kivineitsyt",
                    "id": 1,
                    "dustcover": 1,
                    "format": {
                        "id": 1,
                        "name": "Paperi"
                    },
                    "version": null,
                    "images": [],
                    "coverimage": 1,
                    "isbn": "",
                    "contributions": [
                        {
                        "real_person": null,
                        "description": null,
                        "role": {
                            "id": 2,
                            "name": "Kääntäjä"
                        },
                        "person": {
                            "id": 2,
                            "alt_name": "Aira Buffa",
                            "name": "Buffa, Aira"
                        }
                        }
                    ],
                    "pages": null,
                    "subtitle": "",
                    "binding": {
                        "id": 1,
                        "name": "Ei tietoa/muu"
                    },
                    "pubseries": null,
                    "publisher": {
                        "image_attr": null,
                        "name": "WSOY",
                        "id": 387,
                        "fullname": "Werner Söderström Oy",
                        "image_src": null
                    },
                    "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin,
                                        1985). Suom Aira Buffa. WSOY 1986.
                                        [F].",
                    "editionnum": 1,
                    "printedin": null,
                    "pubyear": 1986,
                    "pubseriesnum": null
                    }
                ],
                "description": null,
                "stories": []
                },
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "GetWork: Tietokantavirhe",
            "status": 400
        }
```

---

### DELETE /api/works/<workid>

**Function:** `api_workdelete`

**File:** `api_works.py`

**Description:**
```
@api {delete} /api/works/:id Delete work
    @apiName Delete Work
    @apiGroup Work
    @apiDescription Delete work by id.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} work Work object.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response": "WorkDelete: Teos poistettu",
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "WorkDelete: Tietokantavirhe",
            "status": 400
        }
```

---

### GET /api/works/<workid>/awards

**Function:** `api_workawards`

**File:** `api_works.py`

**Description:**
```
@api {get} /api/works/awards/:id Get work awards
    @apiName Get Work Awards
    @apiGroup Work
    @apiDescription Get awards for a work.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} awards Array of awards.
    @apiSuccessExample {json} Success-Response:
```

---

### PUT POST /api/works/shorts

**Function:** `api_workshorts_save`

**File:** `api_works.py`

**Description:**
```
Save shorts in a collection. 
    params = request.data.decode('utf-8')
    params = json.loads(params)
    return make_api_response(save_work_shorts(params))


@app.route('/api/worktypes', methods=['get'])
def api_worktypes() -> Response:
```

---

### GET /api/works/shorts/<workid>

**Function:** `api_workshorts`

**File:** `api_works.py`

**Description:**
```
Get shorts in a collection. 
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_WorkShorts: Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_work_shorts(int_id))


@app.route('/api/works/shorts', methods=['put', 'post'])
def api_workshorts_save() -> Response:
     Save shorts in a collection.
```

---

## Worksbyinitial

### GET /api/worksbyinitial/<letter>

**Function:** `api_searchworksbyinitial`

**File:** `api_works.py`

**Description:**
```
Searches for works by author initial.

    Args:
        letter (str): The author initial to search for.

    Returns:
        Response: The API response containing the search results.
```

---

## Worktypes

### GET /api/worktypes

**Function:** `api_worktypes`

**File:** `api_works.py`

**Description:**
```
@api {get} /api/worktypes Get all work types
    @apiName Get WorkTypes
    @apiGroup Work
    @apiDescription Get all work types in the system.
    @apiSuccess {ResponseType} worktypes List of work types.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response": [
                {
                    "id": 1,
                    "name": "Romaani"
                },
                {
                    "id": 2,
                    "name": "Kokoelma"
                },
                ...
            ],
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "WorkTypeGetAll: Tietokantavirhe",
            "status": 400
        }
```

---
