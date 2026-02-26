import json
import os
import subprocess
import shutil
import wx
import requests
from locales import LM

class PatcherHelper:
    def __init__(self):
        self.system_apps_path = "/System/Applications"
        self.user_apps_path = os.path.expanduser("~/Applications")
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.downloads_path = os.path.join(self.base_path, "downloads")

    def check_if_patched(self, app_name):
        target = os.path.join(self.user_apps_path, app_name)
        return os.path.exists(os.path.join(target, "Contents"))

    def _refresh_dock(self, dlg=None):
        if dlg:
            dlg.Update(4, LM.get("LP_RESET_STATUS"))
        
        shell_cmd = 'find /private/var/folders -name "com.apple.dock.launchpad" -exec rm -rf {} +; killall Dock'
        clean_as_cmd = ['osascript', '-e', f'do shell script {subprocess.list2cmdline([shell_cmd])} with administrator privileges']
        subprocess.run(clean_as_cmd)

    def ensure_fileicon_installed(self, parent_window):
        fileicon_bin = shutil.which("fileicon") or "/usr/local/bin/fileicon"
        if os.path.exists(fileicon_bin):
            return True

        ask = wx.MessageDialog(parent_window, 
            LM.get("MSG_FILEICON_MISSING"), 
            LM.get("TITLE_DEP_MISSING"), wx.YES_NO | wx.ICON_QUESTION)
        
        if ask.ShowModal() != wx.ID_YES:
            return False

        dlg = wx.ProgressDialog(LM.get("TITLE_DEP_INSTALL"), LM.get("STATUS_DL_FILEICON"), maximum=100, parent=parent_window)
        
        try:
            if shutil.which("brew"):
                dlg.Update(30, LM.get("STATUS_BREW_INSTALL"))
                subprocess.run(["brew", "install", "fileicon"], capture_output=True)
            else:
                dlg.Update(50, LM.get("STATUS_MANUAL_DL"))
                url = "https://raw.githubusercontent.com/mklement0/fileicon/master/bin/fileicon"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    temp_path = os.path.join(self.base_path, "fileicon_tmp")
                    with open(temp_path, "wb") as f:
                        f.write(response.content)

                    dlg.Update(80, LM.get("STATUS_MV_BIN"))
                    install_cmd = f"chmod +x {temp_path}; mkdir -p /usr/local/bin; mv {temp_path} /usr/local/bin/fileicon"
                    as_cmd = 'do shell script "' + install_cmd + '" with administrator privileges'
                    subprocess.run(["osascript", "-e", as_cmd], check=True)
                else:
                    raise Exception(LM.get("ERR_DL_FAIL"))

            dlg.Update(100, LM.get("MSG_INSTALL_DONE"))
            dlg.Destroy()
            return True
        except Exception as e:
            if dlg: dlg.Destroy()
            wx.MessageBox(f"{LM.get('ERR_GENERAL')}: {str(e)}", LM.get("MENU_SUPPORT"), wx.OK | wx.ICON_ERROR)
            return False

    def get_available_patches(self):
        patches = []
        if not os.path.exists(self.downloads_path):
            return []

        config_path = os.path.join(self.base_path, "config.json")
        selected_branch = None
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    selected_branch = json.load(f).get("selected_pack")
            except: pass

        branches = [d for d in os.listdir(self.downloads_path) if os.path.isdir(os.path.join(self.downloads_path, d))]
        if not branches:
            return []

        if not selected_branch or selected_branch not in branches:
            selected_branch = branches[0]

        current_branch_path = os.path.join(self.downloads_path, selected_branch)
        icon_files = [f for f in os.listdir(current_branch_path) if f.lower().endswith(('.icns', '.png', '.jpg'))]

        for app_name in os.listdir(self.system_apps_path):
            if app_name.endswith(".app"):
                clean_name = app_name.replace(".app", "")
                match = next((icon for icon in icon_files if icon.lower().startswith(clean_name.lower())), None)
                if match:
                    patches.append({
                        'app_name': app_name,
                        'full_app_path': os.path.join(self.system_apps_path, app_name),
                        'icon_path': os.path.join(current_branch_path, match)
                    })
        return patches

    def apply_icons(self, selected_apps, reset_launchpad, parent_window):
        if not self.ensure_fileicon_installed(parent_window):
            return

        dlg = wx.ProgressDialog(LM.get("TITLE"), LM.get("STATUS_APPLYING"), maximum=4, parent=parent_window,
                                 style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH)

        try:
            dlg.Update(1, LM.get("STATUS_MKDIR"))
            if not os.path.exists(self.user_apps_path):
                os.makedirs(self.user_apps_path)

            for app in selected_apps:
                fake_app_path = os.path.join(self.user_apps_path, app['app_name'])
                if os.path.exists(fake_app_path):
                    if os.path.islink(fake_app_path): os.unlink(fake_app_path)
                    else: shutil.rmtree(fake_app_path)
                
                os.makedirs(fake_app_path)
                os.symlink(os.path.join(app['full_app_path'], "Contents"), os.path.join(fake_app_path, "Contents"))

            dlg.Update(2, LM.get("STATUS_INJECTING"))
            fileicon_path = shutil.which("fileicon") or "/usr/local/bin/fileicon"
            for app in selected_apps:
                dest = os.path.join(self.user_apps_path, app['app_name'])
                subprocess.run([fileicon_path, "set", dest, app['icon_path']], capture_output=True)

            dlg.Update(3, LM.get("STATUS_CACHE"))
            wx.MessageBox(LM.get("MSG_RESTART_APPS"), LM.get("TITLE"))

            self._refresh_dock(dlg)

            dlg.Update(4, LM.get("MSG_SUCCESS"))
            wx.MessageBox(LM.get("MSG_SUCCESS"), LM.get("TITLE"), wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            wx.MessageBox(f"{LM.get('ERR_GENERAL')}: {str(e)}", LM.get("MENU_SUPPORT"), wx.OK | wx.ICON_ERROR)
        finally:
            if dlg: dlg.Destroy()

    def restore_icons(self, parent_window):
        count = 0
        try:
            if os.path.exists(self.user_apps_path):
                for item in os.listdir(self.user_apps_path):
                    item_path = os.path.join(self.user_apps_path, item)
                    if item.endswith(".app") and os.path.isdir(item_path):
                        if os.path.islink(os.path.join(item_path, "Contents")):
                            shutil.rmtree(item_path)
                            count += 1
            
            self._refresh_dock()
            msg = LM.get("MSG_RESTORE_DONE").replace("{count}", str(count))
            wx.MessageBox(msg, LM.get("TITLE"), wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"{LM.get('ERR_GENERAL')}: {e}", LM.get("MENU_SUPPORT"), wx.ICON_ERROR)