"""
Sexta-Feira v2.0 - Módulo de Escuta (Wake Word Offline + STT)
=========================================================
Usa Vosk para detecção de wake word 100% offline e local.
Google Speech Recognition para transcrição do comando.

Melhorias:
- Beep de confirmação quando a wake word é detectada
- Reconexão automática se o stream de áudio cair
- Limpeza de fila entre comandos
- Múltiplas variações da wake word
"""

import os
import json
import queue
import logging
import threading
import time
import sounddevice as sd
import speech_recognition as sr
from vosk import Model, KaldiRecognizer

logger = logging.getLogger("Listener")


class Listener:
    """
    Escuta contínua offline com Vosk para wake word.
    Após detectar a wake word, captura o comando via Google STT.
    """

    SAMPLE_RATE = 16000
    BLOCK_SIZE  = 8000
    CHANNELS    = 1

    def __init__(
        self,
        wake_word:       str = "sexta",
        model_path:      str = "models/vosk-model-small-pt-0.3",
        language:        str = "pt-BR",
        command_timeout: int = 8,
    ):
        self.language        = language
        self.command_timeout = command_timeout
        self._stop_event     = threading.Event()

        # Variações da wake word para aumentar taxa de detecção
        base = wake_word.lower().strip()
        self.wake_words = {base}
        if " " in base:
            # "sexta feira" → aceita "sexta" sozinho também
            self.wake_words.add(base.split()[0])
        logger.info(f"Wake words: {self.wake_words}")

        self._audio_queue: queue.Queue = queue.Queue()
        self._model = self._load_model(model_path)

        self._sr_recognizer = sr.Recognizer()
        self._sr_recognizer.pause_threshold = 0.8  # para de escutar mais rápido
        self._sr_mic = sr.Microphone(sample_rate=self.SAMPLE_RATE)
        self._calibrate()

    def _load_model(self, model_path: str) -> Model:
        abs_path = os.path.abspath(model_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(
                f"Modelo Vosk não encontrado em '{abs_path}'.\n"
                f"Baixe em: https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip\n"
                f"Extraia em: {abs_path}"
            )
        logger.info(f"Carregando modelo Vosk: {abs_path}")
        model = Model(abs_path)
        logger.info("Modelo Vosk carregado.")
        return model

    def _calibrate(self):
        logger.info("Calibrando microfone...")
        try:
            with self._sr_mic as source:
                self._sr_recognizer.adjust_for_ambient_noise(source, duration=1.5)
            logger.info("Calibração concluída.")
        except Exception as e:
            logger.warning(f"Erro na calibração: {e}")

    def _beep(self):
        """Toca um beep curto para confirmar detecção da wake word."""
        try:
            import numpy as np
            freq, dur, rate = 880, 0.12, 22050
            t = np.linspace(0, dur, int(rate * dur), False)
            wave = (np.sin(2 * np.pi * freq * t) * 0.3).astype("float32")
            sd.play(wave, rate, blocking=True)
        except Exception:
            pass  # beep é opcional, não deve travar

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"[Audio] {status}")
        self._audio_queue.put(bytes(indata))

    def _contains_wake_word(self, text: str) -> bool:
        text_lower = text.lower()
        return any(w in text_lower for w in self.wake_words)

    def _flush_queue(self):
        """Limpa a fila de áudio entre comandos."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def _listen_for_wake_word(self) -> bool:
        """Escuta continuamente até detectar a wake word. Reconecta automaticamente."""
        logger.info(f"Aguardando wake word: {self.wake_words}...")

        max_tentativas = 5
        tentativa = 0

        while not self._stop_event.is_set() and tentativa < max_tentativas:
            try:
                self._flush_queue()
                with sd.RawInputStream(
                    samplerate=self.SAMPLE_RATE,
                    blocksize=self.BLOCK_SIZE,
                    dtype="int16",
                    channels=self.CHANNELS,
                    callback=self._audio_callback,
                ):
                    rec = KaldiRecognizer(self._model, self.SAMPLE_RATE)
                    tentativa = 0  # reset ao conectar com sucesso

                    while not self._stop_event.is_set():
                        try:
                            data = self._audio_queue.get(timeout=0.5)
                        except queue.Empty:
                            continue

                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            text   = result.get("text", "")
                            if text:
                                logger.debug(f"[Vosk] '{text}'")
                            if self._contains_wake_word(text):
                                logger.info("Wake word detectada!")
                                self._beep()
                                return True
                        else:
                            partial = json.loads(rec.PartialResult()).get("partial", "")
                            if self._contains_wake_word(partial):
                                rec.Result()
                                logger.info("Wake word detectada (parcial)!")
                                self._beep()
                                return True

            except Exception as e:
                tentativa += 1
                logger.warning(f"Erro no stream de áudio (tentativa {tentativa}/{max_tentativas}): {e}")
                if tentativa < max_tentativas:
                    time.sleep(2)

        return False

    def _capture_command_google(self) -> str | None:
        logger.info("Escutando comando...")
        try:
            with self._sr_mic as source:
                audio = self._sr_recognizer.listen(
                    source,
                    timeout=3,
                    phrase_time_limit=self.command_timeout
                )
        except sr.WaitTimeoutError:
            logger.warning("Timeout aguardando comando.")
            return None
        except Exception as e:
            logger.warning(f"Erro ao capturar áudio: {e}")
            return None

        try:
            texto = self._sr_recognizer.recognize_google(audio, language=self.language)
            return texto.lower().strip()
        except sr.UnknownValueError:
            logger.debug("Comando não compreendido.")
            return None
        except sr.RequestError:
            logger.warning("Google STT indisponível. Tentando Vosk...")
            return self._capture_command_vosk(audio)
        except Exception as e:
            logger.warning(f"Erro no STT: {e}")
            return None

    def _capture_command_vosk(self, audio: sr.AudioData) -> str | None:
        try:
            rec   = KaldiRecognizer(self._model, self.SAMPLE_RATE)
            raw   = audio.get_raw_data(convert_rate=self.SAMPLE_RATE, convert_width=2)
            chunk = 4000
            for i in range(0, len(raw), chunk):
                rec.AcceptWaveform(raw[i:i+chunk])
            result = json.loads(rec.FinalResult())
            texto  = result.get("text", "").strip()
            return texto if texto else None
        except Exception as e:
            logger.warning(f"Erro Vosk fallback: {e}")
            return None

    def listen_for_command(self) -> str | None:
        """
        Aguarda wake word offline (Vosk) e captura o comando (Google STT).
        Retorna a transcrição do comando ou None.
        """
        if not self._listen_for_wake_word():
            return None
        comando = self._capture_command_google()
        if comando:
            logger.info(f"Comando: '{comando}'")
        return comando

    def stop(self):
        self._stop_event.set()