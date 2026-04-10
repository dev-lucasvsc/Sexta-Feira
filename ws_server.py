"""
JARVIS v2.0 - Servidor WebSocket
=================================
Ponte entre o core Python (orchestrator.py) e a interface holográfica (interface.html).

Execute em terminal separado ANTES do main.py:
    python ws_server.py

Fluxo:
    orchestrator.py  →  [WebSocket :5005]  →  interface.html

Requer:
    pip install websockets
"""

import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("WSServer")

HOST = "localhost"
PORT = 5005

# Clientes conectados (suporta múltiplos — ex: vários monitores)
CLIENTS: set[WebSocketServerProtocol] = set()


async def broadcast(message: str):
    """Reenvia mensagem do Python para todos os clientes HTML conectados."""
    if not CLIENTS:
        return
    await asyncio.gather(*[c.send(message) for c in CLIENTS], return_exceptions=True)


async def handler(ws: WebSocketServerProtocol):
    """
    Gerencia uma conexão WebSocket.

    Detecta automaticamente quem conectou:
    - Se mandar JSON com 'estado' → é o orchestrator.py → broadcast para interfaces HTML
    - Se não mandar nada logo → é o interface.html → registra como viewer
    """
    CLIENTS.add(ws)
    remote = ws.remote_address
    logger.info(f"Cliente conectado: {remote} | total: {len(CLIENTS)}")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                estado = data.get("estado", "?")
                logger.info(f"[ESTADO] {estado.upper()} | de: {remote}")
                # Reenvia para todos os outros clientes (as interfaces HTML)
                targets = [c for c in CLIENTS if c != ws]
                if targets:
                    await asyncio.gather(*[c.send(raw) for c in targets], return_exceptions=True)
            except json.JSONDecodeError:
                logger.warning(f"Mensagem inválida de {remote}: {raw[:60]}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(ws)
        logger.info(f"Cliente desconectado: {remote} | restantes: {len(CLIENTS)}")


async def main():
    logger.info(f"Servidor WebSocket rodando em ws://{HOST}:{PORT}")
    logger.info("Aguardando conexões do orchestrator.py e do interface.html...")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor encerrado.")