"""
Cover thumbnails (app/thumbnails.py, API plan Phase 5).

conftest points the cover folders at a temporary directory, so these tests
create and read files there, never in app/static/images.
"""
import io
import os

import cv2
import numpy as np
import pytest

from app import app as flask_app
from app.thumbnails import (THUMB_HEIGHT, make_missing_thumbnails,
                            make_thumbnail, thumb_name, thumb_src)

from .test_admin_roundtrips import JPEG, _login

EDITION_ID = 86


@pytest.fixture
def covers(app):
    """The (temporary) book cover folder and its URL prefix."""
    return flask_app.config['BOOKCOVER_SAVELOC'], flask_app.config['BOOKCOVER_DIR']


def _write_cover(folder, name, height=600, width=400):
    image = np.full((height, width, 3), (40, 120, 200), dtype=np.uint8)
    path = os.path.join(folder, name)
    cv2.imwrite(path, image)
    return path


def test_thumbnail_is_scaled_to_height(covers, tmp_path):
    folder, _ = covers
    source = _write_cover(folder, 'b5-scale.jpg', height=600, width=400)
    target = str(tmp_path / 'out.webp')
    assert make_thumbnail(source, target)
    height, width = cv2.imread(target).shape[:2]
    assert (height, width) == (THUMB_HEIGHT, round(400 * THUMB_HEIGHT / 600))


def test_small_cover_is_not_enlarged(covers, tmp_path):
    folder, _ = covers
    source = _write_cover(folder, 'b5-small.jpg', height=100, width=70)
    target = str(tmp_path / 'small.webp')
    assert make_thumbnail(source, target)
    assert cv2.imread(target).shape[:2] == (100, 70)


def test_thumb_src_falls_back_until_the_thumbnail_exists(covers):
    folder, prefix = covers
    _write_cover(folder, 'b5-fallback.jpg')
    src = prefix + 'b5-fallback.jpg'
    assert thumb_src(src) == src
    make_missing_thumbnails(folder)
    assert thumb_src(src) == prefix + 'thumbs/b5-fallback.webp'


@pytest.mark.parametrize('src', [None, '', 'https://example.invalid/kansi.jpg',
                                 '/static/images/elsewhere/kansi.jpg'])
def test_thumb_src_leaves_other_urls_alone(covers, src):
    assert thumb_src(src) == src


def test_make_missing_thumbnails_skips_done_and_reports_broken(covers):
    folder, _ = covers
    _write_cover(folder, 'b5-batch.jpg')
    with open(os.path.join(folder, 'b5-broken.jpg'), 'wb') as fh:
        fh.write(b'not an image')
    made, _, failed = make_missing_thumbnails(folder)
    assert made >= 1 and 'b5-broken.jpg' in failed
    assert os.path.exists(os.path.join(folder, thumb_name('b5-batch.jpg')))

    made_again, skipped, _ = make_missing_thumbnails(folder)
    assert made_again == 0 and skipped >= 1
    remade, _, _ = make_missing_thumbnails(folder, force=True)
    assert remade >= 1


def test_upload_makes_thumbnail_and_api_points_to_it(client, covers):
    """An uploaded cover gets its thumbnail at once, and the edition's
    images carry its URL as thumb_src."""
    folder, prefix = covers
    admin = _login(client)
    before = {i['id'] for i in client.get(f'/api/editions/{EDITION_ID}').get_json()['images']}
    resp = client.post(f'/api/editions/{EDITION_ID}/images', headers=admin,
                       data={'file': (io.BytesIO(JPEG), 'b5-upload.jpg')},
                       content_type='multipart/form-data')
    try:
        assert resp.status_code in (200, 201), resp.get_json()
        assert os.path.exists(os.path.join(folder, 'thumbs', 'b5-upload.webp'))
        images = client.get(f'/api/editions/{EDITION_ID}').get_json()['images']
        new = [i for i in images if i['id'] not in before]
        assert new and new[0]['thumb_src'] == prefix + 'thumbs/b5-upload.webp'
    finally:
        for image in client.get(f'/api/editions/{EDITION_ID}').get_json()['images']:
            if image['id'] not in before:
                client.delete(f"/api/editions/{EDITION_ID}/images/{image['id']}",
                              headers=admin)
