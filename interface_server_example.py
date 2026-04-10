"""
JARVIS v2.0 - Servidor WebSocket para Interface Holográfica
===========================================================
Script auxiliar para testar a comunicação entre o core Python
e um motor gráfico externo (Three.js, Unity, etc.).

Execute em terminal separado ANTES de iniciar o main.py:
    python interface_server_example.py

O servidor escutará na porta 5005 e imprimirá todos os estados
enviados pelo JARVIS. Substitua o handler pela lógica do seu
motor gráfico em produção.
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("InterfaceServer")

HOST = "localhost"
PORT = 5005


async def handler(websocket):
    """Recebe e processa mensagens do JARVIS core."""
    logger.info(f"JARVIS conectado: {websocket.remote_address}")
    try:
        async for raw_message in websocket:
            try:
                data = json.loads(raw_message)
                estado = data.get("estado", "desconhecido")
                payload = data.get("payload", {})

                logger.info(f"[ESTADO] {estado.upper()}")

                if payload:
                    logger.info(f"[PAYLOAD] {json.dumps(payload, ensure_ascii=False, indent=2)}")

                # -------------------------------------------------------
                # AQUI: Adicione a lógica de renderização do seu motor gráfico
                # Exemplos:
                #   - Acionar animação no Three.js via JavaScript bridge
                #   - Enviar mensagem UDP para Unity
                #   - Atualizar DOM de uma interface web
                # -------------------------------------------------------

            except json.JSONDecodeError:
                logger.warning(f"Mensagem inválida recebida: {raw_message}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("Conexão com JARVIS encerrada.")


async def main():
    logger.info(f"Servidor WebSocket aguardando JARVIS em ws://{HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # Loop infinito


if __name__ == "__main__":
    # Requer: pip install websockets
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor encerrado.")
