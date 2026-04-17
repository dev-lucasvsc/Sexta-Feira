"""
Sexta-Feira v2.0 - Módulo de Controle de Janelas
=================================================
Controla janelas abertas no Windows por voz.
Permite minimizar, maximizar, fechar, focar e listar janelas.

Comandos de voz:
    "minimizar tudo"            → mostra área de trabalho
    "maximizar janela"          → maximiza a janela atual
    "fechar janela"             → fecha a janela em foco
    "focar no chrome"           → coloca o Chrome em foco
    "listar janelas abertas"    → lista o que está aberto
    "alternar janela"           → Alt+Tab
    "mover janela pra esquerda" → snap left (Win+←)
    "mover janela pra direita"  → snap right (Win+→)

Requer:
    pip install pygetwindow pyautogui
"""

import logging
import subprocess

logger = logging.getLogger("WindowManager")


class WindowManager:
    """
    Gerencia janelas do Windows via pygetwindow e pyautogui.
    Fallback para comandos PowerShell quando necessário.
    """

    def __init__(self):
        self._gw_available = self._check_pygetwindow()

    def _check_pygetwindow(self) -> bool:
        try:
            import pygetwindow
            return True
        except ImportError:
            logger.warning("[WindowManager] pygetwindow não instalado. Funcionalidade limitada.")
            logger.warning("              Execute: pip install pygetwindow pyautogui")
            return False

    # ------------------------------------------------------------------
    # Operações básicas
    # ------------------------------------------------------------------

    def minimize_all(self) -> tuple[bool, str]:
        """Minimiza todas as janelas (mostra área de trabalho)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            logger.info("[WindowManager] Todas as janelas minimizadas.")
            return True, "Área de trabalho exibida."
        except Exception as e:
            # Fallback via PowerShell
            subprocess.run(
                'powershell -c "(New-Object -ComObject Shell.Application).ToggleDesktop()"',
                shell=True
            )
            return True, "Área de trabalho exibida."

    def maximize_current(self) -> tuple[bool, str]:
        """Maximiza a janela em foco."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "up")
            return True, "Janela maximizada."
        except Exception as e:
            return False, f"Erro ao maximizar: {e}"

    def close_current(self) -> tuple[bool, str]:
        """Fecha a janela em foco."""
        try:
            import pyautogui
            pyautogui.hotkey("alt", "F4")
            return True, "Janela fechada."
        except Exception as e:
            return False, f"Erro ao fechar janela: {e}"

    def alt_tab(self) -> tuple[bool, str]:
        """Alterna entre janelas (Alt+Tab)."""
        try:
            import pyautogui
            pyautogui.hotkey("alt", "tab")
            return True, "Alternando janela."
        except Exception as e:
            return False, f"Erro: {e}"

    def snap_left(self) -> tuple[bool, str]:
        """Encaixa a janela na metade esquerda (Win+←)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "left")
            return True, "Janela movida para a esquerda."
        except Exception as e:
            return False, f"Erro: {e}"

    def snap_right(self) -> tuple[bool, str]:
        """Encaixa a janela na metade direita (Win+→)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "right")
            return True, "Janela movida para a direita."
        except Exception as e:
            return False, f"Erro: {e}"

    # ------------------------------------------------------------------
    # Foco em janela específica
    # ------------------------------------------------------------------

    def focus_window(self, nome: str) -> tuple[bool, str]:
        """
        Coloca em foco a janela cujo título contém 'nome'.

        Args:
            nome: Parte do título da janela (case-insensitive).
        """
        if not self._gw_available:
            return False, "pygetwindow não instalado."

        try:
            import pygetwindow as gw
            nome_lower = nome.lower()
            janelas = [w for w in gw.getAllWindows()
                       if nome_lower in w.title.lower() and w.title.strip()]

            if not janelas:
                return False, f"Nenhuma janela encontrada com '{nome}'."

            janela = janelas[0]
            janela.activate()
            logger.info(f"[WindowManager] Foco em: '{janela.title}'")
            return True, f"Focando em {janela.title}."

        except Exception as e:
            logger.error(f"[WindowManager] Erro ao focar '{nome}': {e}")
            return False, f"Não consegui focar em '{nome}'."

    # ------------------------------------------------------------------
    # Listar janelas
    # ------------------------------------------------------------------

    def list_windows(self) -> tuple[bool, str]:
        """Lista todas as janelas abertas com título visível."""
        if not self._gw_available:
            return False, "pygetwindow não instalado."

        try:
            import pygetwindow as gw
            janelas = [w.title for w in gw.getAllWindows()
                       if w.title.strip() and len(w.title.strip()) > 2]

            # Remove duplicatas e ordena
            janelas = sorted(set(janelas))

            if not janelas:
                return True, "Nenhuma janela aberta encontrada."

            # Limita a 8 janelas na resposta falada
            amostra = janelas[:8]
            fala = f"{len(janelas)} janela(s) aberta(s): {', '.join(amostra)}"
            if len(janelas) > 8:
                fala += f" e mais {len(janelas) - 8}."

            return True, fala

        except Exception as e:
            return False, f"Erro ao listar janelas: {e}"

    # ------------------------------------------------------------------
    # Atalhos de sistema
    # ------------------------------------------------------------------

    def open_task_view(self) -> tuple[bool, str]:
        """Abre a visão de tarefas do Windows (Win+Tab)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "tab")
            return True, "Visão de tarefas aberta."
        except Exception as e:
            return False, f"Erro: {e}"

    def new_virtual_desktop(self) -> tuple[bool, str]:
        """Cria um novo desktop virtual (Win+Ctrl+D)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "d")
            return True, "Novo desktop virtual criado."
        except Exception as e:
            return False, f"Erro: {e}"