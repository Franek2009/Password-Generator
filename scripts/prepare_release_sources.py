#!/usr/bin/env python3
"""Download and verify the corresponding-source assets for v1.0.0."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import urllib.request


QT_ASSETS = (
    (
        "Qt",
        "6.11.2",
        "qt-everywhere-src-6.11.2.tar.xz",
        "https://download.qt.io/archive/qt/6.11/6.11.2/single/"
        "qt-everywhere-src-6.11.2.tar.xz",
        "6dcfbca271d76a6502741a2c0dc6fc98ef7dd0b7b4cfd0abcebb285a86a26f33",
    ),
    (
        "PySide6/Shiboken6",
        "6.11.2",
        "pyside-setup-everywhere-src-6.11.2.zip",
        "https://download.qt.io/official_releases/QtForPython/pyside6/"
        "PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.zip",
        "c0fdd62b91a1d36d5ee2e1fb71050a32fbc93fcdeef0fdcb41d29afaaf00d9b5",
    ),
)

UBUNTU_ARCHIVE = "https://archive.ubuntu.com/ubuntu/pool"
UBUNTU_SOURCES = (
    ("at-spi2-core", "2.52.0-1build1", "main/a/at-spi2-core", "16b82af63769eefb96343366f34545f2af2de5c3661c83293f50969de7fa450a"),
    ("cairo", "1.18.0-3build1", "main/c/cairo", "873d57c66682a2bd419a696c4d47df5f27888c6fab022ce88e885c3b394d5b75"),
    ("fribidi", "1.0.13-3build1", "main/f/fribidi", "2df939e37ac9c71ed8de3c1dd55641f069fd2ed1bfa162e2ce03c819084ddbd1"),
    ("gcc-14", "14.2.0-4ubuntu2~24.04.1", "main/g/gcc-14", "50950080874a6ec6780dd60c243e21d9cda9d736bb32bca98d16095d27cc01b5"),
    ("gdk-pixbuf", "2.42.10+dfsg-3ubuntu3.3", "main/g/gdk-pixbuf", "b86025ff9d9ff4e39ec4b1773f23648f18556d154867e28b2f8fc1e589be80d0"),
    ("glib2.0", "2.80.0-6ubuntu3.8", "main/g/glib2.0", "d44112b09956f61ffd5790a1a40e42558dca287052a945078cffff9b2490ee84"),
    ("graphite2", "1.3.14-2ubuntu0.24.04.1", "main/g/graphite2", "c34a4358cdadcf881fe9794e13c27650f1c5de7bcd3aaf9a40a908047c4d44b4"),
    ("gtk+3.0", "3.24.41-4ubuntu1.3", "main/g/gtk+3.0", "b7ea9dda7ffd3f01f97d7ee673f130a82db5b346ade2d003e609e27886b35269"),
    ("keyutils", "1.6.3-3build1", "main/k/keyutils", "d81679165d93bfcadd5bf3fdca123ce0e4562e2ad9712aa2b9d8c2d1c701324d"),
    ("libdatrie", "0.2.13-3build1", "main/libd/libdatrie", "9d4bef261b1f1a5abd62c99ecdee5cd8b5dc09987b13d1ba1b66a73f1b1f0c6f"),
    ("libgcrypt20", "1.10.3-2ubuntu0.1", "main/libg/libgcrypt20", "ba9c5634309500f0248f9e648faa60e762238a47505ec037f451790a12d3c092"),
    ("libgpg-error", "1.47-3build2.1", "main/libg/libgpg-error", "3c8abf463c9ade945fe2e9d87c4aa2bff0026964207b07e99432d9ef6d9436d8"),
    ("libthai", "0.1.29-2build1", "main/libt/libthai", "a20705f03af7fca8f1bbed128e09020ed958f1bd092859e9133c6c600401a5e5"),
    ("pango1.0", "1.52.1+ds-1build1", "main/p/pango1.0", "faad8d9f21cdd77fb7c930f46506dc304fd66c49c6c5f9bb5d92a8bdc55ec744"),
    ("systemd", "255.4-1ubuntu8.17", "main/s/systemd", "8e5f4e5a7b7ee457214be1efd1ea1d380186c38b146d8c98af5da0f625d3c396"),
    ("util-linux", "2.39.3-9ubuntu6.5", "main/u/util-linux", "206b6fb92d3cb0f6b1a959a6173d81ebf4e0a340564378ac49667a16968578d8"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_sha256: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)

    actual_sha256 = sha256(temporary)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        temporary.unlink()
        raise RuntimeError(
            f"SHA-256 mismatch for {destination.name}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    temporary.replace(destination)


def parse_dsc(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    marker = "-----BEGIN PGP SIGNATURE-----"
    if marker in text:
        text = text.split("\n\n", 1)[1].split(marker, 1)[0]

    fields: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and current is not None:
            fields[current] += "\n" + line.strip()
        elif ":" in line:
            current, value = line.split(":", 1)
            fields[current] = value.strip()
        elif line:
            raise RuntimeError(f"Cannot parse Debian control line in {path}: {line}")
    return fields


def dsc_filename(package: str, version: str) -> str:
    return f"{package}_{version}.dsc"


def verify_audit_source_versions(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        actual = {row["source_package"]: row["source_version"] for row in rows}

    for package, version, _pool_path, _dsc_sha256 in UBUNTU_SOURCES:
        if actual.get(package) != version:
            raise RuntimeError(
                f"Linux audit source version mismatch for {package}: "
                f"expected {version}, got {actual.get(package)!r}"
            )


def download_ubuntu_source(
    output: Path,
    package: str,
    version: str,
    pool_path: str,
    dsc_sha256: str,
) -> list[tuple[Path, str, str, str]]:
    directory = output / "ubuntu" / package
    base_url = f"{UBUNTU_ARCHIVE}/{pool_path}"
    dsc_name = dsc_filename(package, version)
    dsc_path = directory / dsc_name
    dsc_url = f"{base_url}/{dsc_name}"
    download(dsc_url, dsc_path, dsc_sha256)

    fields = parse_dsc(dsc_path)
    if fields.get("Source") != package or fields.get("Version") != version:
        raise RuntimeError(
            f"Unexpected identity in {dsc_name}: "
            f"Source={fields.get('Source')!r}, Version={fields.get('Version')!r}"
        )

    records = [(dsc_path, package, version, dsc_url)]
    checksums = fields.get("Checksums-Sha256")
    if not checksums:
        raise RuntimeError(f"Checksums-Sha256 is missing from {dsc_name}")

    for line in checksums.splitlines():
        if not line:
            continue
        checksum, size_text, filename = line.split()
        path = directory / filename
        url = f"{base_url}/{filename}"
        download(url, path, checksum)
        if path.stat().st_size != int(size_text):
            raise RuntimeError(f"Size mismatch for {filename}")
        records.append((path, package, version, url))
    return records


def write_manifest(
    output: Path,
    records: list[tuple[Path, str, str, str]],
) -> None:
    lines = [
        "Password Generator v1.0.0 - Corresponding Source Assets",
        "========================================================",
        "",
    ]
    total_size = 0
    for path, component, version, origin in records:
        size = path.stat().st_size
        total_size += size
        lines.extend(
            (
                f"filename: {path.name}",
                f"size: {size}",
                f"SHA-256: {sha256(path)}",
                f"source package/component: {component}",
                f"version: {version}",
                f"origin: {origin}",
                "",
            )
        )
    lines.extend((f"TOTAL FILES: {len(records)}", f"TOTAL SIZE: {total_size}", ""))
    (output / "SOURCE_ASSETS_MANIFEST.txt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-source-packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_audit_source_versions(args.audit_source_packages)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    records: list[tuple[Path, str, str, str]] = []
    for component, version, filename, url, checksum in QT_ASSETS:
        path = output / "qt" / filename
        download(url, path, checksum)
        records.append((path, component, version, url))

    for source in UBUNTU_SOURCES:
        records.extend(download_ubuntu_source(output, *source))

    if len(records) != 53:
        raise RuntimeError(f"Expected 53 source files, got {len(records)}")
    write_manifest(output, records)


if __name__ == "__main__":
    main()
