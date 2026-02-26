import wx
import json
import os
import shutil
import threading
import requests
import sys
from io import BytesIO
from locales import LM
from helper import PatcherHelper

class LanguageItem(wx.Panel):
    def __init__(self, parent, lang_code, is_selected=False):
        super().__init__(parent)
        self.lang_code = lang_code
        self.is_selected = is_selected
        
        bg_color = wx.Colour(230, 240, 255) if is_selected else wx.Colour(255, 255, 255)
        self.SetBackgroundColour(bg_color)
        
        grid = wx.FlexGridSizer(1, 4, 0, 0)
        grid.AddGrowableCol(1)

        flag_map = {"it_it": "it", "en_us": "us", "fr_fr": "fr", "es_es": "es", "de_de": "de"}
        iso_code = flag_map.get(lang_code.lower(), "un")
        
        self.bmp = wx.StaticBitmap(self, size=(24, 18))
        
        display_name = lang_code.replace("_", " ").upper()
        self.label = wx.StaticText(self, label=display_name, size=(150, -1))
        font_style = wx.FONTWEIGHT_BOLD if is_selected else wx.FONTWEIGHT_NORMAL
        self.label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, font_style, faceName=".AppleSystemUIFont"))

        progress_val = LM.get_completion_rate(lang_code)
        self.gauge = wx.Gauge(self, range=100, size=(120, 12), style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.gauge.SetValue(progress_val)
        
        self.percent_label = wx.StaticText(self, label=f"{progress_val}%", size=(40, -1))
        self.percent_label.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        grid.Add(self.bmp, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 12)
        grid.Add(self.label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 20)
        grid.Add(self.gauge, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 10)
        grid.Add(self.percent_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 15)
        
        self.SetSizer(grid)
        for child in self.GetChildren():
            child.Bind(wx.EVT_LEFT_DOWN, self._on_click)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_click)

        flag_url = f"https://flagcdn.com/w40/{iso_code}.png"
        threading.Thread(target=self._load_flag, args=(flag_url,), daemon=True).start()

    def _load_flag(self, url):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                img = wx.Image(BytesIO(resp.content)).Rescale(24, 18, wx.IMAGE_QUALITY_HIGH)
                wx.CallAfter(self.bmp.SetBitmap, wx.Bitmap(img))
        except: pass

    def _on_click(self, event):
        self.GetParent().GetParent().GetParent().on_lang_selected(self.lang_code)

class SettingsFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title=LM.get("MENU_PREF"), size=(550, 720),
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        
        self.helper = PatcherHelper()
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.default_source = "https://api.github.com/repos/oxideve/SkinX-icons/branches"
        self.original_lang = LM.current_lang 
        
        self.SetBackgroundColour(wx.Colour(245, 245, 247))
        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.lang_sizer = wx.BoxSizer(wx.VERTICAL)

        # LINGUA
        lang_header = wx.StaticText(panel, label=LM.get("LBL_LANGUAGE"))
        lang_header.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lang_scroll = wx.ScrolledWindow(panel, size=(-1, 180), style=wx.VSCROLL | wx.BORDER_SUNKEN)
        self.lang_scroll.SetScrollRate(0, 10)
        self.lang_scroll.SetBackgroundColour(wx.Colour(255, 255, 255))
        self._refresh_lang_list()

        # UTILS
        utils_header = wx.StaticText(panel, label=LM.get("LBL_UTILS"))
        utils_header.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.btn_clear = wx.Button(panel, label=LM.get("BTN_CLEAR_CACHE"))
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        
        self.btn_refresh_lp = wx.Button(panel, label="Refresh Launchpad Layout")
        self.btn_refresh_lp.Bind(wx.EVT_BUTTON, self.on_refresh_launchpad)
        
        self.btn_revert_all = wx.Button(panel, label=LM.get("BTN_REVERT_ALL"))
        self.btn_revert_all.Bind(wx.EVT_BUTTON, self.on_revert_all)

        # FOOTER
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancel = wx.Button(panel, label=LM.get("BTN_CANCEL"))
        self.btn_save = wx.Button(panel, label=LM.get("BTN_SAVE_CLOSE"))
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save_close)
        bottom_sizer.Add(self.btn_cancel, 0, wx.RIGHT, 10)
        bottom_sizer.AddStretchSpacer(1)
        bottom_sizer.Add(self.btn_save, 0, wx.LEFT, 10)

        self.main_sizer.Add(lang_header, 0, wx.ALL, 15)
        self.main_sizer.Add(self.lang_scroll, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        self.main_sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 15)
        self.main_sizer.Add(utils_header, 0, wx.LEFT | wx.RIGHT, 15)
        self.main_sizer.Add(self.btn_clear, 0, wx.ALL, 10)
        self.main_sizer.Add(self.btn_refresh_lp, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.main_sizer.Add(self.btn_revert_all, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.main_sizer.AddStretchSpacer(1)
        self.main_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.ALL, 20)

        panel.SetSizer(self.main_sizer)
        self.Centre()

    def on_refresh_launchpad(self, event):
        warn_msg = LM.get("MSG_LP_LAYOUT_WARNING")
        dlg = wx.MessageDialog(self, warn_msg, LM.get("TITLE_WARNING"), wx.OK | wx.CANCEL | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_OK:
            self.helper._refresh_dock()
            wx.MessageBox("Launchpad refreshed!", "SkinX")
        dlg.Destroy()

    def on_clear(self, event):
        """Pulisce la cartella downloads e resetta gli SHA nel config"""
        if wx.MessageBox(LM.get("MSG_CONFIRM_CLEAR_CACHE"), "SkinX", wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            # 1. Elimina cartella fisica
            if os.path.exists(self.helper.downloads_path):
                shutil.rmtree(self.helper.downloads_path)
                os.makedirs(self.helper.downloads_path)
            
            # 2. Resetta SHA e Selezione nel config.json
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                    
                    config["installed_shas"] = {}
                    config["selected_pack"] = ""
                    
                    with open(self.config_path, 'w') as f:
                        json.dump(config, f, indent=4)
                except: pass
            
            wx.MessageBox(LM.get("MSG_CACHE_CLEARED"), "SkinX")

    def _refresh_lang_list(self):
        self.lang_sizer.Clear(True)
        available = sorted(LM.get_available_langs())
        for code in available:
            item = LanguageItem(self.lang_scroll, code, (code == LM.current_lang))
            self.lang_sizer.Add(item, 0, wx.EXPAND | wx.BOTTOM, 1)
        self.lang_scroll.SetSizer(self.lang_sizer)
        self.lang_scroll.Layout()

    def on_lang_selected(self, lang_code):
        LM.load_language(lang_code)
        self._refresh_lang_list()

    def on_save_close(self, event):
        config_data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f: config_data = json.load(f)
        
        config_data["language"] = LM.current_lang
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)

        if LM.current_lang != self.original_lang:
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            self.Close()

    def on_cancel(self, event):
        LM.load_language(self.original_lang)
        self.Close()

    def on_revert_all(self, event):
        if wx.MessageBox(LM.get("MSG_CONFIRM_REVERT_ALL"), "Revert", wx.YES_NO) == wx.ID_YES:
            LM.load_language("it_it")
            self.on_save_close(None)