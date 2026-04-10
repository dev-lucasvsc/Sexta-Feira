"""
Sexta-Feira v2.0 - Ponto de Entrada Principal
=========================================
Execute este arquivo para iniciar o assistente:
    python main.py
"""

import os
import time
import webbrowser
from pathlib import Path
from config import Config
from core.orchestrator import SextaFeiraOrchestrator


def main():
    # Abre a interface holográfica no browser automaticamente
    interface_path = Path(__file__).parent / "interface.html"
    if interface_path.exists():
        webbrowser.open(interface_path.as_uri())
        time.sleep(1.5)  # aguarda o browser abrir antes de iniciar a Sexta-Feira

    sexta = SextaFeiraOrchestrator(
        obsidian_vault_path=Config.OBSIDIAN_VAULT_PATH,
        interface_host=Config.INTERFACE_HOST,
        interface_port=Config.INTERFACE_PORT
    )
    sexta.start()


if __name__ == "__main__":
    main()