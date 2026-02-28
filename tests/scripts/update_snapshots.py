#!/usr/bin/env python3
"""
SuomiSF API Snapshot Generator

Captures API responses from the golden database and stores them as snapshots
for comparison during test runs.

Usage:
    pdm run python tests/scripts/update_snapshots.py [--endpoints FILE]

This script should be run after updating the golden database to refresh
the expected test data.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Flask app
from app import app


SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures', 'snapshots')


# Define all endpoints to snapshot
# Format: (method, path, data, snapshot_name)
ENDPOINTS_TO_SNAPSHOT: List[tuple] = [
    # Miscellaneous
    ('GET', '/api/frontpagedata', None, 'frontpagedata'),
    ('GET', '/api/genres', None, 'genres'),
    ('GET', '/api/countries', None, 'countries'),
    ('GET', '/api/roles/', None, 'roles'),
    ('GET', '/api/bindings', None, 'bindings'),
    ('GET', '/api/worktypes', None, 'worktypes'),
    ('GET', '/api/shorttypes', None, 'shorttypes'),
    ('GET', '/api/magazinetypes', None, 'magazinetypes'),
    ('GET', '/api/latest/covers/5', None, 'latest_covers_5'),
    ('GET', '/api/latest/works/5', None, 'latest_works_5'),
    ('GET', '/api/latest/editions/5', None, 'latest_editions_5'),
    ('GET', '/api/latest/people/5', None, 'latest_people_5'),
    ('GET', '/api/latest/shorts/5', None, 'latest_shorts_5'),

    # Statistics
    ('GET', '/api/stats/genrecounts', None, 'stats_genrecounts'),
    ('GET', '/api/stats/personcounts', None, 'stats_personcounts'),
    ('GET', '/api/stats/storypersoncounts', None, 'stats_storypersoncounts'),
    ('GET', '/api/stats/publishercounts', None, 'stats_publishercounts'),
    ('GET', '/api/stats/worksbyyear', None, 'stats_worksbyyear'),
    ('GET', '/api/stats/origworksbyyear', None, 'stats_origworksbyyear'),
    ('GET', '/api/stats/storiesbyyear', None, 'stats_storiesbyyear'),
    ('GET', '/api/stats/issuesperyear', None, 'stats_issuesperyear'),
    ('GET', '/api/stats/nationalitycounts', None, 'stats_nationalitycounts'),
    ('GET', '/api/stats/storynationalitycounts', None, 'stats_storynationalitycounts'),
    ('GET', '/api/stats/misc', None, 'stats_misc'),

    # Lists
    ('GET', '/api/magazines', None, 'magazines'),
    ('GET', '/api/awards', None, 'awards'),
    ('GET', '/api/tags', None, 'tags'),
    ('GET', '/api/publishers', None, 'publishers'),
    ('GET', '/api/bookseries', None, 'bookseries'),
    ('GET', '/api/pubseries', None, 'pubseries'),

    # Sample entity lookups (use known IDs from golden DB)
    ('GET', '/api/works/1', None, 'work_1'),
    ('GET', '/api/editions/1', None, 'edition_1'),
    ('GET', '/api/people/1', None, 'person_1'),
    ('GET', '/api/shorts/1', None, 'short_1'),

    # Test-specific entity snapshots
    ('GET', '/api/shorts/406', None, 'short_406'),
    ('GET', '/api/works/shorts/171', None,
     'work_shorts_171'),
    ('GET', '/api/works/shorts/27', None,
     'work_shorts_27'),
    ('GET', '/api/works/shorts/1378', None,
     'work_shorts_1378'),
    ('GET', '/api/works/27', None, 'work_27'),
    ('GET', '/api/editions/242/shorts', None,
     'edition_shorts_242'),
    ('GET', '/api/editions/28/shorts', None,
     'edition_shorts_28'),
    ('GET', '/api/editions/1585/shorts', None,
     'edition_shorts_1585'),
    ('GET', '/api/issues/92', None, 'issue_92'),
    ('GET', '/api/people/3238/shorts', None,
     'person_shorts_3238'),

    # Filters (patterns must be at least 2 chars)
    ('GET', '/api/filter/people/Asi', None,
     'filter_people_Asi'),
    ('GET', '/api/filter/tags/sci', None,
     'filter_tags_sci'),
    ('GET', '/api/filter/publishers/Tam', None,
     'filter_publishers_Tam'),
]


def make_request(client, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a request and return the response data."""
    if method.upper() == 'GET':
        response = client.get(path)
    elif method.upper() == 'POST':
        response = client.post(path, json=data, content_type='application/json')
    else:
        raise ValueError(f"Unsupported method: {method}")

    result = {
        'status_code': response.status_code,
        'data': None,
        'error': None
    }

    try:
        result['data'] = response.get_json()
    except Exception as e:
        result['error'] = str(e)

    return result


def save_snapshot(name: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """Save a snapshot to file."""
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    snapshot = {
        'metadata': metadata,
        'response': data
    }

    filepath = os.path.join(SNAPSHOTS_DIR, f'{name}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

    return filepath


def generate_snapshots(endpoints: Optional[List[tuple]] = None) -> Dict[str, Any]:
    """Generate snapshots for all endpoints."""
    endpoints = endpoints or ENDPOINTS_TO_SNAPSHOT

    app.config['TESTING'] = True

    # app/__init__.py calls load_dotenv('.env', override=True),
    # which overwrites DATABASE_URL to the production DB.
    # Mirror the conftest.py override: replace the DB name in
    # the prod URL to get the test DB URL, then reconfigure all
    # connection objects so requests hit suomisf_test (which has
    # the migration applied) rather than the production DB.
    import sqlalchemy as sa
    import app.route_helpers as route_helpers_module
    import app.orm_decl as orm_decl_module
    from app import db as flask_db

    _main_db = 'suomisf'
    _test_db = 'suomisf_test'
    prod_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if f'/{_main_db}' in prod_url:
        test_url = prod_url.replace(
            f'/{_main_db}', f'/{_test_db}', 1
        )
    else:
        # Already pointing at test DB or unknown URL
        test_url = prod_url

    app.config['SQLALCHEMY_DATABASE_URI'] = test_url
    route_helpers_module.db_url = test_url
    orm_decl_module.db_url = test_url

    engines = flask_db._app_engines.setdefault(app, {})
    for engine in engines.values():
        engine.dispose()
    engines.clear()
    engines[None] = sa.create_engine(test_url)

    client = app.test_client()

    metadata = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generator': 'update_snapshots.py',
        'total_endpoints': len(endpoints)
    }

    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    print("=" * 60)
    print("SuomiSF API Snapshot Generator")
    print("=" * 60)
    print(f"Snapshots directory: {SNAPSHOTS_DIR}")
    print(f"Endpoints to snapshot: {len(endpoints)}")
    print("=" * 60)
    print()

    for method, path, data, name in endpoints:
        print(f"  {method} {path}...", end=" ", flush=True)

        try:
            response = make_request(client, method, path, data)

            if response['status_code'] == 200:
                endpoint_metadata = {
                    **metadata,
                    'endpoint': path,
                    'method': method,
                    'status_code': response['status_code']
                }

                filepath = save_snapshot(name, response, endpoint_metadata)
                print(f"OK -> {os.path.basename(filepath)}")
                results['success'].append(name)
            else:
                print(f"SKIP (status {response['status_code']})")
                results['skipped'].append((name, response['status_code']))

        except Exception as e:
            print(f"FAIL ({e})")
            results['failed'].append((name, str(e)))

    print()
    print("=" * 60)
    print(f"Success: {len(results['success'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Failed:  {len(results['failed'])}")
    print("=" * 60)

    # Save summary
    summary_path = os.path.join(SNAPSHOTS_DIR, '_snapshot_summary.json')
    with open(summary_path, 'w') as f:
        json.dump({
            'metadata': metadata,
            'results': {
                'success': results['success'],
                'skipped': [(n, s) for n, s in results['skipped']],
                'failed': [(n, e) for n, e in results['failed']]
            }
        }, f, indent=2)

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate API response snapshots')
    parser.add_argument('--endpoints', '-e', help='JSON file with custom endpoints')
    parser.add_argument('--list', '-l', action='store_true', help='List endpoints to snapshot')

    args = parser.parse_args()

    if args.list:
        print("Endpoints to snapshot:")
        for method, path, data, name in ENDPOINTS_TO_SNAPSHOT:
            print(f"  {method:6} {path:40} -> {name}.json")
        return

    endpoints = None
    if args.endpoints:
        with open(args.endpoints, 'r') as f:
            endpoints = json.load(f)

    results = generate_snapshots(endpoints)

    # Exit with error if any failed
    if results['failed']:
        sys.exit(1)


if __name__ == '__main__':
    main()
