"""
Sexta-Feira v2.0 - Módulo de Gerenciamento de Arquivos e Pastas
================================================================
Permite à Sexta-Feira organizar, mover, renomear, listar e
criar arquivos e pastas via comandos de voz ou instruções do LLM.

Operações suportadas:
- Listar conteúdo de pastas
- Criar pastas
- Mover arquivos/pastas
- Renomear arquivos/pastas
- Deletar arquivos/pastas (com confirmação)
- Organizar pasta por tipo de arquivo (ex: Downloads)
- Buscar arquivos por nome ou extensão
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("FileManager")

# Mapeamento de extensões → subpastas para organização automática
EXTENSION_MAP = {
    # Imagens
    ".jpg": "Imagens", ".jpeg": "Imagens", ".png": "Imagens",
    ".gif": "Imagens", ".bmp": "Imagens", ".webp": "Imagens",
    ".svg": "Imagens", ".ico": "Imagens", ".heic": "Imagens",

    # Documentos
    ".pdf":  "Documentos", ".doc":  "Documentos", ".docx": "Documentos",
    ".xls":  "Documentos", ".xlsx": "Documentos", ".ppt":  "Documentos",
    ".pptx": "Documentos", ".txt":  "Documentos", ".rtf":  "Documentos",
    ".odt":  "Documentos", ".csv":  "Documentos",

    # Vídeos
    ".mp4": "Vídeos", ".mkv": "Vídeos", ".avi": "Vídeos",
    ".mov": "Vídeos", ".wmv": "Vídeos", ".flv": "Vídeos",
    ".webm": "Vídeos",

    # Áudio
    ".mp3": "Músicas", ".wav": "Músicas", ".flac": "Músicas",
    ".aac": "Músicas", ".ogg": "Músicas", ".m4a": "Músicas",

    # Compactados
    ".zip": "Compactados", ".rar": "Compactados", ".7z": "Compactados",
    ".tar": "Compactados", ".gz": "Compactados",

    # Código
    ".py":   "Código", ".js": "Código", ".ts":   "Código",
    ".html": "Código", ".css": "Código", ".java": "Código",
    ".cpp":  "Código", ".c":  "Código", ".json": "Código",
    ".xml":  "Código", ".sql": "Código", ".sh":   "Código",

    # Executáveis / instaladores
    ".exe": "Instaladores", ".msi": "Instaladores",
    ".dmg": "Instaladores", ".apk": "Instaladores",
}


class FileManager:
    """
    Gerencia operações de arquivos e pastas no sistema local.
    Todos os métodos retornam (sucesso: bool, mensagem: str).
    """

    def __init__(self):
        self._lixeira: list[dict] = []  # histórico de deleções para desfazer

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------

    def list_folder(self, path: str, max_items: int = 20) -> tuple[bool, str]:
        """
        Lista o conteúdo de uma pasta.

        Returns:
            (True, resumo em texto) ou (False, mensagem de erro)
        """
        p = Path(os.path.expanduser(path))
        if not p.exists():
            return False, f"Pasta não encontrada: {path}"
        if not p.is_dir():
            return False, f"'{path}' não é uma pasta."

        try:
            items = list(p.iterdir())
            pastas = sorted([i for i in items if i.is_dir()], key=lambda x: x.name)
            arquivos = sorted([i for i in items if i.is_file()], key=lambda x: x.name)

            total = len(pastas) + len(arquivos)
            lines = [f"Pasta: {p.name} — {total} item(s)"]

            if pastas:
                lines.append(f"{len(pastas)} pasta(s): {', '.join(f.name for f in pastas[:10])}")
            if arquivos:
                sample = arquivos[:max_items]
                lines.append(f"{len(arquivos)} arquivo(s): {', '.join(f.name for f in sample)}")
                if len(arquivos) > max_items:
                    lines.append(f"... e mais {len(arquivos) - max_items} arquivos.")

            mensagem = " | ".join(lines)
            logger.info(f"[FileManager] Listado: {path}")
            return True, mensagem

        except PermissionError:
            return False, f"Sem permissão para acessar '{path}'."

    # ------------------------------------------------------------------
    # Criar
    # ------------------------------------------------------------------

    def create_folder(self, path: str) -> tuple[bool, str]:
        """Cria uma pasta (incluindo subpastas intermediárias)."""
        p = Path(os.path.expanduser(path))
        try:
            p.mkdir(parents=True, exist_ok=True)
            logger.info(f"[FileManager] Pasta criada: {p}")
            return True, f"Pasta '{p.name}' criada em '{p.parent}'."
        except Exception as e:
            return False, f"Erro ao criar pasta: {e}"

    # ------------------------------------------------------------------
    # Mover
    # ------------------------------------------------------------------

    def move(self, origem: str, destino: str) -> tuple[bool, str]:
        """
        Move um arquivo ou pasta para outro local.

        Args:
            origem:  Caminho de origem (arquivo ou pasta).
            destino: Caminho de destino (pasta de destino ou novo nome).
        """
        o = Path(os.path.expanduser(origem))
        d = Path(os.path.expanduser(destino))

        if not o.exists():
            return False, f"Origem não encontrada: {origem}"

        try:
            shutil.move(str(o), str(d))
            logger.info(f"[FileManager] Movido: {o} → {d}")
            return True, f"'{o.name}' movido para '{d}'."
        except Exception as e:
            return False, f"Erro ao mover: {e}"

    # ------------------------------------------------------------------
    # Renomear
    # ------------------------------------------------------------------

    def rename(self, path: str, novo_nome: str) -> tuple[bool, str]:
        """Renomeia um arquivo ou pasta."""
        p = Path(os.path.expanduser(path))
        if not p.exists():
            return False, f"Arquivo/pasta não encontrado: {path}"

        novo = p.parent / novo_nome
        try:
            p.rename(novo)
            logger.info(f"[FileManager] Renomeado: {p.name} → {novo_nome}")
            return True, f"'{p.name}' renomeado para '{novo_nome}'."
        except Exception as e:
            return False, f"Erro ao renomear: {e}"

    # ------------------------------------------------------------------
    # Deletar (com backup na lixeira interna)
    # ------------------------------------------------------------------

    def delete(self, path: str, confirmar: bool = False) -> tuple[bool, str]:
        """
        Deleta um arquivo ou pasta.
        Requer confirmar=True para proteger contra deleções acidentais.
        """
        if not confirmar:
            return False, "Deleção requer confirmação explícita. Passe confirmar=True."

        p = Path(os.path.expanduser(path))
        if not p.exists():
            return False, f"Não encontrado: {path}"

        try:
            # Guarda registro antes de deletar
            self._lixeira.append({
                "nome": p.name,
                "path_original": str(p),
                "deletado_em": datetime.now().isoformat(),
                "era_pasta": p.is_dir()
            })

            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

            logger.info(f"[FileManager] Deletado: {p}")
            return True, f"'{p.name}' deletado."
        except Exception as e:
            return False, f"Erro ao deletar: {e}"

    # ------------------------------------------------------------------
    # Organizar pasta por tipo
    # ------------------------------------------------------------------

    def organize_by_type(self, path: str) -> tuple[bool, str]:
        """
        Organiza todos os arquivos de uma pasta em subpastas por tipo.
        Ideal para a pasta Downloads.

        Exemplo:
            Downloads/foto.jpg       → Downloads/Imagens/foto.jpg
            Downloads/relatorio.pdf  → Downloads/Documentos/relatorio.pdf
            Downloads/musica.mp3     → Downloads/Músicas/musica.mp3
        """
        p = Path(os.path.expanduser(path))
        if not p.exists() or not p.is_dir():
            return False, f"Pasta não encontrada: {path}"

        movidos = 0
        ignorados = 0
        sem_categoria = 0

        for arquivo in p.iterdir():
            if not arquivo.is_file():
                continue  # ignora subpastas

            ext = arquivo.suffix.lower()
            categoria = EXTENSION_MAP.get(ext)

            if not categoria:
                sem_categoria += 1
                continue

            destino_dir = p / categoria
            destino_dir.mkdir(exist_ok=True)
            destino = destino_dir / arquivo.name

            # Evita sobrescrever arquivo com mesmo nome
            if destino.exists():
                stem = arquivo.stem
                suffix = arquivo.suffix
                contador = 1
                while destino.exists():
                    destino = destino_dir / f"{stem}_{contador}{suffix}"
                    contador += 1

            try:
                shutil.move(str(arquivo), str(destino))
                movidos += 1
            except Exception as e:
                logger.warning(f"[FileManager] Erro ao mover '{arquivo.name}': {e}")
                ignorados += 1

        mensagem = f"Organização concluída. {movidos} arquivo(s) movido(s)."
        if sem_categoria > 0:
            mensagem += f" {sem_categoria} arquivo(s) sem categoria mantido(s) na raiz."
        if ignorados > 0:
            mensagem += f" {ignorados} erro(s) durante a operação."

        logger.info(f"[FileManager] Organizados {movidos} arquivos em '{path}'")
        return True, mensagem

    # ------------------------------------------------------------------
    # Buscar arquivos
    # ------------------------------------------------------------------

    def search(self, path: str, nome: str = "", extensao: str = "", max_results: int = 15) -> tuple[bool, str]:
        """
        Busca arquivos em uma pasta (recursivo) por nome ou extensão.

        Args:
            path:       Pasta raiz da busca.
            nome:       Parte do nome do arquivo (case-insensitive).
            extensao:   Extensão do arquivo (ex: '.pdf', '.mp3').
            max_results: Limite de resultados retornados.
        """
        p = Path(os.path.expanduser(path))
        if not p.exists():
            return False, f"Pasta não encontrada: {path}"

        resultados = []
        nome_lower = nome.lower()
        ext_lower  = extensao.lower()

        try:
            for arquivo in p.rglob("*"):
                if not arquivo.is_file():
                    continue
                nome_ok = (not nome_lower) or (nome_lower in arquivo.name.lower())
                ext_ok  = (not ext_lower) or (arquivo.suffix.lower() == ext_lower)
                if nome_ok and ext_ok:
                    resultados.append(arquivo)
                if len(resultados) >= max_results:
                    break

            if not resultados:
                return True, f"Nenhum arquivo encontrado com os critérios informados em '{p.name}'."

            nomes = ", ".join(r.name for r in resultados[:10])
            mensagem = f"{len(resultados)} arquivo(s) encontrado(s): {nomes}"
            if len(resultados) == max_results:
                mensagem += f" (limitado a {max_results} resultados)"

            return True, mensagem

        except PermissionError:
            return False, f"Sem permissão para buscar em '{path}'."

    # ------------------------------------------------------------------
    # Resumo do histórico de deleções
    # ------------------------------------------------------------------

    def deletion_history(self) -> str:
        """Retorna o histórico de arquivos deletados nesta sessão."""
        if not self._lixeira:
            return "Nenhum arquivo deletado nesta sessão."
        lines = [f"- {d['nome']} (deletado em {d['deletado_em'][:16]})" for d in self._lixeira[-10:]]
        return "\n".join(lines)