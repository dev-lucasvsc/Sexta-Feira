"""
Sexta-Feira v2.0 - Módulo de Google Calendar
============================================
Consulta eventos do Google Calendar por voz.

Setup (uma vez):
    1. Acesse: https://console.cloud.google.com
    2. Crie um projeto → ative a Google Calendar API
    3. Crie credenciais OAuth2 (tipo: Desktop App)
    4. Baixe o JSON → salve como: data/google_credentials.json
    5. Rode: python -c "from core.calendar_manager import CalendarManager; CalendarManager().authorize()"
    6. Autorize no browser → token salvo em data/google_token.json

Requer:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Comandos de voz:
    "o que tenho hoje"          → eventos de hoje
    "o que tenho amanhã"        → eventos de amanhã
    "próximo evento"            → próximo evento na agenda
    "eventos da semana"         → resumo semanal
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("Calendar")

CREDENTIALS_FILE = "data/google_credentials.json"
TOKEN_FILE       = "data/google_token.json"
SCOPES           = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarManager:
    """
    Consulta eventos do Google Calendar via API OAuth2.
    Token renovado automaticamente após autorização inicial.
    """

    def __init__(self):
        self._service = None
        self._available = self._check_dependencies()
        if self._available:
            self._load_service()

    def _check_dependencies(self) -> bool:
        try:
            import google.auth
            import googleapiclient
            return True
        except ImportError:
            logger.warning("[Calendar] Dependências não instaladas.")
            logger.warning("          Execute: pip install google-auth google-auth-oauthlib "
                           "google-auth-httplib2 google-api-python-client")
            return False

    def _load_service(self):
        """Carrega o serviço da API do Google Calendar."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = None

            if Path(TOKEN_FILE).exists():
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self._save_token(creds)
                else:
                    logger.info("[Calendar] Token não encontrado. Execute authorize().")
                    return

            self._service = build("calendar", "v3", credentials=creds)
            logger.info("[Calendar] Serviço Google Calendar carregado.")

        except Exception as e:
            logger.error(f"[Calendar] Erro ao carregar serviço: {e}")

    def _save_token(self, creds):
        Path("data").mkdir(exist_ok=True)
        Path(TOKEN_FILE).write_text(creds.to_json())

    def authorize(self):
        """Abre o browser para autorização OAuth2."""
        if not self._available:
            logger.error("[Calendar] Instale as dependências primeiro.")
            return

        if not Path(CREDENTIALS_FILE).exists():
            logger.error(f"[Calendar] Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
            logger.error("          Baixe em: console.cloud.google.com → APIs → Credenciais")
            return

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            self._save_token(creds)

            from googleapiclient.discovery import build
            self._service = build("calendar", "v3", credentials=creds)
            logger.info("[Calendar] Autorização concluída.")
        except Exception as e:
            logger.error(f"[Calendar] Erro na autorização: {e}")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def _get_events(self, time_min: datetime, time_max: datetime, max_results: int = 10) -> list[dict]:
        """Busca eventos no intervalo de tempo especificado."""
        if not self._service:
            return []

        try:
            result = self._service.events().list(
                calendarId="primary",
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            return result.get("items", [])
        except Exception as e:
            logger.error(f"[Calendar] Erro ao buscar eventos: {e}")
            return []

    def _format_event(self, event: dict) -> str:
        """Formata um evento para leitura em voz."""
        titulo = event.get("summary", "Sem título")
        start  = event.get("start", {})

        # Evento com hora definida
        if "dateTime" in start:
            dt  = datetime.fromisoformat(start["dateTime"])
            hora = dt.strftime("%H:%M")
            return f"{hora} — {titulo}"

        # Evento de dia inteiro
        return f"Dia todo — {titulo}"

    def get_today(self) -> tuple[bool, str]:
        """Retorna os eventos de hoje."""
        agora = datetime.now().astimezone()
        inicio = agora.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        fim    = agora.replace(hour=23, minute=59, second=59, microsecond=0)

        eventos = self._get_events(inicio, fim)

        if not self._service:
            return False, "Google Calendar não configurado. Execute authorize() para conectar."

        if not eventos:
            return True, "Você não tem eventos hoje."

        linhas  = [self._format_event(e) for e in eventos]
        resumo  = f"{len(eventos)} evento(s) hoje: " + "; ".join(linhas[:5])
        if len(eventos) > 5:
            resumo += f" e mais {len(eventos) - 5}."
        return True, resumo

    def get_tomorrow(self) -> tuple[bool, str]:
        """Retorna os eventos de amanhã."""
        amanha = datetime.now().astimezone() + timedelta(days=1)
        inicio = amanha.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        fim    = amanha.replace(hour=23, minute=59, second=59, microsecond=0)

        eventos = self._get_events(inicio, fim)

        if not self._service:
            return False, "Google Calendar não configurado."

        if not eventos:
            return True, "Você não tem eventos amanhã."

        linhas = [self._format_event(e) for e in eventos]
        resumo = f"{len(eventos)} evento(s) amanhã: " + "; ".join(linhas[:5])
        return True, resumo

    def get_next_event(self) -> tuple[bool, str]:
        """Retorna o próximo evento a partir de agora."""
        agora = datetime.now().astimezone()
        fim   = agora + timedelta(days=7)

        eventos = self._get_events(agora, fim, max_results=1)

        if not self._service:
            return False, "Google Calendar não configurado."

        if not eventos:
            return True, "Nenhum evento nos próximos 7 dias."

        evento = eventos[0]
        titulo = evento.get("summary", "Sem título")
        start  = evento.get("start", {})

        if "dateTime" in start:
            dt    = datetime.fromisoformat(start["dateTime"])
            diff  = dt - agora
            horas = int(diff.total_seconds() // 3600)
            mins  = int((diff.total_seconds() % 3600) // 60)

            if horas == 0:
                quando = f"em {mins} minuto(s)"
            elif horas < 24:
                quando = f"em {horas}h{mins:02d}"
            else:
                quando = f"em {dt.strftime('%d/%m às %H:%M')}"

            return True, f"Próximo evento: {titulo}, {quando}."

        return True, f"Próximo evento: {titulo}."

    def get_week(self) -> tuple[bool, str]:
        """Retorna um resumo dos eventos da semana."""
        agora  = datetime.now().astimezone()
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        fim    = inicio + timedelta(days=7)

        eventos = self._get_events(inicio, fim, max_results=20)

        if not self._service:
            return False, "Google Calendar não configurado."

        if not eventos:
            return True, "Nenhum evento nos próximos 7 dias."

        return True, f"Você tem {len(eventos)} evento(s) nos próximos 7 dias."