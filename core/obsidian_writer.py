"""
Sexta-Feira v2.0 - Módulo de Escrita no Obsidian
=================================================
Cria e atualiza notas no vault do Obsidian via comandos de voz.
Complementa o módulo de leitura (memory.py) com capacidade de escrita.

Operações:
    - Criar nota nova com título e conteúdo
    - Adicionar texto ao fim de uma nota existente (append)
    - Criar entrada de diário do dia (Daily Note)
    - Criar nota de tarefa rápida
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("ObsidianWriter")


class ObsidianWriter:
    """
    Escreve e atualiza arquivos .md no vault do Obsidian.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        if not self.vault_path.exists():
            logger.warning(f"[ObsidianWriter] Vault não encontrado: {vault_path}")

    # ------------------------------------------------------------------
    # Criar nota
    # ------------------------------------------------------------------

    def create_note(self, titulo: str, conteudo: str = "", pasta: str = "") -> tuple[bool, str]:
        """
        Cria uma nova nota .md no vault.

        Args:
            titulo:   Título da nota (nome do arquivo).
            conteudo: Conteúdo inicial da nota.
            pasta:    Subpasta dentro do vault (opcional).

        Returns:
            (sucesso, mensagem)
        """
        # Sanitiza o título para nome de arquivo
        titulo_limpo = self._sanitize_filename(titulo)
        if not titulo_limpo:
            return False, "Título inválido para a nota."

        # Define o diretório
        if pasta:
            dir_path = self.vault_path / pasta
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            dir_path = self.vault_path

        filepath = dir_path / f"{titulo_limpo}.md"

        # Evita sobrescrever nota existente
        if filepath.exists():
            return False, f"Já existe uma nota com o título '{titulo}'. Use append para adicionar conteúdo."

        # Monta o conteúdo com frontmatter
        agora     = datetime.now()
        data_str  = agora.strftime("%Y-%m-%d")
        hora_str  = agora.strftime("%H:%M")

        conteudo_final = f"""---
criado: {data_str} {hora_str}
tags: [voz, sexta-feira]
---

# {titulo}

{conteudo if conteudo else ''}
"""

        try:
            filepath.write_text(conteudo_final, encoding="utf-8")
            logger.info(f"[ObsidianWriter] Nota criada: {filepath.name}")
            return True, f"Nota '{titulo}' criada no Obsidian."
        except Exception as e:
            logger.error(f"[ObsidianWriter] Erro ao criar nota: {e}")
            return False, f"Erro ao criar a nota: {e}"

    # ------------------------------------------------------------------
    # Adicionar ao fim de uma nota
    # ------------------------------------------------------------------

    def append_to_note(self, titulo: str, conteudo: str) -> tuple[bool, str]:
        """
        Adiciona texto ao fim de uma nota existente.
        Se a nota não existir, cria uma nova.

        Args:
            titulo:   Título / nome da nota (sem .md).
            conteudo: Texto a adicionar.
        """
        filepath = self._find_note(titulo)

        if not filepath:
            # Nota não existe — cria nova
            return self.create_note(titulo, conteudo)

        hora_str = datetime.now().strftime("%H:%M")
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"\n**[{hora_str}]** {conteudo}\n")
            logger.info(f"[ObsidianWriter] Append em: {filepath.name}")
            return True, f"Conteúdo adicionado à nota '{titulo}'."
        except Exception as e:
            return False, f"Erro ao editar a nota: {e}"

    # ------------------------------------------------------------------
    # Daily Note (nota de diário do dia)
    # ------------------------------------------------------------------

    def append_to_daily_note(self, conteudo: str) -> tuple[bool, str]:
        """
        Adiciona uma entrada à nota diária (formato YYYY-MM-DD.md).
        Cria a nota do dia se não existir.

        Args:
            conteudo: Texto da entrada.
        """
        agora    = datetime.now()
        data_str = agora.strftime("%Y-%m-%d")
        hora_str = agora.strftime("%H:%M")

        # Procura pasta de daily notes
        daily_folder = self._find_daily_folder()
        dir_path     = self.vault_path / daily_folder if daily_folder else self.vault_path
        dir_path.mkdir(parents=True, exist_ok=True)

        filepath = dir_path / f"{data_str}.md"

        if not filepath.exists():
            # Cria a daily note do dia
            header = f"""---
data: {data_str}
tags: [daily, diário]
---

# {agora.strftime("%d/%m/%Y")} — Diário do dia

"""
            filepath.write_text(header, encoding="utf-8")

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"\n- **{hora_str}**: {conteudo}\n")
            logger.info(f"[ObsidianWriter] Daily note atualizada: {filepath.name}")
            return True, f"Anotei no diário de hoje: {conteudo[:60]}."
        except Exception as e:
            return False, f"Erro ao escrever no diário: {e}"

    # ------------------------------------------------------------------
    # Nota de tarefa rápida
    # ------------------------------------------------------------------

    def create_task(self, tarefa: str, pasta: str = "Tarefas") -> tuple[bool, str]:
        """
        Cria uma nota de tarefa rápida com checkbox Obsidian.

        Args:
            tarefa: Descrição da tarefa.
            pasta:  Subpasta onde salvar (padrão: "Tarefas").
        """
        agora     = datetime.now()
        titulo    = f"Tarefa — {agora.strftime('%Y-%m-%d %H%M')}"
        conteudo  = f"- [ ] {tarefa}"
        return self.create_note(titulo, conteudo, pasta=pasta)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_note(self, titulo: str) -> Path | None:
        """Busca uma nota pelo título (case-insensitive, sem extensão)."""
        titulo_lower = titulo.lower()
        for filepath in self.vault_path.rglob("*.md"):
            if filepath.stem.lower() == titulo_lower:
                return filepath
        return None

    def _find_daily_folder(self) -> str:
        """
        Detecta automaticamente a pasta de daily notes.
        Procura por pastas comuns: Daily, Diário, Journal, etc.
        """
        candidates = ["Daily", "Diário", "Diario", "Journal", "Daily Notes", "Notas Diárias"]
        for c in candidates:
            if (self.vault_path / c).is_dir():
                return c
        return ""

    def _sanitize_filename(self, nome: str) -> str:
        """Remove caracteres inválidos para nome de arquivo no Windows."""
        invalid = r'\/:*?"<>|'
        for char in invalid:
            nome = nome.replace(char, "")
        return nome.strip()[:100]  # máximo 100 chars