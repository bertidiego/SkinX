import json
import os

class LocaleManager:
    def __init__(self, lang_code="it_it"):
        self.base_path = os.path.join(os.path.dirname(__file__), "lang")
        self.en_fallback = {}
        self.translations = {}
        self.current_lang = lang_code

        self._load_fallback()
        self.load_language(lang_code)

    def _load_fallback(self):
        path = os.path.join(self.base_path, "en_us.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.en_fallback = json.load(f)

    def load_language(self, lang_code):
        self.current_lang = lang_code
        path = os.path.join(self.base_path, f"{lang_code}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)

    def get(self, key):

        val = self.translations.get(key)
        if val: return val

        val = self.en_fallback.get(key)
        if val: return val

        return f"MISSING_{key}"

    def get_completion_rate(self, lang_code=None):
        target_lang = self.translations
        if lang_code and lang_code != self.current_lang:
            path = os.path.join(self.base_path, f"{lang_code}.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    target_lang = json.load(f)
        
        if not self.en_fallback: return 0
        
        total_keys = len(self.en_fallback)
        translated_keys = sum(1 for k in self.en_fallback if target_lang.get(k))
        return int((translated_keys / total_keys) * 100)

    def get_available_langs(self):
        return [f.replace(".json", "") for f in os.listdir(self.base_path) if f.endswith(".json")]

LM = LocaleManager()