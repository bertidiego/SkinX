# SkinX
**The ultimate macOS system icon customizer.**

SkinX is a powerful and lightweight tool designed for macOS users who want to customize their experience. It allows you to apply high-quality custom icon packs to system applications (like Finder, Mail, Calendar, etc.) safely and easily.

---

## ✨ Features
* **Non-Destructive Patching**: Uses an intelligent system to apply icons without permanently modifying original system binaries.
* **Cloud Selection**: Browse and download different icon versions/branches directly from GitHub.
* **Fuzzy Search**: Quickly find the app you want to customize in your library.
* **Smart Update**: Automatically detects if a new version of the app or an icon pack is available via SHA-hash comparison.
* **Native Experience**: Built with wxPython for a fast, native-feeling macOS interface.
* **Multi-language Support**: Fully localized in English, Italian, and more.

---

## 🚀 Getting Started

### Prerequisites
* **macOS**: High Sierra or newer (optimized for Ventura/Sonoma/Sequoia).
* **fileicon**: The utility for managing custom icons. SkinX will offer to install it for you if it's missing (requires Homebrew).

### Installation
1. Go to the [Releases](https://github.com/bertidiego/SkinX/releases) page.
2. Download the latest `SkinX_Installer.dmg`.
3. Open the DMG and drag **SkinX** to your **Applications** folder.
4. Right-click the app and select **Open** to bypass the "Unidentified Developer" warning (since the app is self-signed).

---

## 🛠 How to Use

1. **Download Icons**: Click on **"Select icon version"**. Choose a pack from the list and click **Download**.
2. **Select Apps**: Click **"Apply changes"**. A list of compatible apps will appear.
3. **Search & Filter**: Use the search bar to find specific apps. SkinX automatically deselects apps that are already patched.
4. **Confirm**: Click **OK**. 
   > ⚠️ **Note**: Applying icons will refresh the Dock and Launchpad. At this time, it will reset your manual Launchpad icon order to alphabetical.
5. **Authenticate**: Enter your system password when prompted to allow the `fileicon` utility to apply the new icons.

---

## 🔄 Restoration
Changed your mind? Restoring original icons is easy:
1. Open SkinX.
2. Hold the **SHIFT** key on your keyboard.
3. The "Apply Changes" button will turn into **"Restore Icons"**.
4. Click it to remove all custom patches and return to the default Apple look.

---

## ❓ Troubleshooting

### The icons are not showing up in the Launchpad
This usually happens if the Launchpad database cache didn't clear correctly. 
* Go to **Settings (Preferences)** within SkinX.
* Click **"Refresh Launchpad Layout"**.
* This will force macOS to rebuild the icon database.

### "Rate Limit Exceeded" Error
SkinX communicates with GitHub to check for updates. If you see this error:
* **Solution**: Wait about 60 minutes for the limit to reset. This is a security measure from GitHub's API.

### Clear Download Cache
If you want to redownload all packs or free up space:
* Go to **Settings** -> **Clear Download Cache**. At this moment it will delete local files and reset the version tracking.

---

## 👨‍💻 Development
To run the source code locally:

1. **Clone the repo**:
   ```bash
   git clone [https://github.com/bertidiego/SkinX.git](https://github.com/bertidiego/SkinX.git)
   cd SkinX

1. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt

1. **Clone the repo**:
   ```bash
   python main.py

---

### 📜 License & Disclaimer
Icons are the property of Apple Inc. or their respective designers. SkinX is provided "as is" without warranty of any kind. Use it at your own risk.