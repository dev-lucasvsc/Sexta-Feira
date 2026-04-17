# Sexta-Feira v2.0 — Assistente Virtual Local

Assistente virtual de desktop com wake word offline, voz neural PT-BR, integração com Obsidian, LLM dual (Claude API + Ollama), controle do SO, visão computacional, Spotify, Google Calendar, notificações nativas e interface holográfica via WebSocket.

---

## Estrutura de Arquivos

```
D:\jarvis\
│
├── main.py                         # Ponto de entrada — execute este
├── config.py                       # Todas as configurações centralizadas
├── requirements.txt                # Dependências Python
├── ws_server.py                    # Servidor WebSocket (Python ↔ interface.html)
├── interface.html                  # Interface holográfica (abre no browser)
├── .env                            # Variáveis sensíveis (não versionar)
│
├── core/                           # Módulos do assistente
│   ├── __init__.py
│   │
│   │   # — Entrada / Saída —
│   ├── listener.py                 # Wake word offline (Vosk) + STT (Google)
│   ├── speaker.py                  # TTS neural PT-BR (Edge TTS + pygame)
│   │
│   │   # — Inteligência —
│   ├── orchestrator.py             # Cérebro central — orquestra tudo
│   ├── intent_parser.py            # Interpreta comandos → ações locais
│   │
│   │   # — Memória —
│   ├── memory.py                   # Leitura + hot-reload do vault Obsidian
│   ├── obsidian_writer.py          # Escrita de notas/tarefas no Obsidian
│   ├── session_memory.py           # Histórico da sessão atual (RAM)
│   ├── history.py                  # Histórico persistente (SQLite)
│   │
│   │   # — Automação —
│   ├── automation.py               # Controle do SO (apps, volume, shell)
│   ├── file_manager.py             # Gerenciar arquivos e pastas
│   ├── window_manager.py           # Controlar janelas (minimizar, focar, snap)
│   ├── screen_vision.py            # Captura de tela + análise pelo LLM
│   │
│   │   # — Serviços Externos —
│   ├── spotify.py                  # Controle do Spotify via Web API
│   ├── calendar_manager.py         # Google Calendar (consulta de eventos)
│   │
│   │   # — Interface / UX —
│   ├── interface_bridge.py         # Envia estados ao WebSocket
│   ├── notifier.py                 # Notificações toast nativas do Windows
│   ├── reminder.py                 # Lembretes com timer por voz
│   └── command_logger.py           # Log de comandos em arquivo .txt
│
├── models/                         # Modelos de IA locais
│   └── vosk-model-small-pt-0.3/   # Modelo de wake word offline (Vosk)
│
├── data/                           # Dados gerados em tempo de execução
│   ├── history.db                  # Banco SQLite de conversas
│   ├── screenshots/                # Screenshots capturados pela visão
│   ├── spotify_token.json          # Token OAuth2 do Spotify (gerado automaticamente)
│   ├── google_credentials.json     # Credenciais OAuth2 do Google (você baixa)
│   └── google_token.json           # Token OAuth2 do Google (gerado automaticamente)
│
├── logs/                           # Logs de comandos por data
│   └── sexta_YYYY-MM-DD.txt        # Um arquivo por dia
│
└── assets/                         # Recursos estáticos (opcional)
    └── icon.ico                    # Ícone para notificações toast
```

---

## Pré-requisitos

### Python 3.12.x — obrigatório

Python 3.13+ e 3.14 não são suportados pelo PyAudio e Vosk.

1. Baixe em: https://www.python.org/downloads/release/python-3120/
2. No instalador, marque **"Add Python to PATH"**
3. Desative os atalhos da Microsoft Store:
   - Configurações → Aplicativos → Aliases de execução → desative `python.exe` e `python3.exe`
4. Libere caminhos longos:
   - Abra o instalador novamente → clique em **"Disable path length limit"**

---

## Instalação

### 1. Instale as dependências

```bash
python -m pip install -r requirements.txt
python -m pip install --upgrade SpeechRecognition setuptools
```

### 2. Modelo Vosk PT-BR (wake word offline)

Baixe e extraia em `D:\jarvis\models\`:
```
https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
```

Resultado:
```
D:\jarvis\models\vosk-model-small-pt-0.3\
```

### 3. Ollama (LLM local gratuito)

Baixe em: https://ollama.com/download

```bash
ollama pull llama3.2
```

---

## Configuração

### Arquivo `.env` (crie na raiz do projeto)

```env
JARVIS_VAULT_PATH="C:/Users/Lucas/OneDrive/Documentos/Obsidian Vault"
ANTHROPIC_API_KEY=sk-ant-...
WEATHER_API_KEY=sua_chave_openweathermap
SPOTIFY_CLIENT_ID=seu_client_id
SPOTIFY_CLIENT_SECRET=seu_client_secret
```

> Use sempre barras `/` nos caminhos — barras invertidas causam SyntaxError no Python.

### Arquivo `config.py` — principais ajustes

```python
OBSIDIAN_VAULT_PATH = "C:/Users/Lucas/OneDrive/Documentos/Obsidian Vault"
WAKE_WORD           = "sexta"
LLM_PROVIDER        = "ollama"     # "claude" | "ollama" | "none"
TTS_VOICE           = "antonio"    # voz masculina PT-BR
TTS_PITCH           = "-4Hz"       # tom mais grave
WEATHER_CITY        = "Brasilia"
PERSONALITY_TONE    = "casual"     # "formal" | "casual" | "técnico" | "conciso"
```

### VS Code — interpretador correto

`Ctrl+Shift+P` → `Python: Select Interpreter` → Python 3.12.0

---

## Como Executar

**Terminal 1 — Servidor WebSocket:**
```bash
python ws_server.py
```

**Terminal 2 — Sexta-Feira:**
```bash
python main.py
```

O browser abre automaticamente com a interface holográfica e conecta ao servidor.

---

## Fluxo Completo

```
Microfone
    ↓
Vosk detecta "sexta" (offline, sem internet)
    ↓
Google STT transcreve o comando completo
    ↓
Orchestrator processa em cascata:

    1. Hora / data?          → resposta imediata (stdlib)
    2. Clima?                → OpenWeatherMap API
    3. Tela?                 → ScreenVision (PIL + Claude Vision)
    4. Calendário?           → Google Calendar API
    5. Intenção local?       → IntentParser (apps, sites, janelas, Spotify...)
    6. LLM?                  → Ollama local ou Claude API
                               (com contexto do Obsidian + histórico SQLite)

    ↓
┌─────────────┬──────────────────┬───────────────────┬──────────────┐
│  Edge TTS   │  interface.html  │  OSAutomation /   │  Notifier    │
│  (voz PT-BR)│  (orbe reativa)  │  WindowManager    │  (toast)     │
└─────────────┴──────────────────┴───────────────────┴──────────────┘
    ↓
CommandLogger → logs/sexta_YYYY-MM-DD.txt
History       → data/history.db
```

---

## Módulos e Funcionalidades

### Entrada / Saída
| Módulo | Função |
|---|---|
| `listener.py` | Wake word offline (Vosk) + transcrição (Google STT) |
| `speaker.py` | Síntese de voz neural PT-BR (Edge TTS) |

### Inteligência
| Módulo | Função |
|---|---|
| `orchestrator.py` | Cérebro central — orquestra todos os módulos |
| `intent_parser.py` | 15+ intenções locais sem LLM |

### Memória
| Módulo | Função |
|---|---|
| `memory.py` | Lê e indexa notas do Obsidian com hot-reload |
| `obsidian_writer.py` | Cria notas, tarefas e entradas de diário |
| `session_memory.py` | Histórico da sessão atual (RAM) |
| `history.py` | Histórico persistente entre sessões (SQLite) |

### Automação
| Módulo | Função |
|---|---|
| `automation.py` | Abre/fecha apps, volume, shell, lock, shutdown |
| `file_manager.py` | Organiza, move, busca e cria pastas/arquivos |
| `window_manager.py` | Minimiza, maximiza, foca, snap de janelas |
| `screen_vision.py` | Captura tela e analisa com Claude Vision |

### Serviços Externos
| Módulo | Função |
|---|---|
| `spotify.py` | Play, pause, next, volume, shuffle via Web API |
| `calendar_manager.py` | Consulta eventos do Google Calendar |

### Interface / UX
| Módulo | Função |
|---|---|
| `interface_bridge.py` | WebSocket → interface holográfica |
| `notifier.py` | Toast notifications nativas do Windows |
| `reminder.py` | Lembretes com timer disparados por voz |
| `command_logger.py` | Log de comandos em arquivo .txt diário |

---

## Comandos de Voz

### Sistema
| Comando | Ação |
|---|---|
| "abrir chrome" | Abre o Chrome |
| "fechar spotify" | Fecha o processo |
| "volume 60" | Ajusta volume para 60% |
| "bloquear tela" | Bloqueia o Windows |
| "desligar computador" | Desliga em 30s |
| "tirar print" | Captura de tela |

### Janelas
| Comando | Ação |
|---|---|
| "minimizar tudo" | Mostra área de trabalho |
| "maximizar janela" | Maximiza a janela atual |
| "fechar janela" | Fecha a janela em foco |
| "focar no VS Code" | Coloca VS Code em foco |
| "mover janela pra esquerda" | Snap left |
| "alternar janela" | Alt+Tab |
| "listar janelas abertas" | Lista o que está aberto |

### Arquivos
| Comando | Ação |
|---|---|
| "organizar downloads" | Separa por tipo (Imagens, Docs, Vídeos...) |
| "criar pasta Projetos" | Cria na área de trabalho |
| "buscar arquivo relatório" | Busca por nome |

### Obsidian
| Comando | Ação |
|---|---|
| "anota que preciso revisar o projeto" | Adiciona ao diário do dia |
| "criar tarefa comprar café" | Cria tarefa com checkbox |
| "criar nota Reunião de quinta" | Cria nota nova |

### Spotify
| Comando | Ação |
|---|---|
| "toca jazz no Spotify" | Busca e toca |
| "pausar" | Pausa |
| "próxima" | Próxima faixa |
| "o que está tocando" | Informa a música atual |
| "modo aleatório" | Shuffle on/off |

### Informações
| Comando | Ação |
|---|---|
| "que horas são" | Hora atual |
| "que dia é hoje" | Data completa |
| "como está o clima" | Temperatura e condição |
| "o que tenho hoje" | Eventos do Google Calendar |
| "próximo evento" | Próximo compromisso |
| "o que tem na tela" | Análise visual da tela |
| "qual o erro na tela" | Identifica erros visíveis |

### Lembretes e Utilidades
| Comando | Ação |
|---|---|
| "me lembra em 30 minutos para tomar água" | Cria lembrete |
| "quais lembretes ativos" | Lista lembretes |
| "modo silencioso" | Desativa voz |
| "volta a falar" | Reativa voz |
| "se apresenta" | Apresentação completa |
| "notícias de hoje" | Abre Google Notícias |

---

## Setup de Serviços Externos

### Spotify
1. Acesse: https://developer.spotify.com/dashboard
2. Crie um app → copie Client ID e Client Secret
3. Em "Redirect URIs" adicione: `http://localhost:8888/callback`
4. Configure no `.env`: `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`
5. Execute uma vez para autorizar:
```bash
python -c "from core.spotify import SpotifyController; SpotifyController('ID','SECRET').authorize()"
```

### Google Calendar
1. Acesse: https://console.cloud.google.com
2. Crie um projeto → ative a **Google Calendar API**
3. Crie credenciais OAuth2 (tipo: **Desktop App**)
4. Baixe o JSON → salve como: `data/google_credentials.json`
5. Execute uma vez para autorizar:
```bash
python -c "from core.calendar_manager import CalendarManager; CalendarManager().authorize()"
```

### OpenWeatherMap (clima)
1. Crie conta em: https://openweathermap.org/api
2. Gere uma API key gratuita (1.000 chamadas/dia)
3. Configure no `.env`: `WEATHER_API_KEY=sua_chave`

### Claude API (LLM)
1. Acesse: https://console.anthropic.com
2. Gere uma API key (mínimo $5 de crédito)
3. Configure no `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. No `config.py`: `LLM_PROVIDER = "claude"`

---

## Problemas Comuns

| Erro | Causa | Solução |
|---|---|---|
| PyAudio não instala | Python 3.13/3.14 | Use Python 3.12.x |
| SyntaxError unicodeescape | Barra invertida no caminho | Use `/` nos caminhos |
| distutils not found | Python 3.12 removeu distutils | `pip install --upgrade setuptools` |
| Pylance com avisos amarelos | Interpretador errado no VS Code | Ctrl+Shift+P → Select Interpreter → 3.12 |
| Modelo Vosk não encontrado | Caminho errado | Verifique `VOSK_MODEL_PATH` no config.py |
| Interface não conecta | ws_server.py não está rodando | Inicie Terminal 1 primeiro |
| websockets não encontrado | Não estava no requirements original | `pip install websockets` |
| Spotify "sem token" | Autorização não feita | Execute o comando de authorize() |
| Calendar "credenciais não encontradas" | JSON não está em data/ | Baixe do Google Console e renomeie |