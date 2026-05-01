"""
Sexta-Feira v2.0 - Módulo de Controle do Spotify
=================================================
Controla o Spotify via Spotipy (biblioteca oficial).

Setup (uma vez):
    1. pip install spotipy
    2. Acesse: https://developer.spotify.com/dashboard
    3. Crie um app → copie Client ID e Client Secret
    4. Em "Redirect URIs" adicione: http://127.0.0.1:8888/callback
       (use 127.0.0.1, não localhost)
    5. Preencha no config.py: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    6. Rode UMA VEZ para autorizar:
       python setup_spotify.py
       (abre o browser, você autoriza, token salvo em data/spotify_token/)

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

import logging
from pathlib import Path

logger = logging.getLogger("Spotify")

REDIRECT_URI  = "http://127.0.0.1:8888/callback"
SCOPES        = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
TOKEN_CACHE   = "data/spotify_token/.cache"


class SpotifyController:
    """
    Controla o Spotify via Spotipy.
    Token é salvo em disco e renovado automaticamente.
    """

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id     = client_id
        self.client_secret = client_secret
        self._sp           = None
        self._mock_mode    = not (client_id and client_secret
                                  and client_id != "SEU_CLIENT_ID"
                                  and client_secret != "SEU_CLIENT_SECRET")

        if self._mock_mode:
            logger.warning("[Spotify] Credenciais não configuradas. Modo MOCK ativo.")
            return

        Path("data/spotify_token").mkdir(parents=True, exist_ok=True)
        self._init_spotipy()

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

    def _init_spotipy(self):
        """Inicializa o cliente Spotipy com cache de token."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=REDIRECT_URI,
                scope=SCOPES,
                cache_path=TOKEN_CACHE,
                open_browser=False,  # controla abertura do browser manualmente
            )

            # Se já tem token em cache, usa direto sem pedir autorização
            token_info = auth_manager.get_cached_token()
            if token_info:
                self._sp = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("[Spotify] Token carregado do cache. Pronto.")
            else:
                logger.warning("[Spotify] Token não encontrado. Execute: python setup_spotify.py")
                self._sp = None

        except ImportError:
            logger.error("[Spotify] spotipy não instalado. Execute: pip install spotipy")
            self._sp = None
        except Exception as e:
            logger.error(f"[Spotify] Erro ao inicializar: {e}")
            self._sp = None

    def _ready(self) -> bool:
        """Verifica se o cliente está pronto para uso."""
        if self._mock_mode:
            return False
        if self._sp is None:
            logger.error("[Spotify] Sem autenticação. Execute: python setup_spotify.py")
            return False
        return True

    def authorize(self):
        """
        Fluxo de autorização manual (usado pelo setup_spotify.py).
        Abre o browser, aguarda o callback e salva o token.
        """
        if self._mock_mode:
            logger.error("[Spotify] Configure as credenciais no config.py primeiro.")
            return False

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            Path("data/spotify_token").mkdir(parents=True, exist_ok=True)

            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=REDIRECT_URI,
                scope=SCOPES,
                cache_path=TOKEN_CACHE,
                open_browser=True,
            )

            # Isso abre o browser e aguarda a URL de callback
            print("\n[Spotify] Abrindo browser para autorização...")
            print("[Spotify] Após autorizar, COLE a URL completa de redirecionamento aqui:")
            print(f"[Spotify] (começa com {REDIRECT_URI}?code=...)\n")

            auth_url = auth_manager.get_authorize_url()
            import webbrowser
            webbrowser.open(auth_url)

            response_url = input("URL de redirecionamento: ").strip()
            code = auth_manager.parse_response_code(response_url)
            auth_manager.get_access_token(code, as_dict=False)

            self._sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("[Spotify] Autorização concluída. Token salvo em data/spotify_token/")
            print("\n[Spotify] ✓ Autorizado com sucesso! Pode fechar o browser.")
            return True

        except Exception as e:
            logger.error(f"[Spotify] Erro na autorização: {e}")
            print(f"\n[Spotify] ✗ Erro: {e}")
            return False

    # ------------------------------------------------------------------
    # Controles de playback
    # ------------------------------------------------------------------

    def play(self) -> tuple[bool, str]:
        """Resume a reprodução."""
        if self._mock_mode:
            return True, "Reprodução iniciada."
        if not self._ready():
            return False, "Spotify não autorizado. Execute setup_spotify.py"
        try:
            self._sp.start_playback()
            return True, "Reprodução iniciada."
        except Exception as e:
            logger.error(f"[Spotify] play: {e}")
            return False, "Não foi possível iniciar a reprodução. Verifique se o Spotify está aberto."

    def pause(self) -> tuple[bool, str]:
        """Pausa a reprodução."""
        if self._mock_mode:
            return True, "Música pausada."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            self._sp.pause_playback()
            return True, "Música pausada."
        except Exception as e:
            logger.error(f"[Spotify] pause: {e}")
            return False, "Não foi possível pausar."

    def next_track(self) -> tuple[bool, str]:
        """Avança para a próxima faixa."""
        if self._mock_mode:
            return True, "Próxima música."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            self._sp.next_track()
            return True, "Próxima música."
        except Exception as e:
            logger.error(f"[Spotify] next: {e}")
            return False, "Não foi possível avançar."

    def previous_track(self) -> tuple[bool, str]:
        """Volta para a faixa anterior."""
        if self._mock_mode:
            return True, "Música anterior."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            self._sp.previous_track()
            return True, "Música anterior."
        except Exception as e:
            logger.error(f"[Spotify] previous: {e}")
            return False, "Não foi possível voltar."

    def set_volume(self, volume: int) -> tuple[bool, str]:
        """Ajusta o volume do Spotify (0-100)."""
        if self._mock_mode:
            return True, f"Volume ajustado para {volume} por cento."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            volume = max(0, min(100, volume))
            self._sp.volume(volume)
            return True, f"Volume do Spotify ajustado para {volume} por cento."
        except Exception as e:
            logger.error(f"[Spotify] volume: {e}")
            return False, "Não foi possível ajustar o volume."

    def toggle_shuffle(self) -> tuple[bool, str]:
        """Liga/desliga modo aleatório."""
        if self._mock_mode:
            return True, "Modo aleatório alternado."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            state = self._sp.current_playback()
            current = state.get("shuffle_state", False) if state else False
            self._sp.shuffle(not current)
            status = "ativado" if not current else "desativado"
            return True, f"Modo aleatório {status}."
        except Exception as e:
            logger.error(f"[Spotify] shuffle: {e}")
            return False, "Não foi possível alterar o modo aleatório."

    def get_current_track(self) -> dict | None:
        """Retorna informações da faixa atual."""
        if not self._ready():
            return None
        try:
            return self._sp.current_user_playing_track()
        except Exception as e:
            logger.error(f"[Spotify] current_track: {e}")
            return None

    def now_playing(self) -> tuple[bool, str]:
        """Retorna o nome da música e artista atual."""
        if self._mock_mode:
            return False, "Nenhuma música tocando no momento."
        if not self._ready():
            return False, "Spotify não autorizado."
        try:
            data = self._sp.current_user_playing_track()
            if not data or not data.get("item"):
                return False, "Nenhuma música tocando no momento."
            item    = data["item"]
            musica  = item["name"]
            artista = ", ".join(a["name"] for a in item["artists"])
            return True, f"Tocando agora: {musica}, de {artista}."
        except Exception as e:
            logger.error(f"[Spotify] now_playing: {e}")
            return False, "Não consegui identificar a música atual."

    def search_and_play(self, query: str) -> tuple[bool, str]:
        """Busca e toca uma música ou artista."""
        if self._mock_mode:
            return True, f"Tocando {query} no Spotify."
        if not self._ready():
            return False, "Spotify não autorizado. Execute setup_spotify.py"
        try:
            results = self._sp.search(q=query, type="track", limit=1)
            tracks  = results.get("tracks", {}).get("items", [])
            if not tracks:
                return False, f"Não encontrei '{query}' no Spotify."

            track   = tracks[0]
            uri     = track["uri"]
            nome    = track["name"]
            artista = track["artists"][0]["name"]

            self._sp.start_playback(uris=[uri])
            return True, f"Tocando {nome}, de {artista}."
        except Exception as e:
            logger.error(f"[Spotify] search_and_play: {e}")
            return False, f"Não consegui tocar '{query}'. Verifique se o Spotify está aberto."