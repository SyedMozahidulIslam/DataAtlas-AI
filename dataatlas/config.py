"""Environment-backed local application settings."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_home: Path
    host: str = "127.0.0.1"
    port: int = 8000
    max_upload_bytes: int = 10 * 1024 * 1024
    max_csv_rows: int = 100_000
    demo_password: str = "dataatlas-demo"
    openai_api_key: str | None = None
    ai_model: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        home = Path(os.environ.get("DATAATLAS_HOME", Path(__file__).resolve().parent.parent / "var")).expanduser()
        host = os.environ.get("DATAATLAS_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("DATAATLAS_PORT", "8000"))
        except ValueError as exc:
            raise ValueError("DATAATLAS_PORT must be an integer between 1 and 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("DATAATLAS_PORT must be an integer between 1 and 65535.")
        demo_password = os.environ.get("DATAATLAS_DEMO_PASSWORD", "dataatlas-demo")
        if len(demo_password) < 10:
            raise ValueError("DATAATLAS_DEMO_PASSWORD must be at least 10 characters.")
        return cls(data_home=home, host=host, port=port, demo_password=demo_password,
                   openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
                   ai_model=os.environ.get("DATAATLAS_AI_MODEL") or None)
