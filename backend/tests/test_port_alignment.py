import re
from pathlib import Path

import pytest

from app.core.config import settings


def test_vite_proxy_and_backend_port_alignment() -> None:
    """Ensures that the Vite development proxy target port in frontend/vite.config.ts
    matches the FastAPI backend listening port in settings.PORT.
    Fails loudly with an explicit error if they diverge.
    """
    repo_root = Path(__file__).resolve().parents[2]
    vite_config_path = repo_root / "frontend" / "vite.config.ts"

    assert (
        vite_config_path.is_file()
    ), f"vite.config.ts not found at: {vite_config_path}"

    content = vite_config_path.read_text(encoding="utf-8")

    # Match target pattern such as:
    # target: process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000"
    # or target: "http://localhost:8000"
    pattern = (
        r"target:\s*(?:process\.env\.[A-Za-z0-9_]+\s*\|\|\s*)?"
        r'["\']https?://(?:localhost|127\.0\.0\.1):(\d+)["\']'
    )
    match = re.search(pattern, content)

    if not match:
        pytest.fail(
            f"Proxy port not found in {vite_config_path}! "
            "Could not parse Vite proxy target."
        )

    proxy_port = int(match.group(1))
    backend_port = settings.PORT

    assert proxy_port == backend_port, (
        f"Proxy port mismatch! Vite proxy targets port {proxy_port}, "
        f"but backend is configured for port {backend_port}."
    )
