import hashlib
import tarfile

import pytest

from scripts.source_archive import create_archive, verify_archive, restore_manifest_names


def sources(tmp_path):
    root = tmp_path / 'sources'
    root.mkdir()
    (root / 'example.tar.xz').write_bytes(b'original upstream bytes')
    digest = hashlib.sha256(b'original upstream bytes').hexdigest()
    (root / 'SOURCE_ASSETS_MANIFEST.txt').write_text(
        f'Original manifest\n\nfilename: example.tar.xz\nsize: 23\nSHA-256: {digest}\n\n')
    return root


def test_archive_preserves_original_sources_and_manifest(tmp_path):
    root = sources(tmp_path)
    output = tmp_path / 'sources.tar.gz'
    create_archive(root, output)
    verify_archive(output, root)
    with tarfile.open(output) as archive:
        assert archive.extractfile('example.tar.xz').read() == b'original upstream bytes'
        assert archive.extractfile('SOURCE_ASSETS_MANIFEST.txt').read() == (root / 'SOURCE_ASSETS_MANIFEST.txt').read_bytes()


def test_corrupt_source_blocks_packaging(tmp_path):
    root = sources(tmp_path)
    (root / 'example.tar.xz').write_bytes(b'changed')
    with pytest.raises(ValueError, match='mismatch'):
        create_archive(root, tmp_path / 'sources.tar.gz')


def test_unlisted_source_blocks_packaging(tmp_path):
    root = sources(tmp_path)
    (root / 'extra.txt').write_text('unexpected')
    with pytest.raises(ValueError, match='does not match'):
        create_archive(root, tmp_path / 'sources.tar.gz')


def test_archive_cannot_be_inside_sources(tmp_path):
    root = sources(tmp_path)
    with pytest.raises(ValueError, match='outside'):
        create_archive(root, root / 'archive.tar.gz')


def test_restores_github_sanitized_name_only_with_matching_digest(tmp_path):
    root = sources(tmp_path)
    manifest = root / 'SOURCE_ASSETS_MANIFEST.txt'
    manifest.write_text(manifest.read_text().replace('example.tar.xz', 'example~1.tar.xz'))
    (root / 'example.tar.xz').rename(root / 'example.1.tar.xz')
    restore_manifest_names(root)
    assert (root / 'example~1.tar.xz').read_bytes() == b'original upstream bytes'
    create_archive(root, tmp_path / 'sources.tar.gz')


def test_corruption_blocks_filename_restoration(tmp_path):
    root = sources(tmp_path)
    (root / 'example.tar.xz').rename(root / 'renamed.tar.xz')
    (root / 'renamed.tar.xz').write_bytes(b'corrupted upstream data')
    with pytest.raises(ValueError, match='Cannot uniquely restore'):
        restore_manifest_names(root)


def test_downloaded_archive_with_changed_contents_is_rejected(tmp_path):
    import io

    root = sources(tmp_path)
    output = tmp_path / 'tampered.tar.gz'
    with tarfile.open(output, 'w:gz') as archive:
        for path in root.iterdir():
            data = b'tampered' if path.name == 'example.tar.xz' else path.read_bytes()
            member = tarfile.TarInfo(path.name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    with pytest.raises(ValueError, match='checksum mismatch'):
        verify_archive(output, root)


def test_downloaded_archive_with_duplicate_member_is_rejected(tmp_path):
    root = sources(tmp_path)
    output = tmp_path / 'duplicate.tar.gz'
    with tarfile.open(output, 'w:gz') as archive:
        for path in [*root.iterdir(), root / 'example.tar.xz']:
            archive.add(path, arcname=path.name)
    with pytest.raises(ValueError, match='does not match'):
        verify_archive(output, root)
