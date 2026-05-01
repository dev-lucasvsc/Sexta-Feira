"""
Sexta-Feira v2.0 - Módulo de Visão Computacional
=================================================
Captura a tela e envia para o LLaVA (via Ollama) analisar o conteúdo visual.
100% offline, sem limite de requisições, sem custo.

Modelo usado: llava:7b
Para baixar: ollama pull llava:7b

Comandos de voz suportados:
    "o que tem na minha tela?"
    "resume o que está aberto"
    "qual é o erro na tela?"
    "lê o texto da tela pra mim"

Requer:
    pip install pillow
    ollama pull llava:7b
"""

import base64
import logging
import requests
from datetime import datetime
from pathlib import Path
from io import BytesIO

logger = logging.getLogger("ScreenVision")


class ScreenVision:
    """
    Captura e analisa o conteúdo visual da tela usando LLaVA via Ollama.
    Totalmente offline, sem custo e sem limite de requisições.
    """

    SCREENSHOT_DIR = "data/screenshots"
    MODEL          = "llava:7b"
    OLLAMA_URL     = "http://localhost:11434/api/generate"

    def __init__(self, **kwargs):
        # Aceita qualquer kwargs para compatibilidade (ex: api_key do código antigo)
        Path(self.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

        # Tenta pegar URL do Ollama do config se disponível
        try:
            from config import Config
            base = getattr(Config, "OLLAMA_BASE_URL", "http://localhost:11434")
            self.OLLAMA_URL = f"{base}/api/generate"
        except Exception:
            pass

        self._check_ollama()

    # ------------------------------------------------------------------
    # Verificação do Ollama
    # ------------------------------------------------------------------

    def _check_ollama(self):
        """Verifica se o Ollama está rodando e o modelo LLaVA está disponível."""
        try:
            base = self.OLLAMA_URL.replace("/api/generate", "")
            r = requests.get(f"{base}/api/tags", timeout=5)
            modelos = [m["name"] for m in r.json().get("models", [])]

            if not any("llava" in m for m in modelos):
                logger.warning(
                    "[ScreenVision] Modelo LLaVA não encontrado. "
                    "Execute: ollama pull llava:7b"
                )
            else:
                logger.info(f"[ScreenVision] LLaVA pronto via Ollama | modelo: {self.MODEL}")

        except Exception as e:
            logger.warning(f"[ScreenVision] Ollama não acessível: {e}")

    # ------------------------------------------------------------------
    # Captura de tela
    # ------------------------------------------------------------------

    def capture(self, save: bool = False) -> bytes | None:
        """
        Captura a tela e retorna os bytes da imagem PNG.

        Args:
            save: Se True, salva o screenshot em disco.

        Returns:
            Bytes PNG da imagem, ou None em caso de erro.
        """
        try:
            from PIL import ImageGrab, Image

            img = ImageGrab.grab()

            # Reduz resolução para economizar memória — máximo 1280px de largura
            max_width = 1280
            if img.width > max_width:
                ratio  = max_width / img.width
                height = int(img.height * ratio)
                img    = img.resize((max_width, height), Image.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            img_bytes = buffer.getvalue()

            if save:
                ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = Path(self.SCREENSHOT_DIR) / f"screen_{ts}.png"
                path.write_bytes(img_bytes)
                logger.info(f"[ScreenVision] Screenshot salvo: {path}")

            logger.info(f"[ScreenVision] Captura realizada: {img.width}x{img.height}px")
            return img_bytes

        except ImportError:
            logger.error("[ScreenVision] Pillow não instalado. Execute: pip install pillow")
            return None
        except Exception as e:
            logger.error(f"[ScreenVision] Erro na captura: {e}")
            return None

    # ------------------------------------------------------------------
    # Análise com LLaVA
    # ------------------------------------------------------------------

    def analyze(self, pergunta: str = "O que está sendo exibido na tela?") -> tuple[bool, str]:
        """
        Captura a tela e envia para o LLaVA analisar.

        Args:
            pergunta: Instrução para o modelo sobre o que analisar.

        Returns:
            (sucesso, resposta_em_texto)
        """
        img_bytes = self.capture()
        if not img_bytes:
            return False, "Não consegui capturar a tela."

        # Converte para base64 (formato aceito pelo Ollama)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            f"Esta é uma captura de tela do meu computador pessoal. {pergunta} "
            "Descreva objetivamente o que está visível: aplicativos abertos, textos, "
            "janelas, erros ou qualquer elemento relevante na tela. "
            "Responda em português brasileiro, máximo 3 frases."
        )

        try:
            response = requests.post(
                self.OLLAMA_URL,
                json={
                    "model":  self.MODEL,
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                },
                timeout=60
            )
            response.raise_for_status()
            resposta = response.json().get("response", "").strip()

            if not resposta:
                return False, "O modelo não retornou uma resposta."

            logger.info(f"[ScreenVision] Análise concluída: {resposta[:80]}...")
            return True, resposta

        except requests.exceptions.ConnectionError:
            logger.error("[ScreenVision] Ollama não está rodando. Inicie com: ollama serve")
            return False, "O Ollama não está rodando. Inicie o serviço e tente novamente."
        except Exception as e:
            logger.error(f"[ScreenVision] Erro na análise LLaVA: {e}")
            return False, "Não consegui analisar o conteúdo da tela no momento."

    # ------------------------------------------------------------------
    # Atalhos semânticos
    # ------------------------------------------------------------------

    def read_screen_text(self) -> tuple[bool, str]:
        """Lê e resume o texto visível na tela."""
        return self.analyze("Leia e resuma o texto principal visível na tela.")

    def describe_screen(self) -> tuple[bool, str]:
        """Descreve o que está sendo exibido na tela."""
        return self.analyze("Descreva brevemente o que está sendo exibido na tela.")

    def find_error(self) -> tuple[bool, str]:
        """Identifica erros ou problemas visíveis na tela."""
        return self.analyze(
            "Existe algum erro, aviso ou problema visível na tela? "
            "Se sim, descreva o erro com detalhes. Se não, diga que a tela parece normal."
        )