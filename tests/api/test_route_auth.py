"""
Static checks on how API routes are protected.

Reads app/api*.py with `ast` (no server needed) and fails when:

  - a decorator sits above @app.route. Flask registers the function at
    @app.route, so anything above it never runs; this silently disabled
    the auth on five endpoints until 2026-10.
  - a write route (POST/PUT/DELETE/PATCH) has no jwt decorator and isn't
    listed in PUBLIC_WRITE_ROUTES. A new write endpoint must either be
    protected or be added to that list on purpose.
"""
import ast
import glob
import os

APP_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app')

# Write routes that are public on purpose (function names).
PUBLIC_WRITE_ROUTES = {
    'api_register',
    'api_password_forgot',
    'api_password_reset',
    'api_search',                  # search term in the body
    'api_searchshorts',            # search term in the body
    'api_searchworks',             # search filters in the body
    'api_random_incomplete_work',  # read-only, filters in the body
    'api_pageview',                # anonymous page-view beacon
    'api_editionshorts',           # GET public; PUT checks admin inline
}

WRITE_METHODS = ("'put'", "'post'", "'delete'", "'patch'")


def _routes():
    for path in sorted(glob.glob(os.path.join(APP_DIR, 'api*.py'))):
        tree = ast.parse(open(path, encoding='utf-8').read())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            decorators = [ast.unparse(d) for d in node.decorator_list]
            route_positions = [i for i, d in enumerate(decorators) if '.route(' in d]
            if route_positions:
                yield os.path.basename(path), node, decorators, route_positions


def test_no_decorator_above_route():
    misplaced = [
        f'{name}:{node.lineno} {node.name}: {decorators[:route_positions[0]]}'
        for name, node, decorators, route_positions in _routes()
        if route_positions[0] != 0
    ]
    assert not misplaced, 'decorators above @app.route never run:\n' + '\n'.join(misplaced)


def test_write_routes_are_protected():
    unprotected = []
    for name, node, decorators, route_positions in _routes():
        route = ' '.join(decorators[i] for i in route_positions).lower()
        if not any(method in route for method in WRITE_METHODS):
            continue
        if any('jwt' in d for d in decorators):
            continue
        if node.name not in PUBLIC_WRITE_ROUTES:
            unprotected.append(f'{name}:{node.lineno} {node.name}')
    assert not unprotected, (
        'write routes with no auth decorator (protect them, or add to '
        'PUBLIC_WRITE_ROUTES if public on purpose):\n' + '\n'.join(unprotected))


def test_public_list_has_no_stale_entries():
    names = {node.name for _, node, _, _ in _routes()}
    assert PUBLIC_WRITE_ROUTES <= names, PUBLIC_WRITE_ROUTES - names
