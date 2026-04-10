"""
Sexta-Feira v2.0 - Módulo de Memória de Sessão
===============================================
Mantém o histórico da conversa atual em memória para
injetar como contexto no LLM, permitindo continuidade
entre comandos ("explica melhor", "e sobre o segundo ponto?").

O histórico é mantido em memória RAM — reseta ao reiniciar.
Para persistência entre sessões, use o módulo de histórico SQLite (futuro).
"""

import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger("SessionMemory")


class SessionMemory:
    """
    Gerencia o histórico de conversa da sessão atual.

    Mantém um buffer circular dos últimos N turnos para
    evitar que o contexto cresça além do limite do LLM.
    """

    def __init__(self, max_turns: int = 10):
        """
        Args:
            max_turns: Número máximo de turnos mantidos em memória.
                       Cada turno = 1 pergunta + 1 resposta.
                       Padrão: 10 turnos (~20 mensagens).
        """
        self.max_turns = max_turns
        self._history: deque = deque(maxlen=max_turns * 2)  # user + assistant
        self._session_start = datetime.now()
        logger.info(f"SessionMemory iniciada | max_turns: {max_turns}")

    def add_user(self, texto: str):
        """Registra a fala do usuário."""
        self._history.append({"role": "user", "content": texto, "ts": datetime.now()})

    def add_assistant(self, texto: str):
        """Registra a resposta da Sexta-Feira."""
        self._history.append({"role": "assistant", "content": texto, "ts": datetime.now()})

    def get_history_for_llm(self) -> list[dict]:
        """
        Retorna o histórico no formato aceito pelo LLM (Claude/Ollama).
        Exclui o campo 'ts' que é interno.

        Returns:
            Lista de dicts com 'role' e 'content'.
        """
        return [{"role": h["role"], "content": h["content"]} for h in self._history]

    def get_summary(self) -> str:
        """
        Retorna um resumo textual do histórico para injetar no system prompt
        de modelos que não suportam multi-turn nativo.
        """
        if not self._history:
            return ""

        lines = []
        for h in list(self._history)[-6:]:  # últimos 3 turnos
            role = "Usuário" if h["role"] == "user" else "Sexta-Feira"
            lines.append(f"{role}: {h['content']}")

        return "Histórico recente da conversa:\n" + "\n".join(lines)

    def clear(self):
        """Limpa o histórico da sessão."""
        self._history.clear()
        logger.info("[SessionMemory] Histórico limpo.")

    @property
    def turn_count(self) -> int:
        return len(self._history) // 2

    @property
    def is_empty(self) -> bool:
        return len(self._history) == 0