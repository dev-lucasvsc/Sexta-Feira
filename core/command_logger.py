"""
Sexta-Feira v2.0 - Módulo de Log de Comandos
=============================================
Registra todos os comandos recebidos e respostas dadas
em um arquivo de log rotativo por data.

Útil para:
- Debug de reconhecimento de voz
- Análise de padrões de uso
- Histórico de comandos executados
"""

import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("CommandLogger")


class CommandLogger:
    """
    Registra comandos e respostas em arquivo .txt diário.

    Formato do log:
        [HH:MM:SS] USER: <comando transcrito>
        [HH:MM:SS] SEXTA: <resposta falada>
        [HH:MM:SS] AÇÃO: <tipo da ação executada>
        ---
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._session_start = datetime.now()
        self._log_path = self._get_log_path()
        self._write_header()
        logger.info(f"[CommandLogger] Log em: {self._log_path}")

    def _get_log_path(self) -> Path:
        data = self._session_start.strftime("%Y-%m-%d")
        return self.log_dir / f"sexta_{data}.txt"

    def _write_header(self):
        """Escreve cabeçalho de sessão no arquivo."""
        hora = self._session_start.strftime("%Y-%m-%d %H:%M:%S")
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"SESSÃO INICIADA: {hora}\n")
            f.write(f"{'='*60}\n")

    def _write(self, linha: str):
        """Escreve uma linha no arquivo de log."""
        hora = datetime.now().strftime("%H:%M:%S")
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{hora}] {linha}\n")
        except Exception as e:
            logger.warning(f"[CommandLogger] Erro ao escrever log: {e}")

    def log_command(self, comando: str):
        """Registra o comando do usuário."""
        self._write(f"USER : {comando}")

    def log_response(self, resposta: str):
        """Registra a resposta da Sexta-Feira."""
        self._write(f"SEXTA: {resposta[:120]}")

    def log_action(self, tipo: str, parametro: str = ""):
        """Registra uma ação executada."""
        detalhe = f" → {parametro}" if parametro else ""
        self._write(f"AÇÃO : {tipo}{detalhe}")

    def log_separator(self):
        """Separador visual entre interações."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write("-" * 40 + "\n")
        except Exception:
            pass

    def log_session_end(self):
        """Registra encerramento da sessão."""
        fim = datetime.now()
        duracao = fim - self._session_start
        minutos = int(duracao.total_seconds() // 60)
        segundos = int(duracao.total_seconds() % 60)
        self._write(f"SESSÃO ENCERRADA — duração: {minutos}m {segundos}s")
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"{'='*60}\n")
        except Exception:
            pass

    def get_today_log(self) -> str:
        """Retorna o conteúdo do log de hoje."""
        try:
            return self._log_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "Nenhum log encontrado para hoje."

    @property
    def log_path(self) -> str:
        return str(self._log_path)