"""
Sexta-Feira v2.0 - Módulo de Fala (Text-to-Speech)
==============================================
Usa edge-tts (Microsoft Edge TTS) para síntese de voz de alta qualidade
em português, sem custo e sem autenticação.

Instalação:
    pip install edge-tts pygame

Vozes PT-BR disponíveis (as melhores):
    pt-BR-AntonioNeural   ← masculina, natural (recomendada para Sexta-Feira)
    pt-BR-FranciscaNeural ← feminina, natural
    pt-BR-ThalitaNeural   ← feminina, jovem

Para listar todas as vozes disponíveis, rode:
    python -m edge_tts --list-voices | findstr pt-BR
"""

import asyncio
import logging
import os
import tempfile
from typing import Callable
import edge_tts
import pygame

logger = logging.getLogger("Speaker")


VOICES = {
    "antonio":   "pt-BR-AntonioNeural",
    "francisca": "pt-BR-FranciscaNeural",
    "thalita":   "pt-BR-ThalitaNeural",
}


class Speaker:
    """
    Síntese de voz usando Microsoft Edge TTS (edge-tts).

    Expõe o callback `on_speaking_change(falando: bool)` para que
    o Orchestrator possa atualizar a interface holográfica em tempo real
    durante toda a duração da fala.
    """

    def __init__(
        self,
        voice:  str = "francisca",
        rate:   str = "+0%",
        volume: str = "+0%",
        pitch:  str = "+0Hz",
    ):
        self.voice  = VOICES.get(voice, voice)
        self.rate   = rate
        self.volume = volume
        self.pitch  = pitch

        # Callback chamado quando o estado de fala muda:
        # on_speaking_change(True)  → começou a falar
        # on_speaking_change(False) → terminou de falar
        self.on_speaking_change: Callable[[bool], None] | None = None

        self._speaking = False
        pygame.mixer.init()
        logger.info(f"Speaker iniciado | voz: {self.voice} | rate: {rate} | pitch: {pitch}")

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def _set_speaking(self, value: bool):
        """Atualiza o estado e dispara o callback se registrado."""
        if self._speaking != value:
            self._speaking = value
            if self.on_speaking_change:
                try:
                    self.on_speaking_change(value)
                except Exception as e:
                    logger.warning(f"[Speaker] Erro no callback on_speaking_change: {e}")

    def speak(self, text: str):
        """
        Sintetiza e reproduz o texto em voz alta.
        Bloqueante — aguarda o fim da fala antes de retornar.
        Dispara on_speaking_change(True/False) nos limites da fala.
        """
        if not text or not text.strip():
            return

        logger.info(f"[FALA] '{text}'")
        asyncio.run(self._synthesize_and_play(text))

    async def _synthesize_and_play(self, text: str):
        """Gera o áudio com edge-tts e reproduz com pygame."""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(tmp_path)

            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            self._set_speaking(True)   # ← interface entra em modo speak

            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"[Speaker] Erro na síntese/reprodução: {e}")
        finally:
            self._set_speaking(False)  # ← interface volta ao standby
            pygame.mixer.music.unload()
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def set_voice(self, voice: str):
        self.voice = VOICES.get(voice, voice)
        logger.info(f"[Speaker] Voz alterada para: {self.voice}")

    def set_rate(self, rate: str):
        self.rate = rate
        logger.info(f"[Speaker] Rate alterado para: {rate}")

    @staticmethod
    async def _list_voices_async() -> list[dict]:
        voices = await edge_tts.list_voices()
        return [v for v in voices if "pt-BR" in v["ShortName"]]

    def list_voices(self) -> list[dict]:
        voices = asyncio.run(self._list_voices_async())
        for v in voices:
            logger.info(f"  {v['ShortName']} | gender: {v['Gender']}")
        return voices