from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop.services.app_paths import user_data_directory


class SettingsService:
    def __init__(self) -> None:
        settings_file = user_data_directory() / "settings.ini"
        self._settings = QSettings(str(settings_file), QSettings.IniFormat)

    def value(self, key: str, default=None):
        return self._settings.value(key, default)

    def set_value(self, key: str, value) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    @property
    def path(self) -> str:
        return self._settings.fileName()
