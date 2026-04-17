"""
Sexta-Feira v2.0 - Módulo de Notificações Windows
==================================================
Exibe notificações nativas (toast) no canto da tela do Windows.
Usado para alertas silenciosos, lembretes visuais e confirmações
sem precisar de fala.

Requer:
    pip install win10toast-click
    (fallback: win10toast ou plyer)

Uso:
    notifier = WindowsNotifier()
    notifier.show("Lembrete", "Reunião em 5 minutos", duracao=8)
"""

import logging
import threading

logger = logging.getLogger("Notifier")


class WindowsNotifier:
    """
    Exibe notificações toast nativas do Windows 10/11.
    Opera em thread separada para não bloquear o loop principal.
    """

    APP_NAME = "Sexta-Feira"
    ICON_PATH = "assets/icon.ico"  # opcional — usa padrão se não existir

    def __init__(self):
        self._backend = self._detect_backend()
        logger.info(f"[Notifier] Backend: {self._backend}")

    def _detect_backend(self) -> str:
        """Detecta qual biblioteca de notificação está disponível."""
        try:
            from win10toast import ToastNotifier
            return "win10toast"
        except ImportError:
            pass
        try:
            from plyer import notification
            return "plyer"
        except ImportError:
            pass
        logger.warning("[Notifier] Nenhuma biblioteca de notificação encontrada.")
        logger.warning("          Execute: pip install win10toast")
        return "none"

    def show(
        self,
        titulo:   str,
        mensagem: str,
        duracao:  int = 5,
        urgente:  bool = False,
    ):
        """
        Exibe uma notificação toast no Windows.
        Operação não-bloqueante — roda em thread separada.

        Args:
            titulo:   Título da notificação.
            mensagem: Corpo da mensagem.
            duracao:  Segundos que a notificação fica visível.
            urgente:  Se True, dura mais tempo (10s mínimo).
        """
        if urgente:
            duracao = max(duracao, 10)

        t = threading.Thread(
            target=self._show_sync,
            args=(titulo, mensagem, duracao),
            daemon=True
        )
        t.start()

    def _show_sync(self, titulo: str, mensagem: str, duracao: int):
        """Exibe a notificação de forma síncrona (roda em thread)."""
        import os

        if self._backend == "win10toast":
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                icon    = self.ICON_PATH if os.path.exists(self.ICON_PATH) else None
                toaster.show_toast(
                    titulo,
                    mensagem,
                    icon_path=icon,
                    duration=duracao,
                    threaded=False,
                )
            except Exception as e:
                logger.warning(f"[Notifier] win10toast erro: {e}")

        elif self._backend == "plyer":
            try:
                from plyer import notification
                notification.notify(
                    title=titulo,
                    message=mensagem,
                    app_name=self.APP_NAME,
                    timeout=duracao,
                )
            except Exception as e:
                logger.warning(f"[Notifier] plyer erro: {e}")

        else:
            # Fallback: PowerShell balloon tip
            try:
                import subprocess
                ps = (
                    f'Add-Type -AssemblyName System.Windows.Forms; '
                    f'$n = New-Object System.Windows.Forms.NotifyIcon; '
                    f'$n.Icon = [System.Drawing.SystemIcons]::Information; '
                    f'$n.Visible = $true; '
                    f'$n.ShowBalloonTip({duracao * 1000}, "{titulo}", "{mensagem}", '
                    f'[System.Windows.Forms.ToolTipIcon]::Info); '
                    f'Start-Sleep -Milliseconds {duracao * 1000 + 500}; '
                    f'$n.Dispose()'
                )
                subprocess.Popen(
                    ["powershell", "-Command", ps],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                logger.warning(f"[Notifier] PowerShell fallback erro: {e}")

        logger.debug(f"[Notifier] '{titulo}': {mensagem[:50]}")

    # ------------------------------------------------------------------
    # Notificações pré-definidas
    # ------------------------------------------------------------------

    def notify_reminder(self, texto: str):
        """Notificação de lembrete."""
        self.show("⏰ Lembrete — Sexta-Feira", texto, duracao=10, urgente=True)

    def notify_command_result(self, resultado: str):
        """Notificação de resultado de comando (modo silencioso)."""
        self.show("Sexta-Feira", resultado, duracao=6)

    def notify_error(self, erro: str):
        """Notificação de erro."""
        self.show("⚠️ Sexta-Feira — Erro", erro, duracao=8)

    def notify_listening(self):
        """Notificação discreta de que está escutando."""
        self.show("Sexta-Feira", "Escutando...", duracao=2)