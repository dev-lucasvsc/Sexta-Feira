"""
JARVIS v2.0 - Módulo de Memória (Obsidian / Segundo Cérebro)
=============================================================
Lê arquivos .md do vault do Obsidian e realiza buscas por palavras-chave
para enriquecer o contexto enviado ao LLM.
"""

import os
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger("ObsidianMemory")


@dataclass
class NoteResult:
    """Representa uma nota encontrada durante a busca."""
    filepath: str
    filename: str
    score: int                    # Número de keywords encontradas (relevância)
    matched_keywords: list[str]   = field(default_factory=list)
    excerpt: str                  = ""  # Trecho relevante do conteúdo


class ObsidianMemory:
    """
    Interface de leitura e busca no vault local do Obsidian.
    
    Carrega as notas em cache ao inicializar e permite buscas
    rápidas por palavras-chave sem I/O repetitivo.
    """

    # Extensão padrão das notas Obsidian
    NOTE_EXTENSION = ".md"

    # Tamanho máximo do contexto retornado ao LLM (caracteres)
    MAX_CONTEXT_CHARS = 3000

    # Tamanho do excerpt (trecho ao redor da keyword encontrada)
    EXCERPT_WINDOW = 150

    def __init__(self, vault_path: str):
        """
        Args:
            vault_path: Caminho absoluto para o diretório raiz do vault Obsidian.
        """
        self.vault_path = Path(vault_path)
        self._note_cache: dict[str, str] = {}  # filepath -> conteúdo bruto

        if not self.vault_path.exists():
            logger.warning(f"Vault path não encontrado: {vault_path}. Criando diretório de exemplo.")
            self.vault_path.mkdir(parents=True, exist_ok=True)

        self._load_vault()

    def _load_vault(self):
        """
        Percorre recursivamente o vault e carrega todos os .md em memória.
        Re-chame este método se as notas forem modificadas externamente.
        """
        self._note_cache.clear()
        count = 0

        for filepath in self.vault_path.rglob(f"*{self.NOTE_EXTENSION}"):
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                self._note_cache[str(filepath)] = content
                count += 1
            except Exception as e:
                logger.warning(f"Erro ao ler '{filepath}': {e}")

        logger.info(f"Vault carregado: {count} notas indexadas de '{self.vault_path}'")

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
        """
        Busca notas relevantes no vault com base nas palavras-chave da query.
        
        Args:
            query: Transcrição do comando do usuário.
            top_k: Número máximo de notas a incluir no contexto.
        
        Returns:
            String formatada com o conteúdo relevante das notas encontradas.
            String vazia se nenhuma nota relevante for encontrada.
        """
        if not self._note_cache:
            logger.warning("Cache do vault vazio. Nenhum contexto disponível.")
            return ""

        keywords = self._tokenize(query)
        if not keywords:
            return ""

        results: list[NoteResult] = []

        for filepath, content in self._note_cache.items():
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
            logger.info(f"Nenhuma nota encontrada para keywords: {keywords}")
            return ""

        # Ordena por relevância (score decrescente)
        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:top_k]

        logger.info(f"Notas encontradas: {[r.filename for r in top_results]}")

        # Monta o contexto formatado para o LLM
        context_parts = []
        total_chars = 0

        for result in top_results:
            section = (
                f"### Nota: {result.filename}\n"
                f"Keywords encontradas: {', '.join(result.matched_keywords)}\n"
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
