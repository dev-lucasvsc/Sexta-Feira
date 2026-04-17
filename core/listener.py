"""
Sexta-Feira v2.0 - Módulo de Escuta (Wake Word Offline + STT)
=========================================================
Usa Vosk para detecção de wake word 100% offline e local.
Google Speech Recognition como fallback para transcrição do comando
(maior precisão para frases longas).

Instalação:
    pip install vosk sounddevice

Modelo PT-BR:
    https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
    Extrair em: D:/jarvis/models/vosk-model-small-pt-0.3/
"""

import os
import json
import queue
import logging
import threading
import sounddevice as sd
import speech_recognition as sr
from vosk import Model, KaldiRecognizer

logger = logging.getLogger("Listener")


class Listener:
    """
    Escuta contínua offline com Vosk para wake word.
    Após detectar a wake word, captura o comando completo
    via Google STT (maior precisão) ou Vosk como fallback.

    Fluxo:
        1. Stream de áudio contínuo → Vosk detecta wake word offline
        2. Wake word detectada → captura próximo bloco de áudio
        3. Google STT transcreve o comando (fallback: Vosk)
        4. Retorna transcrição para o Orquestrador
    """

    SAMPLE_RATE = 16000
    BLOCK_SIZE  = 8000
    CHANNELS    = 1

    def __init__(
        self,
        wake_word:       str = "sexta feira",
        model_path:      str = "models/vosk-model-small-pt-0.3",
        language:        str = "pt-BR",
        command_timeout: int = 8,
    ):
        self.wake_word       = wake_word.lower()
        self.language        = language
        self.command_timeout = command_timeout

        self._audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()

        self._model = self._load_model(model_path)

        self._sr_recognizer = sr.Recognizer()
        self._sr_mic        = sr.Microphone(sample_rate=self.SAMPLE_RATE)
        self._calibrate()

        logger.info(f"Listener pronto | wake word: '{self.wake_word}' | modelo: {model_path}")

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
        with self._sr_mic as source:
            self._sr_recognizer.adjust_for_ambient_noise(source, duration=1.5)
        logger.info("Calibração concluída.")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"[Audio] {status}")
        self._audio_queue.put(bytes(indata))

    def _contains_wake_word(self, text: str) -> bool:
        return self.wake_word in text.lower()

    def _listen_for_wake_word(self) -> bool:
        logger.info(f"Aguardando wake word: '{self.wake_word}'...")

        with sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.BLOCK_SIZE,
            dtype="int16",
            channels=self.CHANNELS,
            callback=self._audio_callback,
        ):
            rec = KaldiRecognizer(self._model, self.SAMPLE_RATE)

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
                        return True
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    if self._contains_wake_word(partial):
                        rec.Result()
                        logger.info("Wake word detectada (parcial)!")
                        return True

        return False

    def _capture_command_google(self) -> str | None:
        logger.info("Escutando comando...")
        with self._sr_mic as source:
            try:
                audio = self._sr_recognizer.listen(
                    source,
                    timeout=3,
                    phrase_time_limit=self.command_timeout
                )
            except sr.WaitTimeoutError:
                logger.warning("Timeout aguardando comando.")
                return None

        try:
            texto = self._sr_recognizer.recognize_google(audio, language=self.language)
            return texto.lower().strip()
        except sr.UnknownValueError:
            logger.debug("Comando não compreendido.")
            return None
        except sr.RequestError:
            logger.warning("Google STT indisponível. Usando Vosk como fallback...")
            return self._capture_command_vosk(audio)

    def _capture_command_vosk(self, audio: sr.AudioData) -> str | None:
        rec  = KaldiRecognizer(self._model, self.SAMPLE_RATE)
        raw  = audio.get_raw_data(convert_rate=self.SAMPLE_RATE, convert_width=2)
        chunk = 4000
        for i in range(0, len(raw), chunk):
            rec.AcceptWaveform(raw[i:i+chunk])
        result = json.loads(rec.FinalResult())
        texto  = result.get("text", "").strip()
        return texto if texto else None

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