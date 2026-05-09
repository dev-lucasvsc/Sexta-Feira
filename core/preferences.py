"""Preferencias persistentes simples da Sexta-Feira."""

import json
import logging
from pathlib import Path

logger = logging.getLogger("Preferences")


class PreferencesStore:
    def __init__(self, path: str = "data/preferences.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = {}
        self.load()

    def load(self):
        if not self.path.exists():
            self._data = {}
            return
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[Preferences] Nao consegui ler preferencias: {e}")
            self._data = {}

    def save(self):
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def set(self, key: str, value: str):
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if not key or not value:
            return False
        self._data[key] = value
        self.save()
        return True

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def all(self) -> dict[str, str]:
        return dict(self._data)

    def summary_for_prompt(self) -> str:
        if not self._data:
            return "Preferencias do usuario: nenhuma registrada."
        items = "; ".join(f"{k}={v}" for k, v in sorted(self._data.items()))
        return f"Preferencias do usuario: {items}."
