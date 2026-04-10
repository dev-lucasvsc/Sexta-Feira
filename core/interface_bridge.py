"""
JARVIS v2.0 - Ponte de Comunicação com Interface Holográfica
============================================================
Envia o estado do assistente e dados para projeção via WebSocket (padrão)
ou UDP como fallback, permitindo integração com Unity, Three.js ou qualquer
motor gráfico que escute nesse canal.

Protocolo de mensagem (JSON):
{
    "estado": "standby" | "processando" | "ativo" | "erro",
    "timestamp": 1234567890.0,
    "payload": { ... }  # Dados adicionais para renderização
}
"""

import json
import time
import socket
import logging
import threading
from enum import Enum

logger = logging.getLogger("InterfaceBridge")


class EstadoInterface(str, Enum):
    STANDBY     = "standby"
    PROCESSANDO = "processando"
    ATIVO       = "ativo"
    ERRO        = "erro"


class InterfaceBridge:
    """
    Gerencia a comunicação bidirecional entre o core Python do JARVIS
    e o motor de interface holográfica externo.

    Suporta dois protocolos:
    - WebSocket (padrão, recomendado para Three.js/browser)
    - UDP (fallback, recomendado para Unity/latência ultra-baixa)
    
    Troca o protocolo via parâmetro `protocol` no construtor.
    """

    SUPPORTED_PROTOCOLS = ("websocket", "udp")

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5005,
        protocol: str = "websocket"
    ):
        """
        Args:
            host: Endereço do motor gráfico. Use 'localhost' para mesma máquina.
            port: Porta de escuta. Padrão: 5005.
            protocol: 'websocket' ou 'udp'.
        """
        if protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError(f"Protocolo inválido: '{protocol}'. Use: {self.SUPPORTED_PROTOCOLS}")

        self.host = host
        self.port = port
        self.protocol = protocol
        self._connected = False
        self._ws = None       # WebSocket connection (se websocket)
        self._udp_sock = None # UDP socket (se udp)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Conexão
    # ------------------------------------------------------------------

    def connect(self):
        """Estabelece a conexão com o motor gráfico."""
        if self.protocol == "websocket":
            self._connect_websocket()
        elif self.protocol == "udp":
            self._connect_udp()

    def _connect_websocket(self):
        """
        Conecta via WebSocket.
        Requer: pip install websocket-client
        """
        try:
            import websocket  # websocket-client
            ws_url = f"ws://{self.host}:{self.port}"
            self._ws = websocket.create_connection(ws_url, timeout=5)
            self._connected = True
            logger.info(f"[WebSocket] Conectado em {ws_url}")
        except ImportError:
            logger.error("websocket-client não instalado. Execute: pip install websocket-client")
            self._connected = False
        except Exception as e:
            logger.warning(f"[WebSocket] Falha na conexão: {e}. Rodando em modo desconectado.")
            self._connected = False

    def _connect_udp(self):
        """Cria o socket UDP (sem handshake — fire and forget)."""
        try:
            self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._connected = True
            logger.info(f"[UDP] Socket criado. Destino: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"[UDP] Erro ao criar socket: {e}")
            self._connected = False

    def disconnect(self):
        """Encerra a conexão de forma limpa."""
        if self.protocol == "websocket" and self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        elif self.protocol == "udp" and self._udp_sock:
            self._udp_sock.close()

        self._connected = False
        logger.info("[InterfaceBridge] Conexão encerrada.")

    # ------------------------------------------------------------------
    # Envio de estado
    # ------------------------------------------------------------------

    def send_state(self, estado: str, payload: dict | None = None):
        """
        Envia o estado atual e dados para o motor gráfico.

        Formato enviado (compatível com interface.html):
        {
            "estado": "speak" | "think" | "listen" | "idle" | "standby" | "erro",
            "timestamp": 1234567890.0,
            "payload": {
                "dados_para_projetar": { "conteudo": "..." }
            }
        }

        Args:
            estado: Estado da interface.
            payload: Dict com dados extras para renderização (opcional).
        """
        message = {
            "estado": estado,
            "timestamp": time.time(),
            "payload": payload or {}
        }

        serialized = json.dumps(message, ensure_ascii=False)
        logger.debug(f"[InterfaceBridge] Enviando: {serialized[:120]}...")

        if not self._connected:
            # Modo desconectado: apenas loga (útil para desenvolvimento)
            logger.info(f"[InterfaceBridge OFFLINE] Estado: {estado}")
            return

        with self._lock:
            if self.protocol == "websocket":
                self._send_websocket(serialized)
            elif self.protocol == "udp":
                self._send_udp(serialized)

    def _send_websocket(self, data: str):
        """Envia dados via WebSocket."""
        try:
            self._ws.send(data)
        except Exception as e:
            logger.error(f"[WebSocket] Erro ao enviar: {e}")
            self._connected = False
            logger.warning("[WebSocket] Conexão perdida. Tentando reconectar...")
            self._connect_websocket()

    def _send_udp(self, data: str):
        """Envia dados via UDP (datagrama)."""
        try:
            self._udp_sock.sendto(data.encode("utf-8"), (self.host, self.port))
        except Exception as e:
            logger.error(f"[UDP] Erro ao enviar: {e}")

    # ------------------------------------------------------------------
    # Helpers de estado pré-definidos
    # ------------------------------------------------------------------

    def set_standby(self):
        self.send_state(EstadoInterface.STANDBY)

    def set_processing(self, info: str = ""):
        self.send_state(EstadoInterface.PROCESSANDO, {"info": info})

    def set_active(self, dados: dict | None = None):
        self.send_state(EstadoInterface.ATIVO, dados)

    def set_error(self, mensagem: str = ""):
        self.send_state(EstadoInterface.ERRO, {"mensagem": mensagem})

    @property
    def is_connected(self) -> bool:
        return self._connected