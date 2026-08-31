# Third-party software notices

Password Generator is distributed under the MIT License. Standalone packages
also contain the components described below. Full license texts and preserved
upstream notices are stored in `licenses/`.

## Common components

### Qt, PySide6, and Shiboken6 6.11.2

Password Generator uses Qt 6.11.2, PySide6 6.11.2, and Shiboken6 6.11.2
under the GNU Lesser General Public License version 3 (LGPLv3).

They are distributed as separate shared libraries. Users may replace them
with modified, interface-compatible versions. The distribution terms for
Password Generator do not prohibit reverse engineering needed to debug such
modifications.

License texts:

- `licenses/LGPL-3.0.txt`
- `licenses/GPL-3.0.txt`, incorporated by the LGPLv3

Upstream: <https://www.qt.io/> and
<https://doc.qt.io/qtforpython-6/>.

The v1.0.0 GitHub Release must provide the following Corresponding Source
beside every binary package, at no additional charge:

- `qt-everywhere-src-6.11.2.tar.xz`
  (`6dcfbca271d76a6502741a2c0dc6fc98ef7dd0b7b4cfd0abcebb285a86a26f33`)
- `pyside-setup-everywhere-src-6.11.2.zip`
  (`c0fdd62b91a1d36d5ee2e1fb71050a32fbc93fcdeef0fdcb41d29afaaf00d9b5`)

Official sources:

- <https://download.qt.io/archive/qt/6.11/6.11.2/single/>
- <https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/>

These source assets implement the network-server mechanism in GPLv3 section
6(d). Qt also contains third-party code under its own licenses; its source and
notices are included in the Qt source archive and documented at
<https://doc.qt.io/qt-6/licenses-used-in-qt.html>.

### CPython 3.14.7

The bundles contain CPython 3.14.7 and its standard library under the Python
Software Foundation License Version 2 and incorporated historical licenses.
The complete notice is in `licenses/PYTHON-3.14.txt`.

Upstream: <https://www.python.org/>.

### OpenSSL

The Linux bundle contains OpenSSL 3.0.13 from Ubuntu. The previously audited
Windows bundle contains OpenSSL 3 libraries supplied with Qt and CPython.
OpenSSL 3 is licensed under Apache License 2.0, reproduced in
`licenses/APACHE-2.0.txt`.

Upstream: <https://openssl-library.org/>.

### Polish word list

The built-in Polish word list is the unmodified `diceware-pl` word list by
Maciek Tałaska. Its upstream README declares MIT licensing but provides no
separate formal license file or explicit copyright notice; none is invented
here.

Upstream: <https://github.com/MaciekTalaska/diceware-pl>. The MIT text is in
the top-level `LICENSE` file.

### Application icon

Unless stated otherwise, first-party source code and assets, including the
final application icon design, are licensed under the repository's MIT
License.

The icon incorporates
[Lock Alt by Amanda Moita](https://inkscape.org/~amandamoita/%E2%98%85lock-alt-svgrepo-com),
made available under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). CC0 does not
require attribution; this is a voluntary credit.

## Linux bundle

The Linux bundle was built on Ubuntu 24.04. Its 58 Ubuntu source packages and
exact versions are recorded by the release provenance audit. One unmodified,
deduplicated Debian copyright document for every source package is included
under `licenses/linux-ubuntu-24.04/`. Those documents preserve the applicable
copyright notices, license variants, and embedded license terms.

Important copyleft runtime components are:

- ATK/AT-SPI 2.52.0, GLib 2.80.0, GTK 3.24.41, GdkPixbuf 2.42.10,
  Pango 1.52.1, FriBidi 1.0.13, libdatrie 0.2.13, libthai 0.1.29,
  libgcrypt 1.10.3, libgpg-error 1.47, libsystemd 255.4, and the bundled
  `libblkid`/`libmount` portions of util-linux 2.39.3 — LGPL version 2/2.1
  or later; `licenses/LGPL-2.1.txt`.
- Cairo 1.18.0 — distributed under its LGPL-2.1 option;
  `licenses/LGPL-2.1.txt`.
- Graphite2 1.3.14 — distributed under its LGPL-2.1-or-later option;
  `licenses/LGPL-2.1.txt`.
- `libgcc_s` and `libstdc++` from GCC 14.2.0 — GPLv3 with GCC Runtime
  Library Exception 3.1; `licenses/GPL-3.0.txt` and
  `licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt`.
The bundled ICU 73.2 libraries supplied by the PySide6 wheel use the ICU
License and incorporated third-party notices reproduced in
`licenses/ICU-73.2.txt`.

Other bundled Ubuntu libraries use permissive, public-domain, or selectable
permissive terms. This includes OpenSSL, DBus (AFL-2.1 option), libcap
(BSD-3-Clause option), zstd (BSD-3-Clause option), X11/XCB, xkbcommon,
Fontconfig, FreeType, HarfBuzz, Pixman, PCRE2, libpng, libjpeg-turbo, Brotli,
bzip2, zlib, LZ4, liblzma, Expat, libffi, Kerberos, and their support
libraries. Their exact notices and terms are preserved in
`licenses/linux-ubuntu-24.04/`.

`libcom_err` 1.47.0 is built from the `lib/et` sources in e2fsprogs. Those
specific sources use MIT/SIPB-style and BSD-3-Clause-style terms rather than
the package's baseline GPL license. Their notices are reproduced in
`licenses/LIBCOM_ERR-1.47.0.txt`; no e2fsprogs source offer is required for
this library.

## Windows bundle

The Windows bundle contains the common Qt/PySide6/Shiboken6, CPython, OpenSSL,
word-list, and icon components described above.

It also contains Microsoft Visual C++ Runtime and Universal C Runtime
redistributable files. They are redistributed under the applicable Microsoft
Visual Studio 2022 and Windows SDK terms; no Microsoft source archive is
required from the application distributor.

Microsoft redistribution documentation:
<https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files>.

Qt's `opengl32sw.dll` is its Mesa-based software OpenGL implementation. Its
source and third-party notices are covered by the exact Qt source archive and
Qt third-party documentation identified above.
