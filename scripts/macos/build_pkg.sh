#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-CalendarDesktopNotifications}"
BUNDLE_ID="${BUNDLE_ID:-com.nc.calendar-desktop-notifications}"

if ! command -v pipenv >/dev/null 2>&1; then
  echo "pipenv is required. Install it first (pip install pipenv)."
  exit 1
fi

export PIPENV_IGNORE_VIRTUALENVS="${PIPENV_IGNORE_VIRTUALENVS:-1}"

VERSION="$(pipenv run python -c 'from src._version import __version__; print(__version__)')"

echo "Building macOS app with PyInstaller (version: ${VERSION})..."
pipenv run python -m pip install --upgrade pyinstaller

rm -rf build dist

pipenv run pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "${APP_NAME}" \
  --add-data "sounds:sounds" \
  src/main.py

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "Expected app bundle not found at: ${APP_PATH}"
  exit 1
fi

PKGROOT="build/pkgroot"
mkdir -p "${PKGROOT}/Applications"
cp -R "${APP_PATH}" "${PKGROOT}/Applications/"

OUT_PKG="build/${APP_NAME}-${VERSION}-unsigned.pkg"

echo "Building macOS installer pkg: ${OUT_PKG}"
pkgbuild \
  --root "${PKGROOT}" \
  --install-location / \
  --identifier "${BUNDLE_ID}" \
  --version "${VERSION}" \
  "${OUT_PKG}"

if [[ ! -f "${OUT_PKG}" ]]; then
  echo "Package build failed (missing output): ${OUT_PKG}"
  exit 1
fi

echo "Done: ${OUT_PKG}"
