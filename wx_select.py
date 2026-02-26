import wx
import requests
import threading
import os
import zipfile
import shutil
import json
from io import BytesIO
from locales import LM

class VersionItem(wx.Panel):
    def __init__(self, parent, name, thumb_url, source_name, is_installed=False, has_update=False, download_url=None, sha="", is_error=False, error_detail=""):
        super(VersionItem, self).__init__(parent)
        self.is_error = is_error
        self.name = name
        self.download_url = download_url
        self.is_installed = is_installed
        self.has_update = has_update
        self.branch_sha = sha
        
        self.SetBackgroundColour(wx.Colour(255, 255, 255) if not is_error else wx.Colour(255, 235, 235))
        
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.pic = wx.StaticBitmap(self, size=(48, 48))
        self.pic.SetBackgroundColour(wx.Colour(240, 240, 240))
        
        status_text = ""
        if is_installed:
            status_text = f" ({LM.get('LBL_INSTALLED')})"
            if has_update:
                status_text = " [UPDATE AVAILABLE]"
        
        self.label = wx.StaticText(self, label=f"{name}{status_text}")
        self.label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=".AppleSystemUIFont"))
        
        if has_update:
            self.label.SetForegroundColour(wx.Colour(200, 100, 0))
        elif is_installed:
            self.label.SetForegroundColour(wx.Colour(0, 120, 0))
            
        sub_text = f"Source: {source_name}" if not is_error else f"Reason: {error_detail}"
        self.src_label = wx.StaticText(self, label=sub_text)
        self.src_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=".AppleSystemUIFont"))
        
        text_sizer.Add(self.label, 0, wx.TOP, 2)
        text_sizer.Add(self.src_label, 0, wx.TOP, 2)
        
        main_sizer.Add(self.pic, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        main_sizer.Add(text_sizer, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        
        self.SetSizer(main_sizer)
        
        self.Bind(wx.EVT_LEFT_DOWN, self._on_ui_click)
        for child in self.GetChildren():
            child.Bind(wx.EVT_LEFT_DOWN, self._on_ui_click)
        
        if not is_error:
            threading.Thread(target=self._load_image, args=(thumb_url,), daemon=True).start()

    def _load_image(self, url):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                img = wx.Image(BytesIO(resp.content)).Rescale(48, 48, wx.IMAGE_QUALITY_HIGH)
                wx.CallAfter(self.pic.SetBitmap, wx.Bitmap(img))
        except: pass

    def _on_ui_click(self, event):
        self.GetParent().GetParent().GetParent().select_item(self)
        event.Skip()

class VersionSelectFrame(wx.Dialog):
    def __init__(self, parent):
        super(VersionSelectFrame, self).__init__(parent, title=LM.get("TITLE_SELECT_VERSION"), size=(550, 400),
                                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.dl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
        self.items = []
        self.selected_item = None
        self.installed_shas = self._load_installed_shas()
        self.sources = self._get_sources_from_config()

        self.SetBackgroundColour(wx.Colour(245, 245, 247))
        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(panel, label=LM.get("LBL_AVAILABLE_BRANCHES"))
        header.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName=".AppleSystemUIFont"))
        
        self.scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL | wx.BORDER_SUNKEN)
        self.scroll.SetScrollRate(0, 10)
        self.scroll.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.scroll_sizer)

        self.btn_action = wx.Button(panel, label=LM.get("BTN_DOWNLOAD"), size=(250, 40))
        self.btn_action.Disable()
        self.btn_action.Bind(wx.EVT_BUTTON, self.on_action_click)

        self.main_sizer.Add(header, 0, wx.ALL | wx.CENTER, 20)
        self.main_sizer.Add(self.scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        self.main_sizer.Add(self.btn_action, 0, wx.ALL | wx.CENTER, 20)
        
        panel.SetSizer(self.main_sizer)
        self.Centre()

        for url in self.sources:
            threading.Thread(target=self._fetch_branches, args=(url,), daemon=True).start()

    def _load_installed_shas(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f).get("installed_shas", {})
            except: pass
        return {}

    def _get_sources_from_config(self):
        default = ["https://api.github.com/repos/bertidiego/SkinX-icons/branches"]
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f).get("sources", default)
            except: pass
        return default

    def _fetch_branches(self, api_url):
        parts = api_url.split('/')
        source_display = f"{parts[4]}/{parts[5]}" if len(parts) > 5 else api_url
        try:
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            data = response.json()

            for b in data:
                name = b.get('name')
                if not name or name in ['main', 'master']: continue
                
                sha = b.get('commit', {}).get('sha', "")
                is_installed = os.path.exists(os.path.join(self.dl_dir, name))

                has_update = False
                if is_installed and name in self.installed_shas:
                    if self.installed_shas[name] != sha:
                        has_update = True

                thumb = f"https://raw.githubusercontent.com/{source_display}/{name}/ver.jpg"
                dl_url = api_url.replace("api.github.com/repos", "github.com").replace("/branches", "") + f"/archive/refs/heads/{name}.zip"
                
                wx.CallAfter(self._add_item, name, thumb, source_display, is_installed, has_update, dl_url, sha)
        except Exception as e:
            wx.CallAfter(self._report_error, source_display, str(e))

    def _add_item(self, name, thumb, source, is_installed, has_update, dl_url, sha):
        item = VersionItem(self.scroll, name, thumb, source, is_installed, has_update, dl_url, sha)
        self.scroll_sizer.Add(item, 0, wx.EXPAND | wx.BOTTOM, 1)
        self.items.append(item)
        self.scroll.Layout()
        self.scroll.FitInside()

    def select_item(self, target_item):
        self.selected_item = target_item
        for item in self.items:
            bg = wx.Colour(245, 245, 247) if item.is_installed else wx.Colour(255, 255, 255)
            item.SetBackgroundColour(bg)
        
        target_item.SetBackgroundColour(wx.Colour(210, 230, 255))

        if target_item.has_update:
            self.btn_action.SetLabel("Update Package")
            self.btn_action.Enable()
        elif target_item.is_installed:
            self.btn_action.SetLabel("Select Package")
            self.btn_action.Enable()
        else:
            self.btn_action.SetLabel(LM.get("BTN_DOWNLOAD"))
            self.btn_action.Enable()
            
        self.scroll.Refresh()

    def on_action_click(self, event):
        if not self.selected_item: return

        if self.selected_item.is_installed and not self.selected_item.has_update:
            self._finalize_selection(self.selected_item.name)
            return

        self.on_download()

    def on_download(self):
        if not os.path.exists(self.dl_dir): os.makedirs(self.dl_dir)
        status_msg = LM.get("STATUS_DOWNLOADING").replace("{branch}", self.selected_item.name)
        self.progress_dialog = wx.ProgressDialog(LM.get("TITLE"), status_msg, 100, self, wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)
        threading.Thread(target=self._download_thread, args=(self.selected_item.download_url, self.dl_dir, self.selected_item.name, self.selected_item.branch_sha), daemon=True).start()

    def _download_thread(self, url, dl_dir, branch, sha):
        try:
            response = requests.get(url, stream=True, timeout=15)
            zip_buffer = BytesIO()
            downloaded = 0
            total_size = int(response.headers.get('content-length', 0))
            for chunk in response.iter_content(4096):
                zip_buffer.write(chunk)
                downloaded += len(chunk)
                if total_size > 0: wx.CallAfter(self.progress_dialog.Update, int((downloaded/total_size)*100))

            wx.CallAfter(self.progress_dialog.Update, 95, LM.get("STATUS_EXTRACTING"))
            with zipfile.ZipFile(zip_buffer) as z:
                z.extractall(dl_dir)
                root = z.namelist()[0].split('/')[0]
                old_path = os.path.join(dl_dir, root)
                new_path = os.path.join(dl_dir, branch)

                if os.path.exists(new_path): shutil.rmtree(new_path)
                
                # Se ci sono altri pack scaricati, li spostiamo in una sottocartella o gestiamo la "selezione"
                # Per ora, SkinX legge il primo pacchetto trovato, quindi rinominiamo quello scelto
                # Ma per supportare la multi-selezione, dobbiamo rinominare gli altri o segnare il preferito
                os.rename(old_path, new_path)
            
            self._save_sha_to_config(branch, sha)
            wx.CallAfter(self._on_finished, branch)
        except Exception as e: wx.CallAfter(self._on_error, str(e))

    def _save_sha_to_config(self, branch, sha):
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f: config = json.load(f)
            if "installed_shas" not in config: config["installed_shas"] = {}
            config["installed_shas"][branch] = sha

            config["selected_pack"] = branch
            with open(self.config_path, 'w') as f: json.dump(config, f, indent=4)
        except: pass

    def _finalize_selection(self, branch):

        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f: config = json.load(f)
            config["selected_pack"] = branch
            with open(self.config_path, 'w') as f: json.dump(config, f, indent=4)
        except: pass
        self.EndModal(wx.ID_OK)

    def _on_finished(self, branch):
        if self.progress_dialog: self.progress_dialog.Destroy()
        self.EndModal(wx.ID_OK)

    def _on_error(self, msg):
        if self.progress_dialog: self.progress_dialog.Destroy()
        wx.MessageBox(f"Error: {msg}", "Error", wx.OK | wx.ICON_ERROR)

    def _report_error(self, source, reason):
        wx.CallAfter(wx.MessageBox, f"Source {source} error: {reason}", "Error")