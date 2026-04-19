"""
Sexta-Feira v2.0 - Módulo de Fala (Text-to-Speech)
==============================================
Usa edge-tts (Microsoft Edge TTS) para síntese de voz de alta qualidade
em português, sem custo e sem autenticação.

Instalação:
    pip install edge-tts pygame

Vozes PT-BR disponíveis:
    pt-BR-AntonioNeural   ← masculina, natural
    pt-BR-FranciscaNeural ← feminina, natural
    pt-BR-ThalitaNeural   ← feminina, jovem

Para listar todas as vozes disponíveis, rode:
    python -m edge_tts --list-voices | findstr pt-BR
"""

import asyncio
import logging
import os
import tempfile
import threading
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

    CORREÇÃO: asyncio.run() conflita com o event loop do Windows quando
    há threads ativas (pygame, watchdog, etc). A solução é rodar o loop
    asyncio em uma thread dedicada separada, isolada do loop principal.
    """

    def __init__(
        self,
        voice:  str = "antonio",
        rate:   str = "+0%",
        volume: str = "+0%",
        pitch:  str = "+0Hz",
    ):
        self.voice  = VOICES.get(voice, voice)
        self.rate   = rate
        self.volume = volume
        self.pitch  = pitch

        self.on_speaking_change: Callable[[bool], None] | None = None
        self._speaking = False

        # Thread dedicada com seu próprio event loop asyncio
        # Evita conflito com loops já existentes (pygame, watchdog, websockets)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Inicializa pygame no thread principal
        try:
            pygame.mixer.init()
            logger.info(f"Speaker iniciado | voz: {self.voice} | rate: {rate} | pitch: {pitch}")
        except Exception as e:
            logger.error(f"[Speaker] Erro ao inicializar pygame: {e}")

    def _run_loop(self):
        """Roda o event loop asyncio em thread separada."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def _set_speaking(self, value: bool):
        """Atualiza estado e dispara callback."""
        if self._speaking != value:
            self._speaking = value
            if self.on_speaking_change:
                try:
                    self.on_speaking_change(value)
                except Exception as e:
                    logger.warning(f"[Speaker] Erro no callback: {e}")

    def speak(self, text: str):
        """
        Sintetiza e reproduz o texto em voz alta.
        Bloqueante — aguarda o fim da fala antes de retornar.
        Usa thread asyncio dedicada para evitar conflitos no Windows.
        """
        if not text or not text.strip():
            return

        logger.info(f"[FALA] '{text}'")

        # Submete a coroutine ao loop dedicado e aguarda conclusão
        future = asyncio.run_coroutine_threadsafe(
            self._synthesize_and_play(text),
            self._loop
        )
        try:
            future.result(timeout=60)  # timeout de 60s para falas longas
        except Exception as e:
            logger.error(f"[Speaker] Erro na fala: {e}")
            self._set_speaking(False)

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

            # pygame precisa ser chamado do thread principal — usa call_soon_threadsafe
            play_done = asyncio.Event()

            def play_audio():
                try:
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                except Exception as e:
                    logger.error(f"[Speaker] Erro no pygame: {e}")
                    self._loop.call_soon_threadsafe(play_done.set)

            # Agenda reprodução no thread principal via threading
            play_thread = threading.Thread(target=play_audio, daemon=True)
            play_thread.start()
            play_thread.join(timeout=2)  # aguarda o play() iniciar

            self._set_speaking(True)

            # Aguarda o áudio terminar
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"[Speaker] Erro na síntese: {e}")
        finally:
            self._set_speaking(False)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def set_voice(self, voice: str):
        self.voice = VOICES.get(voice, voice)
        logger.info(f"[Speaker] Voz alterada para: {self.voice}")

    def set_rate(self, rate: str):
        self.rate = rate

    def stop(self):
        """Encerra o loop asyncio dedicado."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    @staticmethod
    async def _list_voices_async() -> list[dict]:
        voices = await edge_tts.list_voices()
        return [v for v in voices if "pt-BR" in v["ShortName"]]

    def list_voices(self) -> list[dict]:
        future = asyncio.run_coroutine_threadsafe(
            self._list_voices_async(),
            self._loop
        )
        voices = future.result(timeout=10)
        for v in voices:
            logger.info(f"  {v['ShortName']} | gender: {v['Gender']}")
        return voices