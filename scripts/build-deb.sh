#!/usr/bin/env bash
# Build paket .deb ke dist/. Butuh: dpkg-deb, python3, python3-pyqt5, python3-psutil.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PKG="desktop-htop"
STAGE="$ROOT/build/${PKG}_${VERSION}_all"
OUT="$ROOT/dist"

rm -rf "$STAGE"
mkdir -p "$STAGE" "$OUT"
cp -r "$ROOT/packaging/." "$STAGE/"
sed -i "s/@VERSION@/$VERSION/" "$STAGE/DEBIAN/control"

install -Dm755 "$ROOT/htop_widget.py" "$STAGE/usr/lib/desktop-htop/htop_widget.py"
python3 "$ROOT/scripts/make_icons.py" "$STAGE"

gzip -9n "$STAGE/usr/share/man/man1/desktop-htop.1"

# changelog Debian minimal (isi lengkap ada di CHANGELOG.md)
DOC="$STAGE/usr/share/doc/$PKG"
{
  echo "$PKG ($VERSION) unstable; urgency=low"
  echo
  echo "  * Lihat CHANGELOG.md / see CHANGELOG.md"
  echo
  echo " -- Suryo Adhy Chandra <noreply@users.noreply.github.com>  $(date -R)"
} | gzip -9n > "$DOC/changelog.gz"

find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$STAGE/usr/bin/desktop-htop" "$STAGE/usr/lib/desktop-htop/htop_widget.py"

dpkg-deb --build --root-owner-group "$STAGE" "$OUT/${PKG}_${VERSION}_all.deb"
echo "OK -> $OUT/${PKG}_${VERSION}_all.deb"
