import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

import keyring
from platformdirs import user_config_path
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHATTINESS_LEVELS = ("quiet", "normal", "chatty")


class AppSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    # --- model connection -------------------------------------------------
    endpoint: str = ""
    model: str = ""
    system_prompt: str = "你是一只住在桌面上的小宠物，请用自然、简短、亲切的中文回复。"
    request_timeout: int = Field(default=30, ge=1, le=180)

    # --- appearance -------------------------------------------------------
    pet_scale: int = Field(default=100, ge=60, le=180)
    pet_opacity: int = Field(default=100, ge=30, le=100)
    always_on_top: bool = True

    # --- behaviour --------------------------------------------------------
    wander: bool = True
    smart_move: bool = True
    doze: bool = True
    remember_position: bool = True
    click_through: bool = False
    autostart: bool = False
    chattiness: Literal["quiet", "normal", "chatty"] = "normal"

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("接口地址必须以 http:// 或 https:// 开头")
        return value


class PetState(BaseModel):
    """Where the pet was last seen; kept out of settings.json on purpose."""

    x: int | None = None
    y: int | None = None

    def is_placed(self) -> bool:
        return self.x is not None and self.y is not None


class SettingsStore:
    def __init__(self, path: Path | None = None):
        config_dir = Path(user_config_path("shaqiu", appauthor=False))
        self.path = path or config_dir / "settings.json"

    def load(self) -> AppSettings:
        if self.path.exists():
            try:
                return AppSettings.model_validate_json(self.path.read_text(encoding="utf-8"))
            except (OSError, ValidationError, ValueError):
                LOGGER.exception("Unable to load settings from %s", self.path)
        return self._load_legacy_settings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)

    def _load_legacy_settings(self) -> AppSettings:
        legacy_path = PROJECT_ROOT / "pet_config.json"
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
            allowed = {"endpoint", "model", "system_prompt", "request_timeout"}
            legacy_settings = {key: value for key, value in data.items() if key in allowed}
            settings = AppSettings.model_validate(legacy_settings)
            if settings.endpoint or settings.model:
                self.save(settings)
            return settings
        except (OSError, json.JSONDecodeError, ValidationError):
            return AppSettings()


class PetStateStore:
    """Remembers where the pet was left, so it comes back to the same spot."""

    def __init__(self, path: Path | None = None):
        config_dir = Path(user_config_path("shaqiu", appauthor=False))
        self.path = path or config_dir / "pet_state.json"

    def load(self) -> PetState:
        if self.path.exists():
            try:
                return PetState.model_validate_json(self.path.read_text(encoding="utf-8"))
            except (OSError, ValidationError, ValueError):
                LOGGER.exception("Unable to load pet position from %s", self.path)
        return PetState()

    def save(self, state: PetState) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary_path, self.path)
        except OSError:
            LOGGER.exception("Unable to store pet position at %s", self.path)


class CredentialStore:
    SERVICE_NAME = "shaqiu"
    ACCOUNT_NAME = "chat-api"

    def get_api_key(self) -> str:
        try:
            return (
                os.environ.get("DESKTOP_PET_API_KEY")
                or keyring.get_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                or ""
            )
        except keyring.errors.KeyringError:
            LOGGER.exception("Unable to read the API key from the system keyring")
            return os.environ.get("DESKTOP_PET_API_KEY", "")

    def set_api_key(self, api_key: str) -> None:
        try:
            if api_key.strip():
                keyring.set_password(self.SERVICE_NAME, self.ACCOUNT_NAME, api_key.strip())
            else:
                try:
                    keyring.delete_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                except keyring.errors.PasswordDeleteError:
                    pass
        except keyring.errors.KeyringError:
            LOGGER.exception("Unable to store the API key in the system keyring")


class TrainingRecord(BaseModel):
    """One completed training attempt, persisted across app restarts."""

    kind: Literal["schulte", "reaction", "vision"]
    duration_ms: int = Field(ge=0)
    success: bool = True
    played_at: str = Field(
        default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds")
    )
    note: str = ""


class TrainingHistory(BaseModel):
    records: list[TrainingRecord] = Field(default_factory=list)


class TrainingHistoryStore:
    """Small JSON history store for the three attention-training windows."""

    def __init__(self, path: Path | None = None):
        config_dir = Path(user_config_path("shaqiu", appauthor=False))
        self.path = path or config_dir / "training_history.json"

    def load(self) -> TrainingHistory:
        if not self.path.exists():
            return TrainingHistory()
        try:
            return TrainingHistory.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError):
            LOGGER.exception("Unable to load training history from %s", self.path)
            return TrainingHistory()

    def save(self, history: TrainingHistory) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(history.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary_path, self.path)
        except OSError:
            LOGGER.exception("Unable to store training history at %s", self.path)

    def add(self, record: TrainingRecord) -> None:
        history = self.load()
        history.records.append(record)
        self.save(history)

    def records(
        self, kind: Literal["schulte", "reaction", "vision"], limit: int | None = None
    ) -> list[TrainingRecord]:
        matching = [record for record in reversed(self.load().records) if record.kind == kind]
        return matching if limit is None else matching[:limit]

    def fastest_ms(
        self, kind: Literal["schulte", "reaction", "vision"], *, successes_only: bool = True
    ) -> int | None:
        durations = [
            record.duration_ms
            for record in self.records(kind)
            if record.success or not successes_only
        ]
        return min(durations) if durations else None


def read_style_examples() -> str:
    style_path = PROJECT_ROOT / "style_examples.txt"
    try:
        return style_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


__all__ = [
    "CHATTINESS_LEVELS",
    "AppSettings",
    "CredentialStore",
    "PetState",
    "PetStateStore",
    "SettingsStore",
    "TrainingHistory",
    "TrainingHistoryStore",
    "TrainingRecord",
    "read_style_examples",
]
