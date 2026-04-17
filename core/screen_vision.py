"""
Sexta-Feira v2.0 - Módulo de Visão Computacional
=================================================
Captura a tela e envia para o LLM analisar o conteúdo visual.
Permite comandos como:
    "o que tem na minha tela?"
    "resume o que está aberto"
    "qual é o erro na tela?"
    "lê o texto da tela pra mim"

Requer:
    pip install pillow

Para análise com LLM multimodal (Claude claude-sonnet-4-20250514):
    Precisa de ANTHROPIC_API_KEY configurada no config.py.
"""

import base64
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from io import BytesIO

logger = logging.getLogger("ScreenVision")


class ScreenVision:
    """
    Captura e analisa o conteúdo visual da tela.
    Usa PIL para captura e Claude Vision para análise.
    """

    SCREENSHOT_DIR = "data/screenshots"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model   = model
        self._mock   = not api_key or api_key == "SUA_CHAVE_AQUI"

        Path(self.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

        if self._mock:
            logger.warning("[ScreenVision] API key não configurada. Modo MOCK ativo.")

    # ------------------------------------------------------------------
    # Captura de tela
    # ------------------------------------------------------------------

    def capture(self, monitor: int = 0, save: bool = False) -> bytes | None:
        """
        Captura a tela e retorna os bytes da imagem PNG.

        Args:
            monitor: Índice do monitor (0 = primário).
            save:    Se True, salva o screenshot em disco.

        Returns:
            Bytes PNG da imagem, ou None em caso de erro.
        """
        try:
            from PIL import ImageGrab, Image

            # Captura tela inteira
            img = ImageGrab.grab()

            # Reduz resolução para economizar tokens do LLM
            # Mantém proporção, limita ao máximo de 1280px de largura
            max_width = 1280
            if img.width > max_width:
                ratio  = max_width / img.width
                height = int(img.height * ratio)
                img    = img.resize((max_width, height), Image.LANCZOS)

            # Serializa para PNG em memória
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
    # Análise com LLM
    # ------------------------------------------------------------------

    def analyze(self, pergunta: str = "O que está sendo exibido na tela?") -> tuple[bool, str]:
        """
        Captura a tela e envia para o Claude analisar.

        Args:
            pergunta: Instrução para o LLM sobre o que analisar.

        Returns:
            (sucesso, resposta_em_texto)
        """
        if self._mock:
            return True, "Visão computacional ativa. Vejo sua tela com conteúdo em exibição."

        img_bytes = self.capture()
        if not img_bytes:
            return False, "Não consegui capturar a tela."

        try:
            import anthropic

            img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            client  = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": "image/png",
                                "data":       img_b64,
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                f"{pergunta}\n\n"
                                "Responda em português brasileiro, de forma concisa e direta. "
                                "Máximo 3 frases. Foque no conteúdo mais relevante visível."
                            )
                        }
                    ]
                }]
            )

            resposta = response.content[0].text.strip()
            logger.info(f"[ScreenVision] Análise concluída: {resposta[:80]}...")
            return True, resposta

        except Exception as e:
            logger.error(f"[ScreenVision] Erro na análise: {e}")
            return False, "Não consegui analisar o conteúdo da tela."

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
            "Se sim, descreva. Se não, diga que a tela parece normal."
        )