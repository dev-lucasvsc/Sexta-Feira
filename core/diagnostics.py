"""Diagnostico leve das integracoes da Sexta-Feira."""

from pathlib import Path

import requests

from config import Config


def build_diagnostic(orchestrator) -> str:
    checks = []

    try:
        r = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        status = "online" if r.ok else "com erro"
        model_ok = Config.OLLAMA_MODEL in models
        checks.append(f"Ollama {status}; modelo {Config.OLLAMA_MODEL}: {'ok' if model_ok else 'nao encontrado'}")
    except Exception:
        checks.append("Ollama offline")

    token_ok = Path("data/spotify_token/.cache").exists()
    creds_ok = Config.SPOTIFY_CLIENT_ID not in ("", "SEU_CLIENT_ID_AQUI") and Config.SPOTIFY_CLIENT_SECRET not in ("", "SEU_CLIENT_SECRET_AQUI")
    checks.append(f"Spotify credenciais: {'ok' if creds_ok else 'faltando'}; token: {'ok' if token_ok else 'faltando'}")

    checks.append(f"Voz: {'silenciosa' if getattr(orchestrator, 'silent_mode', False) else 'ativa'}")
    checks.append(f"Memoria de sessao: {orchestrator.session_memory.turn_count} turno(s)")
    checks.append(f"Preferencias: {len(orchestrator.preferences.all())} registrada(s)")

    return ". ".join(checks) + "."
