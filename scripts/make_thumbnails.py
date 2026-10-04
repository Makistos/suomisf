"""
Make the list thumbnails for existing book and magazine covers.

Run once after deploying the thumbnail feature, and again whenever covers
are added to the image folders by other means than an upload through the
site (uploads make their thumbnail themselves). Safe to re-run: covers whose
thumbnail is newer than the cover are skipped.

    PYTHONPATH=. pdm run python scripts/make_thumbnails.py            # missing only
    PYTHONPATH=. pdm run python scripts/make_thumbnails.py --force    # remake all

The folders come from the app config (BOOKCOVER_SAVELOC,
MAGAZINECOVER_SAVELOC) unless given with --folder. Thumbnails go to a
thumbs/ subfolder of each folder; see app/thumbnails.py.
"""
import argparse
import os
import sys
import time

from app import app
from app.thumbnails import COVER_LOCATIONS, make_missing_thumbnails


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--force', action='store_true',
                        help='remake thumbnails that already exist')
    parser.add_argument('--folder', action='append',
                        help='cover folder to process (repeatable); '
                             'default: the configured cover folders')
    args = parser.parse_args()

    folders = args.folder or [app.config[key] for _, key in COVER_LOCATIONS
                              if app.config.get(key)]
    failed_total = 0
    for folder in folders:
        if not os.path.isdir(folder):
            print(f'{folder}: not a folder, skipped')
            continue
        started = time.time()
        made, skipped, failed = make_missing_thumbnails(folder, force=args.force)
        failed_total += len(failed)
        print(f'{folder}: {made} made, {skipped} up to date, {len(failed)} failed '
              f'({time.time() - started:.0f} s)')
        for name in failed:
            print(f'  failed: {name}')
    return 1 if failed_total else 0


if __name__ == '__main__':
    sys.exit(main())
