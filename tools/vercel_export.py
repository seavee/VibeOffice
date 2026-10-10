#!/usr/bin/env python3
"""Copy public/ to dist/ and stamp the published version string.

VO.VERSION stays 'dev' in the repository. The copy Vercel serves uses
YYYY.MM.<6-char commit>, as described in docs/suite.md. Standard library only.
"""
import datetime
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'public'
DST = ROOT / 'dist'
STAMP = re.compile(r"VO\.VERSION = 'dev';")


def commit_sha():
    sha = os.environ.get('VERCEL_GIT_COMMIT_SHA', '').strip()
    if sha:
        return sha
    # CLI uploads have no clone. Git deployments set VERCEL_GIT_COMMIT_SHA;
    # a local run can still read HEAD.
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, OSError):
        return ''


def commit_when(sha):
    try:
        iso = subprocess.check_output(
            ['git', 'show', '-s', '--format=%cI', sha], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
        return datetime.datetime.fromisoformat(iso)
    except (subprocess.CalledProcessError, ValueError, OSError):
        return datetime.datetime.now(datetime.timezone.utc)


def main():
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)

    sha = commit_sha()
    if not sha:
        print(f'no commit id; left VO.VERSION as dev -> {DST}')
        return
    if not re.fullmatch(r'[0-9a-fA-F]{7,64}', sha):
        raise SystemExit('refusing to stamp from an unexpected commit id')
    when = commit_when(sha)
    version = f'{when.year}.{when.month:02d}.{sha[:6].lower()}'
    suite = DST / 'common' / 'suite.js'
    text = suite.read_text(encoding='utf-8')
    new, n = STAMP.subn(f"VO.VERSION = '{version}';", text, count=1)
    if n != 1:
        raise SystemExit('VO.VERSION stamp point not found in common/suite.js')
    suite.write_text(new, encoding='utf-8')
    print(f'stamped {version} -> {DST}')


if __name__ == '__main__':
    main()
