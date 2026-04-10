"""
JARVIS v2.0 - Módulo de Fala (Text-to-Speech)
==============================================
Usa edge-tts (Microsoft Edge TTS) para síntese de voz de alta qualidade
em português, sem custo e sem autenticação.

Instalação:
    pip install edge-tts pygame

Vozes PT-BR disponíveis (as melhores):
    pt-BR-AntonioNeural   ← masculina, natural (recomendada para JARVIS)
    pt-BR-FranciscaNeural ← feminina, natural
    pt-BR-ThalitaNeural   ← feminina, jovem

Para listar todas as vozes disponíveis, rode:
    python -m edge_tts --list-voices | findstr pt-BR
"""

import asyncio
import logging
import os
import tempfile
import edge_tts
import pygame

logger = logging.getLogger("Speaker")


# Vozes disponíveis para fácil troca no config
VOICES = {
    "antonio":   "pt-BR-AntonioNeural",    # masculina — recomendada para JARVIS
    "francisca": "pt-BR-FranciscaNeural",  # feminina
    "thalita":   "pt-BR-ThalitaNeural",    # feminina jovem
}


class Speaker:
    """
    Síntese de voz usando Microsoft Edge TTS (edge-tts).
    
    Gera o áudio via API da Microsoft (gratuita, sem chave),
    salva em arquivo temporário e reproduz com pygame.
    Qualidade significativamente superior ao pyttsx3.
    """

    def __init__(
        self,
        voice: str = "antonio",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        Args:
            voice: Chave do dict VOICES ou nome completo da voz Edge TTS.
                   Ex: "antonio", "francisca" ou "pt-BR-AntonioNeural".
            rate:  Velocidade. Ex: "+10%" mais rápido, "-10%" mais lento.
            volume: Volume. Ex: "+20%", "-10%".
            pitch:  Tom. Ex: "-5Hz" mais grave, "+5Hz" mais agudo.
        """
        self.voice  = VOICES.get(voice, voice)
        self.rate   = rate
        self.volume = volume
        self.pitch  = pitch

        pygame.mixer.init()
        logger.info(f"Speaker iniciado | voz: {self.voice} | rate: {rate} | pitch: {pitch}")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def speak(self, text: str):
        """
        Sintetiza e reproduz o texto em voz alta.
        Operação bloqueante — aguarda o fim da fala antes de retornar.

        Args:
            text: Texto a ser falado.
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
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"[Speaker] Erro na síntese/reprodução: {e}")
        finally:
            pygame.mixer.music.unload()
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def set_voice(self, voice: str):
        """Troca a voz em tempo de execução."""
        self.voice = VOICES.get(voice, voice)
        logger.info(f"[Speaker] Voz alterada para: {self.voice}")

    def set_rate(self, rate: str):
        """Ajusta a velocidade. Ex: '+20%', '-10%'."""
        self.rate = rate
        logger.info(f"[Speaker] Rate alterado para: {rate}")

    @staticmethod
    async def _list_voices_async() -> list[dict]:
        voices = await edge_tts.list_voices()
        return [v for v in voices if "pt-BR" in v["ShortName"]]

    def list_voices(self) -> list[dict]:
        """Retorna todas as vozes PT-BR disponíveis. Útil para debug."""
        voices = asyncio.run(self._list_voices_async())
        for v in voices:
            logger.info(f"  {v['ShortName']} | gender: {v['Gender']}")
        return voices