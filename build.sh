#!/bin/bash

# --- CONFIGURAZIONE ---
APP_NAME="SkinX"
VERSION="1.2.0"
MAIN_SCRIPT="main.py"
ICON_PATH="assets/icon.icns"
DIST_DIR="dist"
BUILD_DIR="build"
DMG_NAME="${APP_NAME}_Installer_v${VERSION}.dmg"

echo "-----------------------------------------------"
echo "🚀 Inizio processo di Build per $APP_NAME v$VERSION"
echo "-----------------------------------------------"

# 1. Pulizia cartelle precedenti
echo "🧹 Pulizia vecchie build..."
rm -rf "$DIST_DIR"
rm -rf "$BUILD_DIR"
rm -f *.spec
rm -f "$DIST_DIR/$DMG_NAME"

# 2. Controllo dipendenze
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ Errore: PyInstaller non è installato. Installa con: pip install pyinstaller"
    exit 1
fi

# 3. Build dell'App Bundle con PyInstaller
echo "📦 Creazione App Bundle (.app)..."
pyinstaller --noconsole --onedir --windowed \
    --name "$APP_NAME" \
    --icon "$ICON_PATH" \
    --add-data "assets:assets" \
    --add-data "lang:lang" \
    --contents-directory "Contents" \
    "$MAIN_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Errore durante la compilazione con PyInstaller."
    exit 1
fi

echo "✅ App Bundle creato in $DIST_DIR/$APP_NAME.app"

# 4. Creazione del DMG (Richiede create-dmg installato tramite brew)
echo "💿 Creazione dell'installer DMG..."

if command -v create-dmg &> /dev/null; then
    # Rimuove DMG se già esistente
    rm -f "$DIST_DIR/$DMG_NAME"

    create-dmg \
      --volname "${APP_NAME} Installer" \
      --volicon "$ICON_PATH" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 100 \
      --icon "$APP_NAME.app" 175 120 \
      --hide-extension "$APP_NAME.app" \
      --app-drop-link 425 120 \
      "$DIST_DIR/$DMG_NAME" \
      "$DIST_DIR/$APP_NAME.app"

    echo "✅ Installer DMG creato: $DIST_DIR/$DMG_NAME"
else
    echo "⚠️  Avviso: 'create-dmg' non trovato. Il file DMG non è stato creato."
    echo "👉 Installa con: brew install create-dmg"
fi

echo "-----------------------------------------------"
echo "🎉 Build completata con successo!"
echo "-----------------------------------------------"