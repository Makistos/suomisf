"""
Cover thumbnails.

Lists show covers 60-160 px tall, but the stored covers are ~500 px tall
(median 74 KB). Each book and magazine cover gets a 320 px tall WebP copy
(sharp at 2x for 160 px; ~15 KB) in a thumbs/ folder next to it:

    /static/images/books/Kirja_1p.jpg -> /static/images/books/thumbs/Kirja_1p.webp

Thumbnails are made when a cover is uploaded, and for existing covers by
scripts/make_thumbnails.py. The API's image schemas send `thumb_src`: the
thumbnail's URL when it exists, otherwise the cover's own URL, so lists
work before the backfill has run. Like the covers themselves, thumbnails
are left on disk when a cover is unlinked from an edition or issue.
"""
import os
from typing import List, Optional, Tuple

import cv2

from app import app

THUMB_HEIGHT = 320
THUMB_DIR = 'thumbs'
WEBP_QUALITY = 80

# (URL prefix setting, folder setting) for each kind of cover.
COVER_LOCATIONS = (('BOOKCOVER_DIR', 'BOOKCOVER_SAVELOC'),
                   ('MAGAZINECOVER_IMG', 'MAGAZINECOVER_SAVELOC'))


def _locate(image_src: Optional[str]) -> Optional[Tuple[str, str, str]]:
    """(url_prefix, folder, file name) of a stored cover, or None for
    anything else (e.g. an external URL)."""
    if not image_src:
        return None
    for url_key, folder_key in COVER_LOCATIONS:
        prefix, folder = app.config.get(url_key), app.config.get(folder_key)
        if prefix and folder and image_src.startswith(prefix):
            name = image_src[len(prefix):]
            if name and '/' not in name:
                return prefix, folder, name
    return None


def thumb_name(file_name: str) -> str:
    """Path of a cover's thumbnail relative to the cover's folder."""
    return f'{THUMB_DIR}/{os.path.splitext(file_name)[0]}.webp'


def thumb_src(image_src: Optional[str]) -> Optional[str]:
    """URL of the cover's thumbnail if it exists, else the cover's URL."""
    location = _locate(image_src)
    if location is None:
        return image_src
    prefix, folder, name = location
    if os.path.exists(os.path.join(folder, thumb_name(name))):
        return prefix + thumb_name(name)
    return image_src


def make_thumbnail(source: str, target: str, height: int = THUMB_HEIGHT) -> bool:
    """Write a WebP copy of `source` scaled to `height` (never enlarged)."""
    image = cv2.imread(source, cv2.IMREAD_COLOR)
    if image is None:
        return False
    original_height, original_width = image.shape[:2]
    if original_height > height:
        width = max(1, round(original_width * height / original_height))
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    return bool(cv2.imwrite(target, image, [cv2.IMWRITE_WEBP_QUALITY, WEBP_QUALITY]))


def make_thumbnail_for(image_src: str) -> bool:
    """Make the thumbnail for a stored cover given its URL. Failures are
    logged, not raised: a missing thumbnail only means lists fall back to
    the full cover."""
    location = _locate(image_src)
    if location is None:
        return False
    _, folder, name = location
    try:
        made = make_thumbnail(os.path.join(folder, name),
                              os.path.join(folder, thumb_name(name)))
    except (cv2.error, OSError) as exp:
        app.logger.warning(f'make_thumbnail_for({image_src}): {exp}')
        return False
    if not made:
        app.logger.warning(f'make_thumbnail_for({image_src}): not an image')
    return made


def make_missing_thumbnails(folder: str, force: bool = False) -> Tuple[int, int, List[str]]:
    """Make thumbnails for every cover in `folder` that lacks one (or all,
    with force). Returns (made, skipped, failed file names)."""
    made, skipped, failed = 0, 0, []
    for name in sorted(os.listdir(folder)):
        source = os.path.join(folder, name)
        if not os.path.isfile(source) or not name.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        target = os.path.join(folder, thumb_name(name))
        if not force and os.path.exists(target) \
                and os.path.getmtime(target) >= os.path.getmtime(source):
            skipped += 1
            continue
        try:
            ok = make_thumbnail(source, target)
        except (cv2.error, OSError):
            ok = False
        if ok:
            made += 1
        else:
            failed.append(name)
    return made, skipped, failed
