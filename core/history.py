"""
Sexta-Feira v2.0 - Módulo de Histórico Persistente (SQLite)
============================================================
Salva todas as conversas em banco SQLite local.
Diferente da SessionMemory (RAM, reseta ao reiniciar),
este módulo persiste entre sessões — a Sexta-Feira
pode consultar conversas de dias anteriores.

Banco criado em: data/history.db
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("History")


class ConversationHistory:
    """
    Armazena e recupera conversas do banco SQLite local.

    Tabelas:
        sessions  — cada execução do programa é uma sessão
        messages  — cada par pergunta/resposta dentro de uma sessão
    """

    DB_PATH = "data/history.db"

    def __init__(self):
        Path("data").mkdir(exist_ok=True)
        self._conn = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        self._session_id = self._start_session()
        logger.info(f"[History] Banco inicializado | sessão #{self._session_id}")

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at   TEXT,
                turns      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                intent     TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);

            CREATE INDEX IF NOT EXISTS idx_messages_created
                ON messages(created_at);
        """)
        self._conn.commit()

    def _start_session(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (datetime.now().isoformat(),)
        )
        self._conn.commit()
        return cur.lastrowid

    def add(self, role: str, content: str, intent: str = ""):
        """
        Salva uma mensagem no banco.

        Args:
            role:    "user" ou "assistant"
            content: Texto da mensagem
            intent:  Intenção detectada (opcional, para análise)
        """
        self._conn.execute(
            """INSERT INTO messages (session_id, role, content, intent, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (self._session_id, role, content, intent, datetime.now().isoformat())
        )
        self._conn.execute(
            "UPDATE sessions SET turns = turns + 1 WHERE id = ?",
            (self._session_id,)
        )
        self._conn.commit()

    def end_session(self):
        """Marca o encerramento da sessão atual."""
        self._conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), self._session_id)
        )
        self._conn.commit()
        logger.info(f"[History] Sessão #{self._session_id} encerrada.")

    def get_last_n(self, n: int = 20) -> list[dict]:
        """Retorna as últimas N mensagens da sessão atual."""
        rows = self._conn.execute(
            """SELECT role, content, created_at FROM messages
               WHERE session_id = ?
               ORDER BY id DESC LIMIT ?""",
            (self._session_id, n)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Busca mensagens em todo o histórico por palavra-chave.

        Args:
            query: Texto a buscar (case-insensitive)
            limit: Máximo de resultados

        Returns:
            Lista de mensagens encontradas com data
        """
        rows = self._conn.execute(
            """SELECT role, content, created_at FROM messages
               WHERE content LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_stats(self) -> dict:
        """Retorna estatísticas da sessão atual."""
        row = self._conn.execute(
            "SELECT turns, started_at FROM sessions WHERE id = ?",
            (self._session_id,)
        ).fetchone()
        total = self._conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
        return {
            "session_id":   self._session_id,
            "turns":        row["turns"] if row else 0,
            "started_at":   row["started_at"] if row else "",
            "total_messages": total,
        }

    def get_summary_for_llm(self, n_turns: int = 5) -> str:
        """
        Retorna resumo das últimas N conversas para injetar no LLM.
        Inclui conversas de sessões anteriores — memória real entre dias.
        """
        rows = self._conn.execute(
            """SELECT role, content FROM messages
               ORDER BY id DESC LIMIT ?""",
            (n_turns * 2,)
        ).fetchall()

        if not rows:
            return ""

        lines = []
        for r in reversed(rows):
            role = "Usuário" if r["role"] == "user" else "Sexta-Feira"
            lines.append(f"{role}: {r['content'][:120]}")

        return "Histórico de conversas anteriores:\n" + "\n".join(lines)

    def __del__(self):
        try:
            self._conn.close()
        except Exception:
            pass