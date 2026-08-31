#!/usr/bin/env python3
"""Create package/license provenance for ELF shared objects in PyInstaller onedir."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def command(*args: str) -> str:
    return subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ).stdout.strip()


def is_shared_object(path: str) -> bool:
    name = Path(path).name
    return name.endswith(".so") or ".so." in name


def package_owners(path: Path) -> list[str]:
    owners: set[str] = set()
    for candidate in dict.fromkeys((str(path), str(path.resolve()))):
        try:
            output = command("dpkg-query", "-S", candidate)
        except (OSError, subprocess.CalledProcessError):
            continue
        for line in output.splitlines():
            owner, separator, _ = line.partition(": ")
            if separator:
                owners.add(owner)
    return sorted(owners)


def package_metadata(package: str) -> dict[str, str]:
    fields = command(
        "dpkg-query",
        "-W",
        "-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}",
        package,
    ).split("\t")
    fields += [""] * (4 - len(fields))
    binary, version, source, source_version = fields[:4]
    if not source:
        source = binary.split(":", 1)[0]
    if not source_version:
        source_version = version
    return {
        "package": binary,
        "version": version,
        "source_package": source,
        "source_version": source_version,
    }


def copyright_path(package: str) -> Path | None:
    name = package.split(":", 1)[0]
    candidate = Path("/usr/share/doc") / name / "copyright"
    return candidate.resolve() if candidate.exists() else None


def wheel_files() -> dict[Path, tuple[str, str]]:
    result: dict[Path, tuple[str, str]] = {}
    for distribution in importlib_metadata.distributions():
        name = distribution.metadata.get("Name", "unknown-wheel")
        version = distribution.version
        for relative in distribution.files or ():
            located = Path(distribution.locate_file(relative))
            if located.exists() and (located.name.endswith(".so") or ".so." in located.name):
                result[located.resolve()] = (name, version)
    return result


IGNORED_FILES_PARTS = {
    "debian",
    "doc",
    "docs",
    "example",
    "examples",
    "fuzz",
    "ossfuzz",
    "perf",
    "program",
    "programs",
    "script",
    "scripts",
    "test",
    "tests",
    "tool",
    "tools",
}


def parse_debian_copyright(text: str) -> list[dict[str, str]]:
    """Parse paragraphs and folded fields from DEP-5 copyright metadata."""
    paragraphs: list[dict[str, str]] = []
    fields: dict[str, str] = {}
    current_field: str | None = None

    def finish_paragraph() -> None:
        nonlocal fields, current_field
        if fields:
            paragraphs.append(fields)
        fields = {}
        current_field = None

    for line in text.splitlines() + [""]:
        if line.startswith("#"):
            continue
        if not line.strip():
            finish_paragraph()
            continue
        if line[0].isspace():
            if current_field is None:
                raise ValueError("continuation line without a field")
            continuation = line[1:]
            fields[current_field] += "\n" + continuation
            continue
        field, separator, value = line.partition(":")
        if not separator or not field:
            raise ValueError(f"invalid DEP-5 field line: {line!r}")
        current_field = field.lower()
        fields[current_field] = value.lstrip()

    return paragraphs


def license_tokens(text: str) -> list[str]:
    try:
        paragraphs = parse_debian_copyright(text)
    except ValueError:
        return []
    return sorted({
        paragraph["license"].splitlines()[0]
        for paragraph in paragraphs
        if paragraph.get("license")
    })


def ignored_files_stanza(files: str) -> bool:
    patterns = files.split()
    return bool(patterns) and all(
        any(
            part.rstrip("*").lower() in IGNORED_FILES_PARTS
            for part in Path(pattern.removeprefix("./")).parts
        )
        for pattern in patterns
    )


def license_family(license_name: str) -> tuple[str, bool, str]:
    """Return family, manual-review flag, and source requirement."""
    normalized = " ".join(license_name.lower().split())
    if not normalized:
        return "unknown", True, "unknown"
    if "exception" in normalized:
        return "GPL-with-exception", True, "unknown"
    if " or " in normalized:
        return "dual-license", True, "unknown"
    if " and " in normalized or "," in normalized:
        return "mixed", True, "unknown"
    if re.search(r"lgpl[- ]?3(?:\.0)?(?:\+|-or-later)?", normalized):
        return "LGPL-3.0", False, "yes"
    if re.search(r"lgpl[- ]?2\.1(?:\+|-or-later)?", normalized):
        return "LGPL-2.1+", False, "yes"
    if re.search(r"gpl[- ]?3(?:\.0)?(?:\+|-or-later)?", normalized):
        return "GPL-3.0+", False, "yes"
    if re.search(r"gpl[- ]?2(?:\.0)?(?:\+|-or-later)?", normalized):
        return "GPL-2.0+", False, "yes"
    permissive = (
        "apache", "bsd", "bzip2", "expat", "freetype", "ftl", "isc",
        "libpng", "mit", "public-domain", "public domain", "unicode", "x11",
        "zlib",
    )
    if any(marker in normalized for marker in permissive):
        return "permissive", False, "no"
    return "unknown", True, "unknown"


def classify_copyright(text: str, bundled_path: str) -> dict[str, object]:
    """Classify a bundled library from its applicable DEP-5 file stanza."""
    basename = Path(bundled_path).name
    lower_text = text.lower()
    if basename in {"libgcc_s.so.1", "libstdc++.so.6"}:
        if "gcc runtime library exception" in lower_text:
            return {
                "matched_files_stanza": "GCC runtime metadata",
                "matched_license": "GPL-3.0+ WITH GCC Runtime Library Exception",
                "license_family": "GPL-with-exception",
                "manual_review": True,
                "source_required": "unknown",
                "files_stanzas": "[]",
            }
        return {
            "matched_files_stanza": "",
            "matched_license": "",
            "license_family": "unknown",
            "manual_review": True,
            "source_required": "unknown",
            "files_stanzas": "[]",
        }

    try:
        paragraphs = parse_debian_copyright(text)
    except ValueError:
        return {
            "matched_files_stanza": "",
            "matched_license": "",
            "license_family": "unknown",
            "manual_review": True,
            "source_required": "unknown",
            "files_stanzas": "[]",
        }

    file_stanzas = [
        {
            "files": paragraph["files"],
            "copyright": paragraph.get("copyright", ""),
            "license": paragraph.get("license", "").splitlines()[0],
        }
        for paragraph in paragraphs
        if "files" in paragraph
    ]
    baseline = next(
        (stanza for stanza in file_stanzas if stanza["files"].strip() == "*"),
        None,
    )
    if baseline is None or not baseline["license"]:
        return {
            "matched_files_stanza": "",
            "matched_license": "",
            "license_family": "unknown",
            "manual_review": True,
            "source_required": "unknown",
            "files_stanzas": json.dumps(file_stanzas, sort_keys=True),
        }

    family, manual_review, source_required = license_family(baseline["license"])
    relevant_overrides = [
        stanza
        for stanza in file_stanzas
        if stanza is not baseline and not ignored_files_stanza(stanza["files"])
    ]
    differing_overrides = [
        stanza for stanza in relevant_overrides
        if stanza["license"] != baseline["license"]
    ]
    if differing_overrides:
        manual_review = True
        override_requirements = {
            license_family(stanza["license"])[2]
            for stanza in differing_overrides
        }
        if override_requirements != {source_required}:
            source_required = "unknown"

    return {
        "matched_files_stanza": baseline["files"],
        "matched_license": baseline["license"],
        "license_family": family,
        "manual_review": manual_review,
        "source_required": source_required,
        "files_stanzas": json.dumps(file_stanzas, sort_keys=True),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toc", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    copyright_dir = args.output / "copyright"
    copyright_dir.mkdir(exist_ok=True)

    toc = ast.literal_eval(args.toc.read_text(encoding="utf-8"))
    entries = toc[0] if isinstance(toc, tuple) else toc
    records: list[dict[str, object]] = []
    wheels = wheel_files()

    for destination, source, entry_type in entries:
        if entry_type not in {"BINARY", "EXTENSION"} or not is_shared_object(destination):
            continue
        source_path = Path(source)
        bundled_path = args.bundle / "_internal" / destination
        if not bundled_path.exists():
            bundled_path = args.bundle / destination

        base = {
            "bundle_path": str(bundled_path.relative_to(args.bundle)),
            "source_path": str(source_path),
            "source_realpath": str(source_path.resolve()),
            "sha256": hashlib.sha256(bundled_path.read_bytes()).hexdigest(),
        }
        owners = package_owners(source_path)
        if not owners:
            wheel = wheels.get(source_path.resolve())
            if wheel:
                records.append({
                    **base,
                    "origin": "python-wheel",
                    "package": wheel[0],
                    "version": wheel[1],
                    "source_package": wheel[0],
                    "source_version": wheel[1],
                    "copyright_file": "",
                    "license_tokens": [],
                    "matched_files_stanza": "",
                    "matched_license": "",
                    "license_family": "manual-review",
                    "manual_review": True,
                    "notice_required": True,
                    "source_required": "unknown",
                    "files_stanzas": "[]",
                })
                continue
            python_prefix = Path(sys.base_prefix).resolve()
            try:
                python_relative = source_path.resolve().relative_to(python_prefix)
            except ValueError:
                pass
            else:
                python_lib = f"python{sys.version_info.major}.{sys.version_info.minor}"
                if source_path.name.startswith("libpython") or python_lib in python_relative.parts:
                    records.append({
                        **base,
                        "origin": "cpython-runtime",
                        "package": "CPython",
                        "version": sys.version.split()[0],
                        "source_package": "CPython",
                        "source_version": sys.version.split()[0],
                        "copyright_file": "",
                        "license_tokens": [],
                        "matched_files_stanza": "CPython distribution",
                        "matched_license": "PSF-2.0 and incorporated licenses",
                        "license_family": "permissive",
                        "manual_review": False,
                        "notice_required": True,
                        "source_required": "no",
                        "files_stanzas": "[]",
                    })
                    continue
            records.append({
                **base,
                "origin": "unknown",
                "package": "",
                "version": "",
                "source_package": "",
                "source_version": "",
                "copyright_file": "",
                "license_tokens": [],
                "matched_files_stanza": "",
                "matched_license": "",
                "license_family": "unknown (not owned by dpkg)",
                "manual_review": True,
                "notice_required": True,
                "source_required": "unknown",
                "files_stanzas": "[]",
            })
            continue

        for owner in owners:
            metadata = package_metadata(owner)
            notice = copyright_path(metadata["package"])
            notice_text = notice.read_text(encoding="utf-8", errors="replace") if notice else ""
            tokens = license_tokens(notice_text)
            classification = classify_copyright(notice_text, base["bundle_path"])
            copied_notice = ""
            if notice:
                safe_name = re.sub(r"[^A-Za-z0-9_.+-]", "_", metadata["package"])
                target = copyright_dir / f"{safe_name}.txt"
                shutil.copy2(notice, target)
                copied_notice = str(target.relative_to(args.output))
            records.append({
                **base,
                "origin": "ubuntu-package",
                **metadata,
                "copyright_file": str(notice) if notice else "",
                "copied_notice": copied_notice,
                "license_tokens": tokens,
                **classification,
                "notice_required": True,
            })

    records.sort(key=lambda item: (str(item["bundle_path"]), str(item["package"])))
    (args.output / "inventory.json").write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    columns = [
        "bundle_path", "source_path", "source_realpath", "sha256", "origin", "package",
        "version", "source_package", "source_version", "copyright_file",
        "copied_notice", "license_tokens", "matched_files_stanza", "matched_license",
        "license_family", "manual_review", "notice_required", "source_required",
        "files_stanzas",
    ]
    with (args.output / "inventory.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    source_packages = sorted({
        (
            str(record["source_package"]),
            str(record["source_version"]),
            str(record["matched_license"]),
            str(record["license_family"]),
            str(record["manual_review"]),
            str(record["source_required"]),
        )
        for record in records
        if record["origin"] == "ubuntu-package"
        and record["source_package"]
        and record["source_version"]
    })
    with (args.output / "source-packages.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(
            (
                "source_package", "source_version", "matched_license", "license_family",
                "manual_review", "source_required",
            )
        )
        writer.writerows(source_packages)

    library_paths = [
        args.bundle / "_internal",
        args.bundle / "_internal" / "PySide6" / "Qt" / "lib",
    ]
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = ":".join(str(path) for path in library_paths)
    external: dict[str, dict[str, str]] = {}
    elf_files = [args.bundle / "PasswordGenerator"] + [
        path for path in args.bundle.rglob("*") if path.is_file() and is_shared_object(path.name)
    ]
    for elf in elf_files:
        result = subprocess.run(
            ["ldd", str(elf)], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=environment,
        )
        for line in result.stdout.splitlines():
            match = re.search(r"=>\s+(/\S+)", line)
            if not match:
                match = re.match(r"\s*(/\S+)\s+\(", line)
            if not match:
                continue
            resolved = Path(match.group(1)).resolve()
            try:
                resolved.relative_to(args.bundle.resolve())
                continue
            except ValueError:
                pass
            owners = package_owners(resolved)
            package = owners[0] if owners else ""
            metadata = package_metadata(package) if package else {
                "package": "", "version": "", "source_package": "", "source_version": "",
            }
            external[str(resolved)] = {
                "resolved_path": str(resolved),
                **metadata,
                "classification": "system/runtime dependency; not bundled",
            }
    external_columns = [
        "resolved_path", "package", "version", "source_package",
        "source_version", "classification",
    ]
    with (args.output / "external-dependencies.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=external_columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(sorted(external.values(), key=lambda item: item["resolved_path"]))

    unknown = [
        record for record in records
        if record["origin"] == "unknown"
        or (
            record["origin"] == "ubuntu-package"
            and (
                not record["copyright_file"]
                or record["license_family"] == "unknown"
            )
        )
    ]
    if unknown:
        print(f"Manual review required for {len(unknown)} entries", flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
