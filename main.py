import wx
import os
import requests
import threading
import json
import sys  # Necessario per resource_path
from PIL import Image as PILImage
from data import Data
from wx_select import VersionSelectFrame
from helper import PatcherHelper
from locales import LM 
from wx_settings import SettingsFrame

def resource_path(relative_path):
    """ Ottiene il percorso assoluto delle risorse, compatibile con PyInstaller """
    try:
        # PyInstaller crea una cartella temporanea e memorizza il percorso in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class IconSelectorDialog(wx.Dialog):
    def __init__(self, parent, available_patches):
        super().__init__(parent, title=LM.get("TITLE"), size=(750, 600),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.available = available_patches
        self.helper = PatcherHelper()
        self.checks = []
        self.rows = []
        self.SetBackgroundColour(wx.Colour(245, 245, 247))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        header = wx.StaticText(self, label=LM.get("DLG_SELECT_ICONS"))
        header.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=".AppleSystemUIFont"))
        main_sizer.Add(header, 0, wx.ALL | wx.CENTER, 15)

        self.search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search.SetHint("Search apps...")
        self.search.Bind(wx.EVT_TEXT, self.on_search)
        main_sizer.Add(self.search, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        self.scroll = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.BORDER_SUNKEN)
        self.scroll.SetScrollRate(0, 10)
        self.scroll.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        for item in self.available:
            row_panel = wx.Panel(self.scroll)
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            is_patched = self.helper.check_if_patched(item['app_name'])
            cb = wx.CheckBox(row_panel, label="")
            cb.SetValue(not is_patched) 
            self.checks.append(cb)
            
            bmp = wx.StaticBitmap(row_panel, size=(64, 64))
            try:
                path = item['icon_path']
                if path.lower().endswith('.icns'):
                    with PILImage.open(path) as img_pil:
                        img_pil = img_pil.resize((64, 64), PILImage.Resampling.LANCZOS)
                        if img_pil.mode != 'RGBA':
                            img_pil = img_pil.convert('RGBA')
                        wx_img = wx.Image(64, 64)
                        wx_img.SetData(img_pil.convert("RGB").tobytes())
                        wx_img.SetAlpha(img_pil.getchannel("A").tobytes())
                        bmp.SetBitmap(wx.Bitmap(wx_img))
                else:
                    img = wx.Image(path, wx.BITMAP_TYPE_ANY)
                    if img.IsOk():
                        bmp.SetBitmap(wx.Bitmap(img.Rescale(64, 64, wx.IMAGE_QUALITY_HIGH)))
            except: pass

            name_str = item['app_name']
            if is_patched:
                name_str += f" ({LM.get('LBL_INSTALLED')})"
            
            name = wx.StaticText(row_panel, label=name_str)
            name.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_MEDIUM, faceName=".AppleSystemUIFont"))
            if is_patched:
                name.SetForegroundColour(wx.Colour(120, 120, 120))

            row_sizer.Add(cb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
            row_sizer.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            row_sizer.Add(name, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
            
            row_panel.SetSizer(row_sizer)
            self.scroll_sizer.Add(row_panel, 0, wx.EXPAND)
            line = wx.StaticLine(self.scroll)
            self.scroll_sizer.Add(line, 0, wx.EXPAND)
            
            self.rows.append({'panel': row_panel, 'line': line, 'name': item['app_name'].lower()})

        self.scroll.SetSizer(self.scroll_sizer)
        main_sizer.Add(self.scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_all = wx.Button(self, label=LM.get("DLG_BTN_ALL"))
        btn_none = wx.Button(self, label=LM.get("DLG_BTN_NONE"))
        btn_all.Bind(wx.EVT_BUTTON, self.on_select_all)
        btn_none.Bind(wx.EVT_BUTTON, self.on_deselect_all)
        
        ctrl_sizer.Add(btn_all, 1, wx.ALL, 5)
        ctrl_sizer.Add(btn_none, 1, wx.ALL, 5)
        main_sizer.Add(ctrl_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_CENTER | wx.ALL, 15)
        self.SetSizer(main_sizer)

    def on_search(self, event):
        query = self.search.GetValue().lower()
        for row in self.rows:
            show = query in row['name']
            row['panel'].Show(show)
            row['line'].Show(show)
        self.scroll.Layout()
        self.scroll.FitInside()

    def on_select_all(self, event):
        for i, row in enumerate(self.rows):
            if row['panel'].IsShown():
                self.checks[i].SetValue(True)

    def on_deselect_all(self, event):
        for i, row in enumerate(self.rows):
            if row['panel'].IsShown():
                self.checks[i].SetValue(False)

    def GetSelectedItems(self):
        return [self.available[i] for i, cb in enumerate(self.checks) if cb.GetValue()]

class MainFrame(wx.Frame):
    def __init__(self, parent):
        self.constants = Data()
        # Il config rimane fuori dal bundle per poter essere scritto
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self._load_saved_language()
        
        full_title = f"SkinX v{self.constants.patcher_version} ({self.constants.patcher_subversion})"
        super(MainFrame, self).__init__(parent, title=full_title, size=(650, 420), 
                                        style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        
        # Imposta l'icona dell'app nel dock/finestra
        icon_path = resource_path("assets/icon.icns")
        if os.path.exists(icon_path):
            self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICON))

        self.helper = PatcherHelper()
        self.font_model = wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=".AppleSystemUIFont")
        self.font_desc = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=".AppleSystemUIFont")

        self.btn_apply = None; self.desc_apply = None; self.pack_label = None
        self._generate_elements()
        self.Centre(); self.Show()
        
        threading.Thread(target=self._check_app_updates, daemon=True).start()
        threading.Thread(target=self._check_icon_updates, daemon=True).start()

    def _load_saved_language(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                LM.load_language(config.get("language", "it_it"))
        except: LM.load_language("it_it")

    def _check_app_updates(self):
        try:
            repo_api = "https://api.github.com/repos/bertidiego/SkinX/releases/latest"
            r = requests.get(repo_api, timeout=5)
            if r.status_code == 200:
                latest = r.json().get("tag_name", "").replace("v", "")
                if latest and latest != self.constants.patcher_version:
                    wx.CallAfter(self._show_app_update_popup, latest, r.json().get("html_url"))
        except: pass

    def _show_app_update_popup(self, ver, url):
        msg = f"A new version of SkinX (v{ver}) is available.\nWould you like to visit the download page?"
        if wx.MessageBox(msg, "App Update", wx.YES_NO | wx.ICON_INFORMATION) == wx.YES:
            import webbrowser
            webbrowser.open(url)

    def _check_icon_updates(self):
        if not os.path.exists(self.config_path): return
        try:
            with open(self.config_path, 'r') as f: config = json.load(f)
            installed_shas = config.get("installed_shas", {})
            sources = config.get("sources", ["https://api.github.com/repos/bertidiego/SkinX-icons/branches"])
            
            for api_url in sources:
                r = requests.get(api_url, timeout=10)
                if r.status_code == 200:
                    for branch in r.json():
                        name = branch['name']
                        remote_sha = branch.get('commit', {}).get('sha')
                        
                        if name in installed_shas:
                            if installed_shas[name] != remote_sha:
                                wx.CallAfter(self._show_update_popup, name)
                                return 
        except: pass

    def _show_update_popup(self, branch_name):
        msg = LM.get("MSG_UPDATE_ICON_AVAILABLE").replace("{branch}", branch_name)
        dlg = wx.MessageDialog(self, msg, LM.get("TITLE_UPDATE_AVAILABLE"), wx.YES_NO | wx.ICON_INFORMATION)
        dlg.SetYesNoLabels(LM.get("BTN_OPEN_SELECTOR"), LM.get("BTN_CANCEL"))
        if dlg.ShowModal() == wx.ID_YES:
            self.on_select_version(None)
        dlg.Destroy()

    def _generate_elements(self):
        title_label = wx.StaticText(self, label=f"{LM.get('TITLE')} {self.constants.patcher_version}", pos=(-1, 10))
        title_label.SetFont(wx.Font(19, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=".AppleSystemUIFont"))
        title_label.Centre(wx.HORIZONTAL)

        self.pack_label = wx.StaticText(self, label="", pos=(-1, 40))
        self.pack_label.SetFont(self.font_model)
        self._refresh_pack_label()

        menu_configs = [
            {"key": "MENU_APPLY", "func": self.on_apply_changes, "desc": "DESC_APPLY", "icon": "assets/apply.png"},
            {"key": "MENU_SELECT", "func": self.on_select_version, "desc": "DESC_SELECT", "icon": "assets/sel.png"},
            {"key": "MENU_PREF", "func": self.on_open_settings, "desc": "DESC_PREF", "icon": "assets/pref.png"},
            {"key": "MENU_SUPPORT", "func": self.on_dummy, "desc": "DESC_SUPPORT", "icon": "assets/docs.png"}
        ]

        bx, by, idx = 55, 95, 0
        for cfg in menu_configs:
            # CORREZIONE: Usiamo resource_path per le icone del menu
            icon_p = resource_path(cfg["icon"])
            if os.path.exists(icon_p):
                img = wx.Image(icon_p, wx.BITMAP_TYPE_ANY).Rescale(1024, 1024, wx.IMAGE_QUALITY_HIGH)
                wx.StaticBitmap(self, bitmap=wx.Bitmap(img), pos=(bx - 15, by), size=(80, 80))

            btn = wx.Button(self, label=LM.get(cfg["key"]), pos=(bx + 75, by), size=(180, 30))
            btn.SetFont(self.font_model); btn.Bind(wx.EVT_BUTTON, cfg["func"])
            
            desc = wx.StaticText(self, label=LM.get(cfg["desc"]), pos=(bx + 85, by + 35))
            desc.SetFont(self.font_desc)

            if cfg["key"] == "MENU_APPLY":
                self.btn_apply = btn; self.desc_apply = desc
                self.btn_apply.Bind(wx.EVT_UPDATE_UI, self.on_update_apply_ui)

            by += 115; idx += 1
            if idx == 2: bx, by = 345, 95

        discl = wx.StaticText(self, label=LM.get("DISCLAIMER"), pos=(-1, 335))
        discl.SetFont(self.font_desc); discl.Centre(wx.HORIZONTAL)

    def on_update_apply_ui(self, event):
        if wx.GetKeyState(wx.WXK_SHIFT):
            event.SetText(LM.get("MENU_RESTORE"))
            self.desc_apply.SetLabel(LM.get("DESC_RESTORE"))
        else:
            event.SetText(LM.get("MENU_APPLY"))
            self.desc_apply.SetLabel(LM.get("DESC_APPLY"))

    def _refresh_pack_label(self):
        dl_path = self.helper.downloads_path
        current = "None"
        try:
            with open(self.config_path, 'r') as f:
                selected = json.load(f).get("selected_pack")
                if selected and os.path.exists(os.path.join(dl_path, selected)):
                    current = selected
                elif os.path.exists(dl_path):
                    folders = [f for f in os.listdir(dl_path) if os.path.isdir(os.path.join(dl_path, f))]
                    if folders: current = folders[0]
        except: pass
        
        self.pack_label.SetLabel(LM.get("LBL_SELECTED_PACK").replace("{pack}", current))
        self.pack_label.Centre(wx.HORIZONTAL)

    def on_apply_changes(self, event):
        if wx.GetKeyState(wx.WXK_SHIFT):
            if wx.MessageBox(LM.get("MSG_RESTORE_CONFIRM"), LM.get("MENU_RESTORE"), wx.YES_NO | wx.ICON_WARNING) == wx.YES:
                self.helper.restore_icons(self); self._refresh_pack_label()
            return
        
        dl_path = self.helper.downloads_path
        has_downloads = False
        if os.path.exists(dl_path):
            folders = [f for f in os.listdir(dl_path) if os.path.isdir(os.path.join(dl_path, f)) and not f.startswith('.')]
            if folders:
                has_downloads = True

        if not has_downloads:
            wx.MessageBox(LM.get("MSG_NO_BRANCHES_DOWNLOADED"), "SkinX Info", wx.OK | wx.ICON_INFORMATION)
            self.on_select_version(None)
            return

        available = self.helper.get_available_patches()
        if not available:
            wx.MessageBox(LM.get("MSG_NO_PATCHES"), "Error", wx.OK | wx.ICON_ERROR); return
        
        dlg = IconSelectorDialog(self, available)
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.GetSelectedItems()
            if selected:
                warn_msg = LM.get("MSG_LP_LAYOUT_WARNING")
                warn_dlg = wx.MessageDialog(self, warn_msg, LM.get("TITLE_WARNING"), wx.OK | wx.CANCEL | wx.ICON_WARNING)
                if warn_dlg.ShowModal() == wx.ID_OK:
                    self.helper.apply_icons(selected, True, self)
        dlg.Destroy()

    def on_select_version(self, event):
        dlg = VersionSelectFrame(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._refresh_pack_label()
        dlg.Destroy()

    def on_open_settings(self, event): SettingsFrame(self).Show()
    def on_dummy(self, event): wx.MessageBox(LM.get("MSG_NOT_IMPLEMENTED"), "Info")

if __name__ == "__main__":
    app = wx.App(); MainFrame(None); app.MainLoop()