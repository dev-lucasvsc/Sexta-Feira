"""
Sexta-Feira v2.0 - Módulo de Fala (Text-to-Speech)
==============================================
Usa edge-tts (Microsoft Edge TTS) como engine principal.
Fallback automático para pyttsx3 (offline) caso edge-tts falhe
ou não haja acesso aos servidores da Microsoft.

Vozes PT-BR disponíveis (edge-tts):
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

# --- Import seguro do edge-tts ---
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except Exception as _e:
    edge_tts = None  # type: ignore
    EDGE_TTS_AVAILABLE = False
    logging.getLogger("Speaker").warning(
        f"[Speaker] edge-tts indisponível ({_e}). Usando pyttsx3 como fallback."
    )

# --- Import seguro do pygame ---
try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception:
    pygame = None  # type: ignore
    PYGAME_AVAILABLE = False

# --- Import seguro do pyttsx3 (fallback offline) ---
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except Exception:
    pyttsx3 = None  # type: ignore
    PYTTSX3_AVAILABLE = False

logger = logging.getLogger("Speaker")

VOICES = {
    "antonio":   "pt-BR-AntonioNeural",
    "francisca": "pt-BR-FranciscaNeural",
    "thalita":   "pt-BR-ThalitaNeural",
}


class Speaker:
    """
    Síntese de voz com fallback automático:

    1. edge-tts (online, Microsoft) + pygame  → alta qualidade
    2. pyttsx3 (offline, sistema)             → fallback automático

    A escolha do engine ocorre no __init__ e pode ser forçada
    via parâmetro `force_engine="pyttsx3"` ou `"edge"`.

    CORREÇÃO asyncio/Windows: o loop asyncio roda em thread dedicada
    para evitar conflito com pygame, watchdog e websockets.
    """

    def __init__(
        self,
        voice:        str = "francisca",
        rate:         str = "+0%",
        volume:       str = "+0%",
        pitch:        str = "+0Hz",
        force_engine: str = "auto",   # "auto" | "edge" | "pyttsx3"
    ):
        self.voice  = VOICES.get(voice, voice)
        self.rate   = rate
        self.volume = volume
        self.pitch  = pitch

        self.on_speaking_change: Callable[[bool], None] | None = None
        self._speaking = False

        # --- Escolha do engine ---
        self._engine = self._select_engine(force_engine)
        logger.info(f"[Speaker] Engine TTS selecionado: {self._engine}")

        # --- Inicialização do pygame (apenas se edge-tts for o engine) ---
        if self._engine == "edge" and PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                logger.info(f"[Speaker] pygame inicializado | voz: {self.voice}")
            except Exception as e:
                logger.error(f"[Speaker] Erro ao inicializar pygame: {e}")
                self._engine = "pyttsx3"
                logger.warning("[Speaker] Revertendo para pyttsx3.")

        # --- Inicialização do pyttsx3 (apenas se for o engine ativo) ---
        self._pyttsx3_engine = None
        if self._engine == "pyttsx3":
            self._init_pyttsx3()

        # --- Loop asyncio dedicado (apenas para edge-tts) ---
        self._loop   = None
        self._thread = None
        if self._engine == "edge":
            self._loop   = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    # ------------------------------------------------------------------
    # Seleção de engine
    # ------------------------------------------------------------------

    def _select_engine(self, force: str) -> str:
        """Decide qual engine usar com base na disponibilidade e no parâmetro."""
        if force == "edge":
            if EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE:
                return "edge"
            logger.warning("[Speaker] edge-tts forçado mas indisponível. Usando pyttsx3.")
            return "pyttsx3"

        if force == "pyttsx3":
            return "pyttsx3"

        # auto: prefere edge-tts se disponível
        if EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE:
            return "edge"

        if PYTTSX3_AVAILABLE:
            logger.warning("[Speaker] edge-tts indisponível. Usando pyttsx3 (offline).")
            return "pyttsx3"

        raise RuntimeError(
            "[Speaker] Nenhum engine TTS disponível. "
            "Instale: pip install edge-tts pygame  OU  pip install pyttsx3"
        )

    # ------------------------------------------------------------------
    # Inicialização do pyttsx3
    # ------------------------------------------------------------------

    def _init_pyttsx3(self):
        """Inicializa o pyttsx3 e configura voz PT-BR se disponível."""
        try:
            self._pyttsx3_engine = pyttsx3.init()

            # Tenta selecionar voz feminina PT-BR
            voices = self._pyttsx3_engine.getProperty("voices")
            voz_ptbr = None
            for v in voices:
                if "brazil" in v.name.lower() or "português" in v.name.lower() or "pt" in v.id.lower():
                    voz_ptbr = v.id
                    break

            if voz_ptbr:
                self._pyttsx3_engine.setProperty("voice", voz_ptbr)
                logger.info(f"[Speaker] pyttsx3 voz PT-BR: {voz_ptbr}")
            else:
                logger.warning("[Speaker] Nenhuma voz PT-BR encontrada no pyttsx3. Usando voz padrão do sistema.")

            # Taxa de fala (pyttsx3 usa valor inteiro, padrão ~200)
            self._pyttsx3_engine.setProperty("rate", 175)
            self._pyttsx3_engine.setProperty("volume", 1.0)

            logger.info("[Speaker] pyttsx3 inicializado com sucesso.")
        except Exception as e:
            logger.error(f"[Speaker] Falha ao inicializar pyttsx3: {e}")
            self._pyttsx3_engine = None

    # ------------------------------------------------------------------
    # Loop asyncio (edge-tts)
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Roda o event loop asyncio em thread separada."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ------------------------------------------------------------------
    # Estado de fala
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def speak(self, text: str):
        """
        Sintetiza e reproduz o texto em voz alta.
        Roteamento automático para o engine ativo (edge-tts ou pyttsx3).
        Bloqueante — aguarda o fim da fala antes de retornar.
        """
        if not text or not text.strip():
            return

        logger.info(f"[FALA] '{text}'")

        if self._engine == "edge":
            self._speak_edge(text)
        else:
            self._speak_pyttsx3(text)

    # ------------------------------------------------------------------
    # Engine 1: edge-tts + pygame
    # ------------------------------------------------------------------

    def _speak_edge(self, text: str):
        """Fala usando edge-tts. Fallback para pyttsx3 em caso de falha de rede."""
        future = asyncio.run_coroutine_threadsafe(
            self._synthesize_and_play(text),
            self._loop
        )
        try:
            future.result(timeout=60)
        except Exception as e:
            logger.error(f"[Speaker] edge-tts falhou: {e}. Tentando pyttsx3...")
            self._set_speaking(False)
            # Fallback em tempo real para pyttsx3
            if PYTTSX3_AVAILABLE:
                if self._pyttsx3_engine is None:
                    self._init_pyttsx3()
                self._speak_pyttsx3(text)

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

            # Reprodução em thread separada (pygame não é thread-safe)
            play_thread = threading.Thread(
                target=self._play_audio_pygame,
                args=(tmp_path,),
                daemon=True
            )
            play_thread.start()
            play_thread.join(timeout=2)  # aguarda o play() iniciar

            self._set_speaking(True)

            # Aguarda o áudio terminar
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"[Speaker] Erro na síntese edge-tts: {e}")
            raise  # propaga para _speak_edge acionar o fallback
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

    def _play_audio_pygame(self, path: str):
        """Carrega e inicia a reprodução do arquivo de áudio via pygame."""
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except Exception as e:
            logger.error(f"[Speaker] Erro no pygame: {e}")

    # ------------------------------------------------------------------
    # Engine 2: pyttsx3 (offline)
    # ------------------------------------------------------------------

    def _speak_pyttsx3(self, text: str):
        """Fala usando pyttsx3 (offline, sem internet)."""
        if self._pyttsx3_engine is None:
            logger.error("[Speaker] pyttsx3 não inicializado.")
            return

        try:
            self._set_speaking(True)
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        except Exception as e:
            logger.error(f"[Speaker] Erro no pyttsx3: {e}")
        finally:
            self._set_speaking(False)

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def set_voice(self, voice: str):
        """Altera a voz do edge-tts (não afeta pyttsx3)."""
        self.voice = VOICES.get(voice, voice)
        logger.info(f"[Speaker] Voz edge-tts alterada para: {self.voice}")

    def set_rate(self, rate: str):
        """Altera a taxa de fala do edge-tts (ex: '+10%', '-20%')."""
        self.rate = rate

    def get_engine(self) -> str:
        """Retorna o engine TTS ativo."""
        return self._engine

    def stop(self):
        """Encerra os recursos do Speaker de forma limpa."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._pyttsx3_engine:
            try:
                self._pyttsx3_engine.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Listagem de vozes (edge-tts)
    # ------------------------------------------------------------------

    @staticmethod
    async def _list_voices_async() -> list[dict]:
        if not EDGE_TTS_AVAILABLE:
            return []
        voices = await edge_tts.list_voices()
        return [v for v in voices if "pt-BR" in v["ShortName"]]

    def list_voices(self) -> list[dict]:
        """Lista vozes PT-BR disponíveis no edge-tts."""
        if not EDGE_TTS_AVAILABLE or self._loop is None:
            logger.warning("[Speaker] edge-tts indisponível. Não é possível listar vozes.")
            return []
        future = asyncio.run_coroutine_threadsafe(
            self._list_voices_async(),
            self._loop
        )
        try:
            voices = future.result(timeout=10)
            for v in voices:
                logger.info(f"  {v['ShortName']} | gender: {v['Gender']}")
            return voices
        except Exception as e:
            logger.error(f"[Speaker] Erro ao listar vozes: {e}")
            return []