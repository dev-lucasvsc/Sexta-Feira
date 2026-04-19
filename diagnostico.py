"""
Sexta-Feira v2.0 - Diagnóstico do Sistema
==========================================
Verifica todos os módulos e dependências antes de iniciar.
Roda automaticamente no boot e identifica problemas antes que causem falhas.

Uso:
    python diagnostico.py          # roda o diagnóstico completo
    python diagnostico.py --fix    # tenta corrigir problemas automaticamente
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path


class Cor:
    OK     = "\033[92m"  # verde
    WARN   = "\033[93m"  # amarelo
    ERRO   = "\033[91m"  # vermelho
    INFO   = "\033[94m"  # azul
    RESET  = "\033[0m"
    BOLD   = "\033[1m"


def ok(msg):    print(f"  {Cor.OK}✓{Cor.RESET} {msg}")
def warn(msg):  print(f"  {Cor.WARN}⚠{Cor.RESET} {msg}")
def erro(msg):  print(f"  {Cor.ERRO}✗{Cor.RESET} {msg}")
def info(msg):  print(f"  {Cor.INFO}→{Cor.RESET} {msg}")
def titulo(msg): print(f"\n{Cor.BOLD}{msg}{Cor.RESET}")


# ─── Resultados ──────────────────────────────────────────────────────────────
resultados = {"ok": 0, "warn": 0, "erro": 0}

def ck(condicao, msg_ok, msg_erro, critico=False):
    if condicao:
        ok(msg_ok)
        resultados["ok"] += 1
        return True
    else:
        if critico:
            erro(msg_erro)
            resultados["erro"] += 1
        else:
            warn(msg_erro)
            resultados["warn"] += 1
        return False


# ─── Verificações ─────────────────────────────────────────────────────────────

def check_python():
    titulo("Python")
    v = sys.version_info
    ck(v.major == 3 and v.minor == 12,
       f"Python {v.major}.{v.minor}.{v.micro} — versão correta",
       f"Python {v.major}.{v.minor}.{v.micro} — recomendado 3.12.x",
       critico=False)


def check_config():
    titulo("Configuração")
    config_path = Path("config.py")
    if not ck(config_path.exists(), "config.py encontrado", "config.py AUSENTE — crie na raiz do projeto", critico=True):
        return

    try:
        sys.path.insert(0, str(Path.cwd()))
        from config import Config

        vault = Path(Config.OBSIDIAN_VAULT_PATH)
        ck(vault.exists(),
           f"Vault Obsidian encontrado: {Config.OBSIDIAN_VAULT_PATH}",
           f"Vault Obsidian não encontrado: {Config.OBSIDIAN_VAULT_PATH}")

        ck(Config.WAKE_WORD.strip() != "",
           f"Wake word configurada: '{Config.WAKE_WORD}'",
           "Wake word vazia no config.py")

        ck(Config.LLM_PROVIDER in ("claude", "ollama", "none"),
           f"LLM provider: {Config.LLM_PROVIDER}",
           f"LLM provider inválido: {Config.LLM_PROVIDER}")

        if Config.LLM_PROVIDER == "claude":
            ck(Config.ANTHROPIC_API_KEY != "SUA_CHAVE_AQUI",
               "Anthropic API key configurada",
               "Anthropic API key não configurada (LLM_PROVIDER = 'claude' mas sem chave)")

        if Config.LLM_PROVIDER == "ollama":
            try:
                import requests
                r = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=3)
                ck(r.ok, f"Ollama respondendo em {Config.OLLAMA_BASE_URL}", f"Ollama não responde em {Config.OLLAMA_BASE_URL}")
            except Exception:
                warn(f"Ollama não está rodando em {Config.OLLAMA_BASE_URL} — inicie com: ollama serve")
                resultados["warn"] += 1

    except Exception as e:
        erro(f"Erro ao carregar config.py: {e}")
        resultados["erro"] += 1


def check_vosk():
    titulo("Vosk (Wake Word offline)")
    try:
        sys.path.insert(0, str(Path.cwd()))
        from config import Config
        model_path = Path(Config.VOSK_MODEL_PATH)
    except Exception:
        model_path = Path("models/vosk-model-small-pt-0.3")

    ck(model_path.exists(),
       f"Modelo Vosk encontrado: {model_path}",
       f"Modelo Vosk NÃO encontrado em: {model_path}\n"
       f"    Baixe em: https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
       critico=True)

    pkg_ok = ck(_pkg("vosk"), "vosk instalado", "vosk não instalado — pip install vosk", critico=True)
    _pkg_ck("sounddevice", "sounddevice instalado", "sounddevice não instalado — pip install sounddevice")
    _pkg_ck("speech_recognition", "SpeechRecognition instalado", "SpeechRecognition não instalado")
    _pkg_ck("pyaudio", "PyAudio instalado", "PyAudio não instalado — pip install pyaudio")


def check_tts():
    titulo("Text-to-Speech (edge-tts)")
    _pkg_ck("edge_tts", "edge-tts instalado", "edge-tts não instalado — pip install edge-tts")
    _pkg_ck("pygame", "pygame instalado", "pygame não instalado — pip install pygame")
    _pkg_ck("pyttsx3", "pyttsx3 instalado (fallback offline)", "pyttsx3 não instalado — pip install pyttsx3 (recomendado para fallback)")

    # Testa edge-tts CLI
    try:
        r = subprocess.run(["edge-tts", "--help"], capture_output=True, timeout=5)
        ck(r.returncode == 0, "edge-tts CLI disponível no PATH", "edge-tts CLI não encontrado no PATH")
    except FileNotFoundError:
        warn("edge-tts CLI não encontrado — adicione o Python Scripts ao PATH")
        resultados["warn"] += 1


def check_internet():
    titulo("Conectividade")
    try:
        import urllib.request
        urllib.request.urlopen("https://speech.platform.bing.com", timeout=5)
        ok("speech.platform.bing.com acessível — edge-tts vai funcionar")
        resultados["ok"] += 1
    except Exception:
        warn("speech.platform.bing.com inacessível — edge-tts pode falhar, pyttsx3 será usado como fallback")
        resultados["warn"] += 1

    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        ok("Internet disponível")
        resultados["ok"] += 1
    except Exception:
        warn("Sem internet — STT e LLM cloud não vão funcionar")
        resultados["warn"] += 1


def check_websocket():
    titulo("WebSocket (Interface Holográfica)")
    _pkg_ck("websockets", "websockets instalado", "websockets não instalado — pip install websockets")
    _pkg_ck("websocket", "websocket-client instalado", "websocket-client não instalado — pip install websocket-client")

    # Testa se ws_server está acessível
    try:
        import socket
        s = socket.create_connection(("localhost", 5005), timeout=1)
        s.close()
        ok("ws_server.py rodando na porta 5005")
        resultados["ok"] += 1
    except Exception:
        warn("ws_server.py não está rodando — inicie com: python ws_server.py")
        resultados["warn"] += 1


def check_modulos():
    titulo("Módulos do Projeto")
    modulos = [
        ("core.orchestrator",    "Orquestrador"),
        ("core.listener",        "Listener (Vosk + STT)"),
        ("core.speaker",         "Speaker (TTS)"),
        ("core.intent_parser",   "Intent Parser"),
        ("core.memory",          "Memória Obsidian"),
        ("core.automation",      "Automação SO"),
        ("core.file_manager",    "Gerenciador de Arquivos"),
        ("core.window_manager",  "Gerenciador de Janelas"),
        ("core.reminder",        "Lembretes"),
        ("core.history",         "Histórico SQLite"),
        ("core.session_memory",  "Memória de Sessão"),
        ("core.command_logger",  "Logger de Comandos"),
        ("core.notifier",        "Notificações"),
        ("core.spotify",         "Spotify"),
        ("core.calendar_manager","Google Calendar"),
        ("core.screen_vision",   "Visão Computacional"),
        ("core.obsidian_writer", "Escrita Obsidian"),
        ("core.interface_bridge","Interface Bridge"),
    ]

    sys.path.insert(0, str(Path.cwd()))
    for mod, nome in modulos:
        try:
            importlib.import_module(mod)
            ok(f"{nome}")
            resultados["ok"] += 1
        except ImportError as e:
            warn(f"{nome} — import falhou: {str(e)[:60]}")
            resultados["warn"] += 1
        except Exception as e:
            warn(f"{nome} — erro ao carregar: {str(e)[:60]}")
            resultados["warn"] += 1


def check_pastas():
    titulo("Estrutura de Pastas")
    pastas = [
        ("core/",   "Módulos Python"),
        ("models/", "Modelos de IA"),
        ("data/",   "Dados gerados"),
        ("logs/",   "Logs de sessão"),
    ]
    for pasta, desc in pastas:
        p = Path(pasta)
        existe = p.exists()
        if not existe and pasta in ("data/", "logs/"):
            p.mkdir(exist_ok=True)
            ok(f"{pasta} criada ({desc})")
            resultados["ok"] += 1
        else:
            ck(existe, f"{pasta} existe ({desc})", f"{pasta} não encontrada ({desc})")


def check_opcionais():
    titulo("Dependências Opcionais")
    _pkg_ck("PIL",          "Pillow instalado (visão computacional)", "Pillow não instalado — pip install pillow")
    _pkg_ck("pygetwindow",  "pygetwindow instalado (janelas)", "pygetwindow não instalado — pip install pygetwindow pyautogui")
    _pkg_ck("win10toast",   "win10toast instalado (notificações)", "win10toast não instalado — pip install win10toast")
    _pkg_ck("watchdog",     "watchdog instalado (hot-reload Obsidian)", "watchdog não instalado — pip install watchdog")
    _pkg_ck("anthropic",    "anthropic instalado (Claude API)", "anthropic não instalado — pip install anthropic")
    _pkg_ck("googleapiclient", "google-api-python-client instalado (Calendar)", "google-api instalado não instalado (opcional)")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pkg(nome):
    try:
        importlib.import_module(nome)
        return True
    except ImportError:
        return False

def _pkg_ck(nome, msg_ok, msg_erro, critico=False):
    return ck(_pkg(nome), msg_ok, msg_erro, critico=critico)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{Cor.BOLD}{'='*55}{Cor.RESET}")
    print(f"{Cor.BOLD}  Sexta-Feira v2.0 — Diagnóstico do Sistema{Cor.RESET}")
    print(f"{Cor.BOLD}{'='*55}{Cor.RESET}")

    check_python()
    check_pastas()
    check_config()
    check_vosk()
    check_tts()
    check_internet()
    check_websocket()
    check_modulos()
    check_opcionais()

    # Resumo
    print(f"\n{Cor.BOLD}{'='*55}{Cor.RESET}")
    total = sum(resultados.values())
    print(f"  {Cor.OK}✓ {resultados['ok']} OK{Cor.RESET}  "
          f"{Cor.WARN}⚠ {resultados['warn']} avisos{Cor.RESET}  "
          f"{Cor.ERRO}✗ {resultados['erro']} erros{Cor.RESET}")

    if resultados["erro"] > 0:
        print(f"\n  {Cor.ERRO}Sistema com erros críticos — corrija antes de iniciar.{Cor.RESET}")
        sys.exit(1)
    elif resultados["warn"] > 3:
        print(f"\n  {Cor.WARN}Sistema funcional mas com avisos. Verifique os itens acima.{Cor.RESET}")
    else:
        print(f"\n  {Cor.OK}Sistema pronto. Execute: python main.py{Cor.RESET}")

    print(f"{Cor.BOLD}{'='*55}{Cor.RESET}\n")


if __name__ == "__main__":
    main()