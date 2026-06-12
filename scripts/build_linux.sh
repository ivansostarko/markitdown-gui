#!/usr/bin/env bash
# Build the Linux app, .deb package and portable tarball.
# Requires: python3 (3.10+), python3-venv, python3-tk, dpkg-deb (for the .deb).

set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="$(python3 -c "import tomllib,pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")"
ARCH="amd64"
APP=markitdown-gui

echo "=== Installing build dependencies ==="
python3 -m pip install --upgrade pip
python3 -m pip install ".[dev]"

echo "=== Generating icons ==="
python3 scripts/generate_icon.py

echo "=== Building portable app with PyInstaller ==="
python3 -m PyInstaller markitdown_gui.spec --noconfirm

echo "=== Building tarball ==="
tar -C dist -czf "dist/${APP}-${VERSION}-linux-x86_64.tar.gz" "${APP}"

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "dpkg-deb not found — skipping .deb (tarball is ready in dist/)."
    exit 0
fi

echo "=== Building .deb package ==="
PKGROOT="build/debroot"
rm -rf "$PKGROOT"
mkdir -p "$PKGROOT/DEBIAN" \
         "$PKGROOT/opt/${APP}" \
         "$PKGROOT/usr/share/applications" \
         "$PKGROOT/usr/share/icons/hicolor/512x512/apps" \
         "$PKGROOT/usr/bin"

cp -r "dist/${APP}/." "$PKGROOT/opt/${APP}/"
cp installers/linux/markitdown-gui.desktop "$PKGROOT/usr/share/applications/"
cp assets/icon.png "$PKGROOT/usr/share/icons/hicolor/512x512/apps/${APP}.png"
ln -sf "/opt/${APP}/${APP}" "$PKGROOT/usr/bin/${APP}"

INSTALLED_SIZE=$(du -sk "$PKGROOT" | cut -f1)
cat > "$PKGROOT/DEBIAN/control" <<EOF
Package: ${APP}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: Ivan Sostarko <ivan.sostarko@hotmail.com>
Homepage: https://github.com/ivansostarko/markitdown-gui
Description: Desktop GUI for Microsoft MarkItDown
 Convert PDF, Office, HTML, image and audio files to clean,
 AI-ready Markdown with a modern drag-and-drop interface.
EOF

dpkg-deb --build --root-owner-group "$PKGROOT" "dist/${APP}_${VERSION}_${ARCH}.deb"

echo
echo "Done!"
echo "  Portable app : dist/${APP}/"
echo "  Tarball      : dist/${APP}-${VERSION}-linux-x86_64.tar.gz"
echo "  Debian pkg   : dist/${APP}_${VERSION}_${ARCH}.deb"
