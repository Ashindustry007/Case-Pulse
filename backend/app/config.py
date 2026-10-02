"""Settings loaded from .env (shared, frozen). Import `settings` everywhere; never read os.environ directly."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = _get("ANTHROPIC_API_KEY")
    model_main: str = _get("MODEL_MAIN", "claude-opus-5-5")
    model_fast: str = _get("MODEL_FAST", "claude-haiku-4-5")
    clio_client_id: str = _get("CLIO_CLIENT_ID")
    clio_client_secret: str = _get("CLIO_CLIENT_SECRET")
    clio_redirect_uri: str = _get("CLIO_REDIRECT_URI", "http://127.0.0.1:8000/auth/clio/callback")
    clio_base_url: str = _get("CLIO_BASE_URL", "https://app.clio.com").rstrip("/")
    jwt_secret: str = _get("JWT_SECRET", "dev-insecure-secret-change-me-before-any-demo")
    attorney_email: str = _get("ATTORNEY_EMAIL", "attorney@firm.test")
    attorney_password: str = _get("ATTORNEY_PASSWORD", "")
    attorney_name: str = _get("ATTORNEY_NAME", "Firm Attorney")
    firm_name: str = _get("FIRM_NAME", "Your Firm")
    resend_api_key: str = _get("RESEND_API_KEY")
    invite_from_email: str = _get("INVITE_FROM_EMAIL")
    ai_budget_per_matter_usd: float = float(_get("AI_BUDGET_PER_MATTER_USD", "5") or 5)
    embed_model: str = _get("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
    db_path: Path = ROOT / _get("DB_PATH", "data/casepulse.db")
    data_dir: Path = ROOT / _get("DATA_DIR", "data")
    api_base_url: str = _get("API_BASE_URL", "http://localhost:8000").rstrip("/")
    frontend_url: str = _get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


settings = Settings()
