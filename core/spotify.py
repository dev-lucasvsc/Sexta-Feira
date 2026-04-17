"""
Sexta-Feira v2.0 - Módulo de Controle do Spotify
=================================================
Controla o Spotify via Spotify Web API usando OAuth2.

Setup (uma vez):
    1. Acesse: https://developer.spotify.com/dashboard
    2. Crie um app → copie Client ID e Client Secret
    3. Em "Redirect URIs" adicione: http://localhost:8888/callback
    4. Preencha no config.py: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    5. Rode: python -c "from core.spotify import SpotifyController; SpotifyController().authorize()"
    6. Siga o link no terminal para autorizar — token salvo automaticamente

Comandos de voz suportados:
    "tocar música"          → resume/play
    "pausar"                → pause
    "próxima"               → next track
    "anterior"              → previous track
    "tocar [nome]"          → busca e toca a música/artista
    "volume 70"             → ajusta volume do Spotify (0-100)
    "o que está tocando"    → informa a música atual
    "modo aleatório"        → shuffle on/off
"""

import os
import json
import logging
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger("Spotify")

TOKEN_FILE = "data/spotify_token.json"
REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"


class SpotifyController:
    """
    Controla o Spotify via Web API com autenticação OAuth2.
    Token é salvo localmente e renovado automaticamente.
    """

    AUTH_URL    = "https://accounts.spotify.com/authorize"
    TOKEN_URL   = "https://accounts.spotify.com/api/token"
    API_BASE    = "https://api.spotify.com/v1"

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id     = client_id
        self.client_secret = client_secret
        self._token_data: dict = {}
        self._mock_mode = not (client_id and client_secret)

        if self._mock_mode:
            logger.warning("[Spotify] Client ID/Secret não configurados. Modo MOCK ativo.")
        else:
            Path("data").mkdir(exist_ok=True)
            self._load_token()

    # ------------------------------------------------------------------
    # Autorização OAuth2
    # ------------------------------------------------------------------

    def authorize(self):
        """Abre o browser para autorização OAuth2 e salva o token."""
        if self._mock_mode:
            logger.error("[Spotify] Configure SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET primeiro.")
            return

        params = {
            "client_id":     self.client_id,
            "response_type": "code",
            "redirect_uri":  REDIRECT_URI,
            "scope":         SCOPES,
        }
        url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"[Spotify] Abrindo browser para autorização...")
        webbrowser.open(url)
        self._wait_for_callback()

    def _wait_for_callback(self):
        """Sobe servidor local para capturar o código de autorização."""
        controller = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = parse_qs(urlparse(self.path).query)
                code = qs.get("code", [None])[0]
                if code:
                    controller._exchange_code(code)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Autorizado! Pode fechar esta aba.")
                else:
                    self.send_response(400)
                    self.end_headers()

            def log_message(self, *args):
                pass  # silencia logs do servidor

        server = HTTPServer(("localhost", 8888), Handler)
        logger.info("[Spotify] Aguardando callback em http://localhost:8888/callback ...")
        server.handle_request()

    def _exchange_code(self, code: str):
        """Troca o código de autorização pelo access token."""
        import requests as req
        import base64

        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        r = req.post(self.TOKEN_URL, data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
        }, headers={"Authorization": f"Basic {credentials}"})

        if r.ok:
            self._token_data = r.json()
            self._token_data["expires_at"] = (
                __import__("time").time() + self._token_data.get("expires_in", 3600)
            )
            self._save_token()
            logger.info("[Spotify] Token obtido e salvo com sucesso.")
        else:
            logger.error(f"[Spotify] Erro ao obter token: {r.text}")

    def _refresh_token(self):
        """Renova o access token usando o refresh token."""
        import requests as req
        import base64

        refresh = self._token_data.get("refresh_token")
        if not refresh:
            logger.error("[Spotify] Sem refresh token. Execute authorize() novamente.")
            return

        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        r = req.post(self.TOKEN_URL, data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh,
        }, headers={"Authorization": f"Basic {credentials}"})

        if r.ok:
            data = r.json()
            self._token_data["access_token"] = data["access_token"]
            self._token_data["expires_at"]   = __import__("time").time() + data.get("expires_in", 3600)
            if "refresh_token" in data:
                self._token_data["refresh_token"] = data["refresh_token"]
            self._save_token()
        else:
            logger.error(f"[Spotify] Erro ao renovar token: {r.text}")

    def _get_token(self) -> str | None:
        """Retorna o access token válido, renovando se necessário."""
        if not self._token_data:
            return None
        if __import__("time").time() >= self._token_data.get("expires_at", 0) - 60:
            self._refresh_token()
        return self._token_data.get("access_token")

    def _save_token(self):
        with open(TOKEN_FILE, "w") as f:
            json.dump(self._token_data, f, indent=2)

    def _load_token(self):
        try:
            with open(TOKEN_FILE) as f:
                self._token_data = json.load(f)
            logger.info("[Spotify] Token carregado do disco.")
        except FileNotFoundError:
            logger.info("[Spotify] Token não encontrado. Execute authorize() para autorizar.")

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def _api(self, method: str, endpoint: str, **kwargs) -> dict | None:
        """Faz uma chamada à Spotify Web API."""
        if self._mock_mode:
            logger.info(f"[Spotify MOCK] {method.upper()} {endpoint}")
            return {"mock": True}

        import requests as req
        token = self._get_token()
        if not token:
            logger.error("[Spotify] Sem token válido. Execute authorize().")
            return None

        url = f"{self.API_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        r = getattr(req, method)(url, headers=headers, **kwargs)

        if r.status_code == 204:
            return {}
        if r.ok:
            try:
                return r.json()
            except Exception:
                return {}
        logger.error(f"[Spotify] Erro {r.status_code}: {r.text[:200]}")
        return None

    # ------------------------------------------------------------------
    # Controles de playback
    # ------------------------------------------------------------------

    def play(self) -> tuple[bool, str]:
        """Resume a reprodução."""
        r = self._api("put", "/me/player/play")
        if r is not None:
            return True, "Reprodução iniciada."
        return False, "Não foi possível iniciar a reprodução."

    def pause(self) -> tuple[bool, str]:
        """Pausa a reprodução."""
        r = self._api("put", "/me/player/pause")
        if r is not None:
            return True, "Música pausada."
        return False, "Não foi possível pausar."

    def next_track(self) -> tuple[bool, str]:
        """Avança para a próxima faixa."""
        r = self._api("post", "/me/player/next")
        if r is not None:
            return True, "Próxima música."
        return False, "Não foi possível avançar."

    def previous_track(self) -> tuple[bool, str]:
        """Volta para a faixa anterior."""
        r = self._api("post", "/me/player/previous")
        if r is not None:
            return True, "Música anterior."
        return False, "Não foi possível voltar."

    def set_volume(self, volume: int) -> tuple[bool, str]:
        """Ajusta o volume do Spotify (0-100)."""
        volume = max(0, min(100, volume))
        r = self._api("put", "/me/player/volume", params={"volume_percent": volume})
        if r is not None:
            return True, f"Volume do Spotify ajustado para {volume} por cento."
        return False, "Não foi possível ajustar o volume."

    def toggle_shuffle(self) -> tuple[bool, str]:
        """Liga/desliga modo aleatório."""
        state = self.get_current_track()
        current_shuffle = state.get("shuffle_state", False) if state else False
        r = self._api("put", "/me/player/shuffle", params={"state": not current_shuffle})
        if r is not None:
            status = "ativado" if not current_shuffle else "desativado"
            return True, f"Modo aleatório {status}."
        return False, "Não foi possível alterar o modo aleatório."

    def get_current_track(self) -> dict | None:
        """Retorna informações da faixa atual."""
        return self._api("get", "/me/player/currently-playing")

    def now_playing(self) -> tuple[bool, str]:
        """Retorna o nome da música e artista atual."""
        data = self.get_current_track()
        if not data or self._mock_mode:
            return False, "Nenhuma música tocando no momento."
        try:
            item    = data["item"]
            musica  = item["name"]
            artista = ", ".join(a["name"] for a in item["artists"])
            return True, f"Tocando agora: {musica}, de {artista}."
        except (KeyError, TypeError):
            return False, "Não consegui identificar a música atual."

    def search_and_play(self, query: str) -> tuple[bool, str]:
        """Busca e toca uma música ou artista."""
        if self._mock_mode:
            logger.info(f"[Spotify MOCK] search_and_play: '{query}'")
            return True, f"Tocando {query} no Spotify."

        r = self._api("get", "/search", params={"q": query, "type": "track", "limit": 1})
        if not r:
            return False, "Não encontrei essa música no Spotify."

        try:
            track = r["tracks"]["items"][0]
            uri   = track["uri"]
            nome  = track["name"]
            artista = track["artists"][0]["name"]
            self._api("put", "/me/player/play", json={"uris": [uri]})
            return True, f"Tocando {nome}, de {artista}."
        except (KeyError, IndexError):
            return False, f"Não encontrei '{query}' no Spotify."