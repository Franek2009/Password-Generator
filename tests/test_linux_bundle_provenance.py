import pytest

from scripts.linux_bundle_provenance import (
    classify_copyright,
    license_family,
    parse_debian_copyright,
)


OPENSSL_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: OpenSSL

Files: *
Copyright: 1995-2020, The OpenSSL Project Authors
License: Apache-2.0

Files: external/perl/Text-Template-1.56/*
Copyright: 2013, Mark Jason Dominus
License: Artistic or GPL-1+
"""

BZIP2_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: 1996-2010 Julian R Seward
License: BSD-variant

Files: debian/*
Copyright: Debian maintainers
License: GPL-2
"""

LIBPNG_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: 1995-2024 The PNG Reference Library Authors.
License: libpng

Files: contrib/pngexif/*
Copyright: 2017-2020 Cosmin Truta
License: expat
"""

LZ4_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: 2011-2020, Yann Collet.
License: BSD-2-clause

Files: programs/* tests/* examples/*
Copyright: Yann Collet
License: GPL-2+

Files: lib/lz4file.c lib/lz4file.h
Copyright: 2022, Xiaomi Inc.
License: BSD-2-clause
"""

HARFBUZZ_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: 2005-2023, HarfBuzz contributors
License: MIT

Files: src/hb-ucd.cc
Copyright: 2012, Grigori Goronzy
License: ISC

Files: test/shape/data/*
Copyright: Unicode Inc
License: Apache-2.0
"""

LIBFFI_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: 1996-2024 Red Hat, Inc.
License: Expat

Files: scripts/generate-darwin-source-and-headers.py
Copyright: 2011 Facebook, Inc.
License: BSD-3-clause
"""

GCC_COPYRIGHT = """\
The runtime libraries are covered by GPL-3.0 and the
GCC Runtime Library Exception, version 3.1.
"""


@pytest.mark.parametrize(
    ("copyright_text", "bundle_path", "matched_license", "family", "source_required"),
    [
        (OPENSSL_COPYRIGHT, "_internal/libssl.so.3", "Apache-2.0", "permissive", "unknown"),
        (BZIP2_COPYRIGHT, "_internal/libbz2.so.1.0", "BSD-variant", "permissive", "no"),
        (LIBPNG_COPYRIGHT, "_internal/libpng16.so.16", "libpng", "permissive", "no"),
        (LZ4_COPYRIGHT, "_internal/liblz4.so.1", "BSD-2-clause", "permissive", "no"),
        (HARFBUZZ_COPYRIGHT, "_internal/libharfbuzz.so.0", "MIT", "permissive", "no"),
        (LIBFFI_COPYRIGHT, "_internal/libffi.so.8", "Expat", "permissive", "no"),
    ],
)
def test_classification_uses_baseline_files_stanza(
    copyright_text, bundle_path, matched_license, family, source_required
):
    result = classify_copyright(copyright_text, bundle_path)

    assert result["matched_files_stanza"] == "*"
    assert result["matched_license"] == matched_license
    assert result["license_family"] == family
    assert result["source_required"] == source_required


@pytest.mark.parametrize("bundle_path", ["libgcc_s.so.1", "libstdc++.so.6"])
def test_gcc_runtime_requires_manual_review(bundle_path):
    result = classify_copyright(GCC_COPYRIGHT, bundle_path)

    assert result["license_family"] == "GPL-with-exception"
    assert result["manual_review"] is True
    assert result["source_required"] == "unknown"


def test_parser_preserves_folded_files_and_copyright_fields():
    paragraphs = parse_debian_copyright(
        "Files: lib/foo.c\n lib/foo.h\nCopyright: First holder\n Second holder\nLicense: MIT\n"
    )

    assert paragraphs == [{
        "files": "lib/foo.c\nlib/foo.h",
        "copyright": "First holder\nSecond holder",
        "license": "MIT",
    }]


def test_parser_ignores_deb822_comment_lines():
    paragraphs = parse_debian_copyright(
        "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n"
        "# a package comment\n\nFiles: *\nCopyright: Holder\nLicense: MIT\n"
    )

    assert paragraphs[-1]["files"] == "*"
    assert paragraphs[-1]["license"] == "MIT"


@pytest.mark.parametrize(
    ("license_name", "family", "manual_review", "source_required"),
    [
        ("LGPL-2.1+", "LGPL-2.1+", False, "yes"),
        ("LGPL-3.0", "LGPL-3.0", False, "yes"),
        ("GPL-2+", "GPL-2.0+", False, "yes"),
        ("GPL-3+", "GPL-3.0+", False, "yes"),
        ("BSD-3-clause or GPL-2", "dual-license", True, "unknown"),
        ("MIT and Apache-2.0", "mixed", True, "unknown"),
    ],
)
def test_license_family_has_explicit_source_policy(
    license_name, family, manual_review, source_required
):
    assert license_family(license_name) == (family, manual_review, source_required)
