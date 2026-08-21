"""Settings loaded from the environment. Nothing here is a business threshold —
those live in the `settings` DB table so they can be changed without a deploy."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/pramaan"
    storage_root: Path = Path("./storage")

    jwt_secret: str = "dev-only-change-me-32-bytes-minimum-secret"
    jwt_alg: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 14

    max_upload_mb: int = 100

    # Browser origins allowed to call this API. In dev the frontend proxies through
    # Next's rewrite so this is unused; on a split deploy the two are on different
    # hosts and this is the only thing letting the browser through.
    cors_origins: str = "http://localhost:3000"

    # The cloud LLM. Read by api/app/llm/provider.py and by nothing else (invariant #5).
    # `GOOGLE_API_KEY` is accepted as an alias because that is the name Google's own SDK and
    # docs use, and an operator who exports it expecting it to work should not be met with
    # "no API key set".
    gemini_api_key: str = ""
    google_api_key: str = ""
    # Pinned, not an alias. `gemini-flash-latest` would move under us between a rehearsal and
    # the demo, and the response cache is keyed by model name — a silent model change
    # invalidates every cached answer at the worst possible moment.
    llm_model: str = "gemini-3.6-flash"
    # Gemini 3.x reasons before answering, and those thinking tokens are billed and count
    # against `max_output_tokens`. This job is deterministic field extraction at temperature
    # 0, not a reasoning problem, so LOW is the right setting: measured ~70 thinking tokens
    # and 1.8s per call against ~5.0s at the default. Set to "" for a model that does not
    # accept the parameter at all (the 2.5 family rejects it).
    llm_thinking_level: str = "LOW"
    # A hung call must not wedge the worker. Without this the SDK waits indefinitely, and one
    # unlucky request stalls the job — and therefore the document — with no way to tell.
    llm_timeout_seconds: int = 90
    demo_mode: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        """`database_url` with a driver the project actually installs.

        Hosted Postgres hands out `postgres://` or `postgresql://`, and SQLAlchemy reads
        a bare `postgresql://` as psycopg2 — which is not in requirements.txt, so the
        engine dies at import with ModuleNotFoundError before a single log line. We ship
        psycopg 3, so name it. A URL that already specifies a driver is left alone.
        """
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def allowed_origins(self) -> list[str]:
        """Comma-separated in the environment; a list is what Starlette wants."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def llm_api_key(self) -> str:
        """One name for the key, whichever variable it arrived in."""
        return self.gemini_api_key or self.google_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
