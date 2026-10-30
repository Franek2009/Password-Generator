"""Safely consolidate v1.0.2 source assets; default is a read-only preview."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import tarfile

from source_archive import create_archive, sha256, verify_archive, restore_manifest_names

REPO = 'Franek2009/Password-Generator'
TAG = 'v1.0.2'
ARCHIVE = 'PasswordGenerator-third-party-sources.tar.gz'
BINARIES = {'PasswordGenerator-linux-x86_64.tar.gz', 'PasswordGenerator-windows-x86_64.zip'}


def gh(*args: str) -> str:
    return subprocess.check_output(['gh', *args], text=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Upload, verify, then replace source assets')
    args = parser.parse_args()
    release = json.loads(gh('release', 'view', TAG, '--repo', REPO, '--json', 'assets,body'))
    names = {a['name'] for a in release['assets']}
    sources = names - BINARIES - {ARCHIVE}
    if not BINARIES <= names:
        raise ValueError('Expected desktop binaries are missing')
    if sources == set() and ARCHIVE in names:
        print('Release already consolidated.')
        return
    if ARCHIVE not in names and (len(sources) != 54 or 'SOURCE_ASSETS_MANIFEST.txt' not in sources):
        raise ValueError('Expected exactly 53 original sources and their manifest; inspect release manually')
    print('Keep:', ', '.join(sorted(BINARIES)), flush=True)
    print(f'Replace {len(sources)} source assets with {ARCHIVE}')
    if not args.apply:
        print('Preview only. Use --apply to download, verify and consolidate.')
        return
    with tempfile.TemporaryDirectory(prefix='password-release-') as temporary:
        root = Path(temporary)
        source_dir = root / 'sources'
        source_dir.mkdir()
        if ARCHIVE in names:
            gh('release', 'download', TAG, '--repo', REPO, '--pattern', ARCHIVE, '--dir', str(root))
            with tarfile.open(root / ARCHIVE) as stream:
                for member in stream.getmembers():
                    if not member.isfile() or Path(member.name).name != member.name:
                        raise ValueError('Unexpected path in existing source archive')
                    content = stream.extractfile(member)
                    if content is None:
                        raise ValueError('Missing archived source')
                    (source_dir / member.name).write_bytes(content.read())
            verify_archive(root / ARCHIVE, source_dir)
            if len(list(source_dir.iterdir())) != 54:
                raise ValueError('Expected 53 sources and their original manifest')
        archived_hashes = {sha256(p) for p in source_dir.iterdir()} if ARCHIVE in names else set()
        for name in sorted(sources):
            # On resume, compare remaining assets with the already published archive.
            destination = root / 'remaining' if ARCHIVE in names else source_dir
            destination.mkdir(exist_ok=True)
            gh('release', 'download', TAG, '--repo', REPO, '--pattern', name, '--dir', str(destination))
            if ARCHIVE in names and sha256(destination / name) not in archived_hashes:
                raise ValueError('Remaining asset differs from source archive: ' + name)
        print('Downloaded original sources; checking manifest and creating archive.', flush=True)
        restore_manifest_names(source_dir)
        archive = root / ARCHIVE
        create_archive(source_dir, archive)
        # Never overwrite an existing archive until its identity is established.
        if ARCHIVE not in names:
            gh('release', 'upload', TAG, str(archive), '--repo', REPO)
        print('Archive uploaded; downloading it again for verification.', flush=True)
        check = root / 'download-check'
        check.mkdir()
        gh('release', 'download', TAG, '--repo', REPO, '--pattern', ARCHIVE, '--dir', str(check))
        verify_archive(check / ARCHIVE, source_dir)
        if sha256(archive) != sha256(check / ARCHIVE):
            print('Existing archive bytes differ; verified contained files are identical.')
        notes = root / 'notes.md'
        base = f'https://github.com/{REPO}/releases/download/{TAG}'
        notes.write_text(
            '## Download\n\n'
            f'- [Windows x86-64]({base}/PasswordGenerator-windows-x86_64.zip)\n'
            f'- [Linux x86-64]({base}/PasswordGenerator-linux-x86_64.tar.gz)\n\n'
            '## Third-party sources\n\n'
            f'[Download complete dependency sources and checksum manifest]({base}/{ARCHIVE}). '
            'This archive preserves all 53 original source files and their manifest. '
            'It is provided for license compliance; it is not required to run the application.\n\n'
            + (release['body'][release['body'].index('**Full Changelog**'):] if '**Full Changelog**' in release['body'] else release['body']) + '\n', encoding='utf-8')
        gh('release', 'edit', TAG, '--repo', REPO, '--notes-file', str(notes))
        print('Published archive verified; removing replaced source assets.', flush=True)
        for name in sorted(sources):
            gh('release', 'delete-asset', TAG, name, '--repo', REPO, '--yes')
    remaining = json.loads(gh('release', 'view', TAG, '--repo', REPO, '--json', 'assets'))
    if {a['name'] for a in remaining['assets']} != BINARIES | {ARCHIVE}:
        raise ValueError('Unexpected final assets; inspect release')
    print('Verified: desktop binaries and complete third-party source archive remain.')


if __name__ == '__main__':
    main()
