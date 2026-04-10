"""
Sexta-Feira v2.0 - Módulo de Lembretes
=======================================
Gerencia lembretes por tempo disparados por voz.
Cada lembrete roda em uma thread separada e chama
um callback ao vencer, sem bloquear o loop principal.
"""

import threading
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("Reminder")


class ReminderManager:
    """
    Gerencia lembretes com disparo via callback.

    Uso:
        rm = ReminderManager(on_reminder=minha_funcao)
        rm.add(minutos=30, texto="Reunião com o cliente")
    """

    def __init__(self, on_reminder=None):
        """
        Args:
            on_reminder: Callable(texto: str) chamado quando o lembrete vence.
        """
        self.on_reminder = on_reminder
        self._lembretes: list[dict] = []
        self._lock = threading.Lock()

    def add(self, texto: str, minutos: int = 0, segundos: int = 0) -> str:
        """
        Agenda um lembrete.

        Args:
            texto:    Mensagem do lembrete.
            minutos:  Minutos até disparar.
            segundos: Segundos adicionais.

        Returns:
            Confirmação em texto para ser falada.
        """
        total_seg = minutos * 60 + segundos
        if total_seg <= 0:
            return "O tempo do lembrete precisa ser maior que zero."

        vence_em = datetime.now() + timedelta(seconds=total_seg)
        lembrete = {
            "id":      len(self._lembretes) + 1,
            "texto":   texto,
            "vence":   vence_em,
            "ativo":   True,
        }

        with self._lock:
            self._lembretes.append(lembrete)

        # Dispara thread de contagem
        t = threading.Timer(total_seg, self._disparar, args=[lembrete])
        t.daemon = True
        t.start()
        lembrete["_timer"] = t

        # Monta confirmação
        if minutos > 0 and segundos > 0:
            tempo_str = f"{minutos} minuto(s) e {segundos} segundo(s)"
        elif minutos > 0:
            tempo_str = f"{minutos} minuto(s)"
        else:
            tempo_str = f"{segundos} segundo(s)"

        hora_str = vence_em.strftime("%H:%M")
        logger.info(f"[Reminder] Agendado em {tempo_str}: '{texto}'")
        return f"Lembrete criado. Em {tempo_str}, às {hora_str}, vou te avisar: {texto}."

    def _disparar(self, lembrete: dict):
        """Chamado pela thread quando o tempo vence."""
        if not lembrete.get("ativo"):
            return

        lembrete["ativo"] = False
        texto = lembrete["texto"]
        logger.info(f"[Reminder] Disparado: '{texto}'")

        if self.on_reminder:
            try:
                self.on_reminder(texto)
            except Exception as e:
                logger.error(f"[Reminder] Erro no callback: {e}")

    def list_active(self) -> str:
        """Retorna os lembretes ativos como texto."""
        with self._lock:
            ativos = [l for l in self._lembretes if l.get("ativo")]

        if not ativos:
            return "Não há lembretes ativos no momento."

        lines = []
        for l in ativos:
            hora = l["vence"].strftime("%H:%M:%S")
            lines.append(f"- {l['texto']} às {hora}")

        return f"{len(ativos)} lembrete(s) ativo(s): " + "; ".join(
            f"{l['texto']} às {l['vence'].strftime('%H:%M')}" for l in ativos
        )

    def cancel_all(self):
        """Cancela todos os lembretes ativos."""
        with self._lock:
            for l in self._lembretes:
                if l.get("ativo"):
                    l["ativo"] = False
                    t = l.get("_timer")
                    if t:
                        t.cancel()
        logger.info("[Reminder] Todos os lembretes cancelados.")