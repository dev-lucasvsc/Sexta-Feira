"""
setup_spotify.py - Autorização do Spotify (execute uma única vez)
=================================================================
Execute este arquivo para autorizar a Sexta-Feira a controlar o Spotify.

    python setup_spotify.py

O que acontece:
    1. Abre o browser na página de autorização do Spotify
    2. Você faz login e clica em "Autorizar"
    3. O Spotify redireciona para 127.0.0.1:8888/callback?code=...
    4. O browser mostra "página não encontrada" — isso é NORMAL
    5. Você copia a URL completa da barra de endereços e cola aqui
    6. Token salvo em data/spotify_token/.cache
"""

import sys
import os

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.spotify import SpotifyController

if Config.SPOTIFY_CLIENT_ID == "SEU_CLIENT_ID":
    print("\n[ERRO] Configure SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET no config.py primeiro.\n")
    sys.exit(1)

print("=" * 60)
print("  Sexta-Feira — Autorização do Spotify")
print("=" * 60)

controller = SpotifyController(
    client_id=Config.SPOTIFY_CLIENT_ID,
    client_secret=Config.SPOTIFY_CLIENT_SECRET,
)

ok = controller.authorize()

if ok:
    print("\n✓ Spotify autorizado com sucesso!")
    print("  Agora pode rodar o main.py normalmente.\n")
else:
    print("\n✗ Falha na autorização. Verifique as credenciais e tente novamente.\n")