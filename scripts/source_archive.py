"""Pack verified corresponding sources without losing filenames or metadata."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tarfile

MAX_ASSET_SIZE = 2**31 - 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def restore_manifest_names(root: Path) -> None:
    """GitHub changes characters such as '~' in uploaded asset names.

    Restore original upstream names only after matching the manifest digest.
    """
    current = {}
    records = []
    for line in (root / 'SOURCE_ASSETS_MANIFEST.txt').read_text(encoding='utf-8').splitlines() + ['']:
        if not line.strip():
            if 'filename' in current:
                records.append(current)
            current = {}
        elif ': ' in line:
            key, value = line.split(': ', 1)
            current[key] = value
    for record in records:
        name = record['filename']
        if Path(name).name != name:
            raise ValueError('Unsafe source filename in manifest')
        if (root / name).exists():
            continue
        candidates = [p for p in root.iterdir() if p.is_file()
                      and p.stat().st_size == int(record['size'])
                      and sha256(p) == record['SHA-256']]
        if len(candidates) != 1:
            raise ValueError('Cannot uniquely restore original source filename: ' + name)
        candidates[0].rename(root / name)


def verify_sources(root: Path) -> list[Path]:
    manifest = root / 'SOURCE_ASSETS_MANIFEST.txt'
    records = []
    current = {}
    for line in manifest.read_text(encoding='utf-8').splitlines() + ['']:
        if not line.strip():
            if 'filename' in current:
                records.append(current)
            current = {}
        elif ': ' in line:
            key, value = line.split(': ', 1)
            current[key] = value
    files = {p.name: p for p in root.rglob('*') if p.is_file() and p != manifest}
    if len(files) != len([p for p in root.rglob('*') if p.is_file() and p != manifest]):
        raise ValueError('Duplicate source filenames')
    if not records or len({r['filename'] for r in records}) != len(records):
        raise ValueError('Empty or duplicate source manifest')
    if set(files) != {r['filename'] for r in records}:
        raise ValueError('Manifest does not match source files')
    for record in records:
        path = files[record['filename']]
        if path.stat().st_size != int(record['size']) or sha256(path) != record['SHA-256']:
            raise ValueError(f'Source checksum or size mismatch: {path.name}')
    return [manifest, *sorted(files.values())]


def verify_archive(archive: Path, root: Path) -> None:
    expected = {str(p.relative_to(root)): p for p in verify_sources(root)}
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != set(expected):
            raise ValueError('Archive does not match verified sources')
        for member in members:
            if not member.isfile():
                raise ValueError('Only regular source files are allowed')
            contents = stream.extractfile(member)
            if contents is None or hashlib.file_digest(contents, 'sha256').hexdigest() != sha256(expected[member.name]):
                raise ValueError(f'Archive checksum mismatch: {member.name}')


def create_archive(root: Path, output: Path) -> None:
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('Archive must be outside the source directory')
    files = verify_sources(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz', compresslevel=1) as stream:
        for path in files:
            stream.add(path, arcname=str(path.relative_to(root)), recursive=False)
    if output.stat().st_size > MAX_ASSET_SIZE:
        raise ValueError('Source archive exceeds GitHub asset size limit')
    verify_archive(output, root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    create_archive(args.sources, args.output)
