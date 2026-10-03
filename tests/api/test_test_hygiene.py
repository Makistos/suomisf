"""
Checks on the test code itself.

A status assertion like `status_code in [200, 400, 500]` passes whether the
request worked, was refused or crashed the server, so it can't catch a
regression. Until 2026-10 the suite had 141 of them, and they hid a 500 on
every wishlist read and five endpoints anyone could write to.

Fails when a status-code list:
  - accepts a 5xx, or
  - accepts both a 2xx and a 4xx (success and failure both "pass").
Assert the one status the test should get instead.
"""
import glob
import os
import re

TESTS_DIR = os.path.dirname(os.path.dirname(__file__))
STATUS_LIST = re.compile(r'status_code\s+in\s+[\[(]([^\])]*)[\])]')


def test_status_assertions_are_specific():
    offenders = []
    for path in sorted(glob.glob(os.path.join(TESTS_DIR, '**', '*.py'), recursive=True)):
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue
        for lineno, line in enumerate(open(path, encoding='utf-8'), 1):
            for match in STATUS_LIST.finditer(line):
                codes = {c.strip() for c in match.group(1).split(',') if c.strip()}
                accepts_crash = any(c.startswith('5') for c in codes)
                accepts_both = (any(c.startswith('2') for c in codes)
                                and any(c.startswith('4') for c in codes))
                if accepts_crash or accepts_both:
                    offenders.append(
                        f'{os.path.relpath(path, TESTS_DIR)}:{lineno}: {line.strip()}')
    assert not offenders, 'non-specific status assertions:\n' + '\n'.join(offenders)
