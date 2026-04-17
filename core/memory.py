"""
Sexta-Feira v2.0 - Módulo de Memória (Obsidian / Segundo Cérebro)
=============================================================
Lê arquivos .md do vault do Obsidian e realiza buscas por palavras-chave
para enriquecer o contexto enviado ao LLM.

Hot-reload automático: detecta novas notas e alterações via watchdog
sem precisar reiniciar a Sexta-Feira.
Instale com: pip install watchdog
"""

import os
import re
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger("ObsidianMemory")


@dataclass
class NoteResult:
    """Representa uma nota encontrada durante a busca."""
    filepath: str
    filename: str
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    excerpt: str = ""


class ObsidianMemory:
    """
    Interface de leitura, busca e hot-reload do vault local do Obsidian.

    Hot-reload: usa watchdog para monitorar o diretório e recarregar
    automaticamente quando notas são criadas, modificadas ou deletadas.
    """

    NOTE_EXTENSION    = ".md"
    MAX_CONTEXT_CHARS = 3000
    EXCERPT_WINDOW    = 150

    def __init__(self, vault_path: str, hot_reload: bool = True):
        """
        Args:
            vault_path:  Caminho absoluto para o vault Obsidian.
            hot_reload:  Ativa monitoramento automático de alterações.
        """
        self.vault_path  = Path(vault_path)
        self.hot_reload  = hot_reload
        self._note_cache: dict[str, str] = {}
        self._lock       = threading.Lock()
        self._observer   = None

        if not self.vault_path.exists():
            logger.warning(f"Vault não encontrado: {vault_path}. Criando...")
            self.vault_path.mkdir(parents=True, exist_ok=True)

        self._load_vault()

        if hot_reload:
            self._start_watcher()

    def _start_watcher(self):
        """Inicia o watchdog para monitorar o vault em background."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            memory = self

            class VaultHandler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(".md"):
                        logger.info(f"[Obsidian] Nova nota: {Path(event.src_path).name}")
                        memory._reload_single(event.src_path)

                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(".md"):
                        logger.debug(f"[Obsidian] Nota modificada: {Path(event.src_path).name}")
                        memory._reload_single(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory and event.src_path.endswith(".md"):
                        logger.info(f"[Obsidian] Nota removida: {Path(event.src_path).name}")
                        with memory._lock:
                            memory._note_cache.pop(event.src_path, None)

            self._observer = Observer()
            self._observer.schedule(VaultHandler(), str(self.vault_path), recursive=True)
            self._observer.daemon = True
            self._observer.start()
            logger.info("[Obsidian] Hot-reload ativo — monitorando vault.")

        except ImportError:
            logger.warning("[Obsidian] watchdog não instalado. Hot-reload desativado.")
            logger.warning("          Execute: pip install watchdog")

    def _reload_single(self, filepath: str):
        """Recarrega uma única nota no cache."""
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
            with self._lock:
                self._note_cache[filepath] = content
        except Exception as e:
            logger.warning(f"[Obsidian] Erro ao recarregar '{filepath}': {e}")

    def _load_vault(self):
        """Percorre recursivamente o vault e carrega todos os .md em memória."""
        count = 0
        new_cache = {}

        for filepath in self.vault_path.rglob(f"*{self.NOTE_EXTENSION}"):
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                new_cache[str(filepath)] = content
                count += 1
            except Exception as e:
                logger.warning(f"Erro ao ler '{filepath}': {e}")

        with self._lock:
            self._note_cache = new_cache

        logger.info(f"Vault carregado: {count} notas de '{self.vault_path}'")

    def reload(self):
        """Força recarga do vault (útil se as notas mudaram desde o início)."""
        logger.info("Recarregando vault do Obsidian...")
        self._load_vault()

    def _tokenize(self, text: str) -> list[str]:
        """Extrai palavras significativas (>3 chars) de um texto."""
        words = re.findall(r'\b\w{4,}\b', text.lower())
        # Remove stopwords básicas em português
        stopwords = {"para", "como", "isso", "esse", "esta", "este", "uma", "mais",
                     "pela", "pelo", "com", "que", "não", "sim", "pode", "fazer"}
        return [w for w in words if w not in stopwords]

    def _extract_excerpt(self, content: str, keyword: str) -> str:
        """Extrai um trecho do conteúdo ao redor da primeira ocorrência da keyword."""
        idx = content.lower().find(keyword.lower())
        if idx == -1:
            return ""
        start = max(0, idx - self.EXCERPT_WINDOW)
        end = min(len(content), idx + len(keyword) + self.EXCERPT_WINDOW)
        return "..." + content[start:end].strip() + "..."

    def search(self, query: str, top_k: int = 3) -> str:
        """Busca notas relevantes com base nas palavras-chave da query."""
        with self._lock:
            cache_snapshot = dict(self._note_cache)

        if not cache_snapshot:
            return ""

        keywords = self._tokenize(query)
        if not keywords:
            return ""

        results: list[NoteResult] = []

        for filepath, content in cache_snapshot.items():
            content_lower = content.lower()
            matched = [kw for kw in keywords if kw in content_lower]
            if matched:
                excerpt = self._extract_excerpt(content, matched[0])
                results.append(NoteResult(
                    filepath=filepath,
                    filename=Path(filepath).stem,
                    score=len(matched),
                    matched_keywords=matched,
                    excerpt=excerpt
                ))

        if not results:
            return ""

        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:top_k]
        logger.info(f"Notas encontradas: {[r.filename for r in top_results]}")

        context_parts = []
        total_chars = 0

        for result in top_results:
            section = (
                f"### Nota: {result.filename}\n"
                f"Keywords: {', '.join(result.matched_keywords)}\n"
                f"Trecho: {result.excerpt}\n"
            )
            if total_chars + len(section) > self.MAX_CONTEXT_CHARS:
                break
            context_parts.append(section)
            total_chars += len(section)

        return "\n".join(context_parts)

    def get_note_content(self, filename: str) -> str | None:
        """
        Retorna o conteúdo completo de uma nota pelo nome do arquivo (sem extensão).
        
        Args:
            filename: Nome da nota sem extensão (ex: 'Projeto Alpha').
        
        Returns:
            Conteúdo da nota ou None se não encontrada.
        """
        for filepath, content in self._note_cache.items():
            if Path(filepath).stem.lower() == filename.lower():
                return content
        return None

    @property
    def note_count(self) -> int:
        """Número de notas atualmente indexadas."""
        return len(self._note_cache)