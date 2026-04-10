# Sexta-Feira — Assistente Virtual Local

Assistente virtual de desktop com wake word offline (Vosk), voz neural PT-BR (Edge TTS), integração com Obsidian como segundo cérebro, suporte a Claude API e Ollama local, automação do SO, SmartHome via SmartThings e interface holográfica via WebSocket.

---

## Estrutura do Projeto

```
Sexta-Feira/
│
├── main.py                         # Ponto de entrada — execute este
├── config.py                       # Todas as configurações centralizadas
├── requirements.txt                # Dependências Python
├── ws_server.py                    # Servidor WebSocket (ponte Python ↔ interface.html)
├── interface.html                  # Interface holográfica (abre no browser)
├── .env                            # Variáveis sensíveis (não versionar)
│
├── models/
│   └── vosk-model-small-pt-0.3/   # Modelo de voz offline (Vosk)
│
└── core/
    ├── __init__.py
    ├── orchestrator.py             # Cérebro central
    ├── listener.py                 # Wake word offline (Vosk) + STT (Google)
    ├── speaker.py                  # TTS neural PT-BR (Edge TTS)
    ├── memory.py                   # Obsidian (segundo cérebro)
    ├── automation.py               # Automação SO + SmartThings
    ├── interface_bridge.py         # Envia estados ao WebSocket
    └── intent_parser.py            # Interpreta comandos de voz → ações
```

---

## Pré-requisitos

### Python 3.12.x — obrigatório

Python 3.13+ e 3.14 não são suportados pelo PyAudio e Vosk.

1. Baixe em: https://www.python.org/downloads/release/python-3120/
2. No instalador, marque **"Add Python to PATH"**
3. Após instalar, desative os atalhos da Microsoft Store:
   - Configurações → Aplicativos → Aliases de execução de aplicativo
   - Desative `python.exe` e `python3.exe` da Store
4. Libere caminhos longos (mais de 260 caracteres):
   - Abra o instalador do Python novamente → clique em **"Disable path length limit"**

---

## Instalação

### 1. Instale as dependências

```bash
python -m pip install -r requirements.txt
python -m pip install --upgrade SpeechRecognition setuptools
```

> Se houver erro no `distutils` com Python 3.12, o segundo comando resolve.

### 2. Instale o modelo Vosk PT-BR (wake word offline)

Baixe e extraia em `D:\SextFeira\models\`:
```
https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
```

Resultado esperado:
```
D:\SextaFeira\models\vosk-model-small-pt-0.3\
```

### 3. Instale o Ollama (LLM local gratuito)

Baixe o instalador em: https://ollama.com/download

Após instalar, baixe o modelo:
```bash
ollama pull llama3.2
```

---

## Configuração

### Arquivo `.env` (crie na raiz do projeto)

```env
JARVIS_VAULT_PATH="C:/Users/Lucas/OneDrive/Documentos/Obsidian Vault"
SMARTTHINGS_TOKEN=seu_token_aqui
ANTHROPIC_API_KEY=sk-ant-...
```

> Use barras normais `/` no caminho — barras invertidas causam SyntaxError no Python.

### Arquivo `config.py`

```python
# Caminho do vault Obsidian
OBSIDIAN_VAULT_PATH = "C:/Users/Lucas/OneDrive/Documentos/Obsidian Vault"

# Provider do LLM — escolha um:
LLM_PROVIDER = "ollama"    # local, gratuito (recomendado para testes)
LLM_PROVIDER = "claude"    # API paga, melhor qualidade
LLM_PROVIDER = "none"      # só comandos locais, sem LLM

# Voz
TTS_VOICE = "antonio"      # masculina PT-BR
TTS_PITCH = "-4Hz"         # mais grave, estilo JARVIS
```

### VS Code — selecione o interpretador correto

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

O browser abre automaticamente com a interface holográfica.

---

## Fluxo de Funcionamento

```
Microfone → Vosk detecta "Sexta feira" (offline)
    ↓
Google STT transcreve o comando (fallback: Vosk)
    ↓
IntentParser tenta resolver localmente
    ↓ (se não resolver)
LLM processa com contexto do Obsidian
    ↓
┌──────────────┬──────────────────┬──────────────────┐
│  Edge TTS    │  interface.html  │  OSAutomation /  │
│  (voz PT-BR) │  (orbe reage)    │  SmartThings     │
└──────────────┴──────────────────┴──────────────────┘
```

---

## Comandos de Voz (sem LLM)

| Comando | Ação |
|---|---|
| "Sexta Feira, abrir chrome" | Abre o Chrome |
| "Sexta Feira, abrir vs code" | Abre o VS Code |
| "Sexta Feira, abrir youtube" | Abre youtube.com |
| "Sexta Feira, pesquisar python" | Pesquisa no Google |
| "Sexta Feira, fechar spotify" | Fecha o processo |
| "Sexta Feira, volume 60" | Ajusta volume para 60% |
| "Sexta Feira, bloquear tela" | Bloqueia o Windows |
| "Sexta Feira, desligar computador" | Desliga em 30s |
| "Sexta Feira, tirar print" | Captura de tela |
| "Sexta Feira, abrir downloads" | Abre pasta Downloads |
| "Sexta Feira, mostrar desktop" | Mostra área de trabalho |

Com LLM ativo, qualquer pergunta em linguagem natural é processada.

---

## Providers de LLM

### Ollama (gratuito, offline)
```python
LLM_PROVIDER = "ollama"
OLLAMA_MODEL  = "llama3.2"
```

### Claude API
```python
LLM_PROVIDER      = "claude"
ANTHROPIC_API_KEY = "sk-ant-..."
```
Custo estimado: ~$0.001 a $0.003 por interação. Com $5 tem ~1.500 a 5.000 interações.

---

## Problemas Comuns

| Erro | Causa | Solução |
|---|---|---|
| PyAudio não instala | Python 3.13/3.14 | Use Python 3.12.x |
| SyntaxError unicodeescape | Barra invertida no caminho | Use `/` nos caminhos |
| distutils not found | Python 3.12 removeu distutils | `pip install --upgrade setuptools` |
| Pylance com avisos | Interpretador errado | Ctrl+Shift+P → Select Interpreter → 3.12 |
| Modelo Vosk não encontrado | Caminho errado | Verifique VOSK_MODEL_PATH no config.py |
| Interface não conecta | ws_server.py parado | Inicie o Terminal 1 primeiro |
| websockets não encontrado | Não estava no requirements original | `pip install websockets` |