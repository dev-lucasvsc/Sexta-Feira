"""
Sexta-Feira v2.0 - Setup Automático
====================================
Instala todas as dependências e verifica a configuração.

Execute UMA VEZ após clonar o projeto:
    python setup.py

O que este script faz:
    1. Verifica a versão do Python
    2. Instala todas as dependências do requirements.txt
    3. Instala o pyttsx3 como fallback de voz
    4. Cria as pastas necessárias (data/, logs/, assets/)
    5. Roda o diagnóstico completo
    6. Orienta sobre os próximos passos
"""

import sys
import os
import subprocess
from pathlib import Path


def cor(c):
    cores = {"verde": "\033[92m", "amarelo": "\033[93m", "vermelho": "\033[91m",
             "azul": "\033[94m", "bold": "\033[1m", "reset": "\033[0m"}
    return cores.get(c, "")


def print_step(n, total, msg):
    print(f"\n{cor('bold')}[{n}/{total}] {msg}{cor('reset')}")


def run(cmd, desc=""):
    if desc:
        print(f"  → {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"  {cor('amarelo')}aviso: {result.stderr[:120]}{cor('reset')}")
    return result.returncode == 0


def main():
    print(f"""
{cor('bold')}{'='*55}
  Sexta-Feira v2.0 — Setup Automático
{'='*55}{cor('reset')}""")

    total = 6

    # 1. Verifica Python
    print_step(1, total, "Verificando Python")
    v = sys.version_info
    if v.major != 3 or v.minor < 12:
        print(f"  {cor('vermelho')}Python {v.major}.{v.minor} detectado.")
        print(f"  Este projeto requer Python 3.12.x")
        print(f"  Baixe em: https://www.python.org/downloads/release/python-3120/{cor('reset')}")
        sys.exit(1)
    print(f"  {cor('verde')}Python {v.major}.{v.minor}.{v.micro} — OK{cor('reset')}")

    # 2. Atualiza pip
    print_step(2, total, "Atualizando pip e setuptools")
    run(f'"{sys.executable}" -m pip install --upgrade pip setuptools --quiet',
        "atualizando pip...")

    # 3. Instala dependências principais
    print_step(3, total, "Instalando dependências principais")
    deps_essenciais = [
        ("edge-tts",           "TTS neural (voz)"),
        ("pygame==2.6.1",      "reprodução de áudio"),
        ("pyttsx3",            "voz offline (fallback)"),
        ("SpeechRecognition",  "reconhecimento de voz"),
        ("vosk==0.3.45",       "wake word offline"),
        ("sounddevice==0.4.6", "captura de áudio"),
        ("requests==2.31.0",   "requisições HTTP"),
        ("websockets==12.0",   "WebSocket servidor"),
        ("websocket-client",   "WebSocket cliente"),
        ("python-dotenv",      "variáveis de ambiente"),
        ("watchdog==4.0.0",    "hot-reload Obsidian"),
    ]

    for pkg, desc in deps_essenciais:
        ok = run(f'"{sys.executable}" -m pip install {pkg} --quiet')
        status = f"{cor('verde')}✓{cor('reset')}" if ok else f"{cor('amarelo')}⚠{cor('reset')}"
        print(f"  {status} {desc} ({pkg})")

    # 4. Instala dependências opcionais
    print_step(4, total, "Instalando dependências opcionais")
    deps_opcionais = [
        ("pillow",            "visão computacional"),
        ("pygetwindow",       "controle de janelas"),
        ("pyautogui",         "automação de janelas"),
        ("win10toast",        "notificações Windows"),
        ("anthropic",         "Claude API"),
    ]

    for pkg, desc in deps_opcionais:
        ok = run(f'"{sys.executable}" -m pip install {pkg} --quiet')
        status = f"{cor('verde')}✓{cor('reset')}" if ok else f"{cor('amarelo')}⚠{cor('reset')}"
        print(f"  {status} {desc} ({pkg}) {'— opcional, pode instalar depois' if not ok else ''}")

    # PyAudio separado (pode precisar de passos extras no Windows)
    print(f"  → instalando PyAudio...")
    ok_pyaudio = run(f'"{sys.executable}" -m pip install pyaudio --quiet')
    if not ok_pyaudio:
        print(f"  {cor('amarelo')}⚠ PyAudio falhou. Tente manualmente:{cor('reset')}")
        print(f"     pip install pipwin && pipwin install pyaudio")

    # 5. Cria pastas
    print_step(5, total, "Criando estrutura de pastas")
    pastas = ["data", "logs", "assets", "models", "data/screenshots"]
    for pasta in pastas:
        Path(pasta).mkdir(parents=True, exist_ok=True)
        print(f"  {cor('verde')}✓{cor('reset')} {pasta}/")

    # 6. Diagnóstico final
    print_step(6, total, "Rodando diagnóstico")
    if Path("diagnostico.py").exists():
        subprocess.run([sys.executable, "diagnostico.py"])
    else:
        print(f"  {cor('amarelo')}diagnostico.py não encontrado{cor('reset')}")

    # Próximos passos
    print(f"""
{cor('bold')}{'='*55}
  Próximos passos:
{'='*55}{cor('reset')}

  1. {cor('bold')}Configure o config.py:{cor('reset')}
     - OBSIDIAN_VAULT_PATH = seu vault
     - LLM_PROVIDER = "ollama" (gratuito) ou "claude"
     - WEATHER_CITY = sua cidade

  2. {cor('bold')}Baixe o modelo Vosk PT-BR:{cor('reset')}
     https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
     Extraia em: models/vosk-model-small-pt-0.3/

  3. {cor('bold')}Instale o Ollama (LLM gratuito):{cor('reset')}
     https://ollama.com/download
     Depois: ollama pull llama3.2

  4. {cor('bold')}Teste sem microfone:{cor('reset')}
     python teste.py

  5. {cor('bold')}Inicie o sistema:{cor('reset')}
     Terminal 1: python ws_server.py
     Terminal 2: python main.py

{cor('verde')}Setup concluído!{cor('reset')}
""")


if __name__ == "__main__":
    main()