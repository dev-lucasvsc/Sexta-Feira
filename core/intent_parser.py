"""
JARVIS v2.0 - Módulo de Interpretação de Intenções
====================================================
Analisa a transcrição do comando e gera a lista de acoes_sistema
correspondente, sem depender de um LLM externo.

Funciona como uma camada de regras + mapeamento que cobre os casos
mais comuns de automação local. Quando o LLM real for integrado,
este módulo pode ser mantido como fallback offline.
"""

import re
import os
import logging

logger = logging.getLogger("IntentParser")


# ==============================================================================
# Mapa de aplicativos: termos falados → comando/caminho real no Windows
# ==============================================================================
APP_MAP = {
    # Browsers
    "edge":                   "msedge",
    "microsoft edge":         "msedge",
    "chrome":                 "chrome",
    "google chrome":          "chrome",
    "firefox":                "firefox",

    # Office / produtividade
    "word":                   "winword",
    "excel":                  "excel",
    "powerpoint":             "powerpnt",
    "outlook":                "outlook",
    "teams":                  "teams",
    "microsoft teams":        "teams",
    "onenote":                "onenote",

    # Sistema
    "bloco de notas":         "notepad",
    "notepad":                "notepad",
    "explorador":             "explorer",
    "explorador de arquivos": "explorer",
    "calculadora":            "calc",
    "paint":                  "mspaint",
    "task manager":           "taskmgr",
    "gerenciador de tarefas": "taskmgr",
    "painel de controle":     "control",
    "configurações":          "ms-settings:",
    "prompt":                 "cmd",
    "terminal":               "wt",          # Windows Terminal
    "powershell":             "powershell",

    # Dev
    "vs code":                "code",
    "visual studio code":     "code",
    "visual studio":          "devenv",
    "github desktop":         "githubdesktop",
    "postman":                "postman",
    "docker":                 "docker desktop",
    "dbeaver":                "dbeaver",

    # Comunicação / mídia
    "spotify":                "spotify",
    "discord":                "discord",
    "whatsapp":               "whatsapp",
    "telegram":               "telegram",
    "slack":                  "slack",
    "zoom":                   "zoom",
    "obs":                    "obs64",

    # Ferramentas
    "obsidian":               "obsidian",
    "notion":                 "notion",
    "figma":                  "figma",
    "photoshop":              "photoshop",
    "premiere":               "premiere",
}

# ==============================================================================
# Mapa de sites: termos falados → URL
# ==============================================================================
SITE_MAP = {
    # Geral
    "youtube":          "https://youtube.com",
    "google":           "https://google.com",
    "gmail":            "https://mail.google.com",
    "google drive":     "https://drive.google.com",
    "google docs":      "https://docs.google.com",
    "google sheets":    "https://sheets.google.com",
    "google calendar":  "https://calendar.google.com",
    "google maps":      "https://maps.google.com",

    # Dev
    "github":           "https://github.com",
    "stackoverflow":    "https://stackoverflow.com",
    "stack overflow":   "https://stackoverflow.com",
    "npm":              "https://npmjs.com",
    "pypi":             "https://pypi.org",
    "vercel":           "https://vercel.com",
    "netlify":          "https://netlify.com",
    "railway":          "https://railway.app",
    "render":           "https://render.com",

    # IA
    "chatgpt":          "https://chat.openai.com",
    "claude":           "https://claude.ai",
    "gemini":           "https://gemini.google.com",
    "perplexity":       "https://perplexity.ai",
    "midjourney":       "https://midjourney.com",

    # Produtividade
    "notion":           "https://notion.so",
    "trello":           "https://trello.com",
    "linear":           "https://linear.app",
    "figma":            "https://figma.com",

    # Social / entretenimento
    "linkedin":         "https://linkedin.com",
    "instagram":        "https://instagram.com",
    "twitter":          "https://twitter.com",
    "reddit":           "https://reddit.com",
    "twitch":           "https://twitch.tv",
    "netflix":          "https://netflix.com",
    "whatsapp":         "https://web.whatsapp.com",

    # Finanças / utilitários
    "nubank":           "https://nubank.com.br",
    "mercado livre":    "https://mercadolivre.com.br",
    "amazon":           "https://amazon.com.br",
    "clima":            "https://weather.com/pt-BR",
    "tempo":            "https://weather.com/pt-BR",
}

# ==============================================================================
# Parser principal
# ==============================================================================

class IntentParser:
    """
    Interpreta comandos de voz e retorna uma lista de acoes_sistema.
    
    Intenções suportadas:
    - abrir_app    → abre aplicativo local
    - abrir_site   → abre URL no browser padrão
    - volume       → ajusta volume do sistema
    - bloquear     → bloqueia a tela
    - desligar      → desliga o PC
    - reiniciar    → reinicia o PC
    - pesquisar    → pesquisa no Google
    """

    def parse(self, comando: str) -> tuple[list[dict], str]:
        """
        Analisa o comando e retorna (acoes, resposta_fala).
        """
        comando = comando.lower().strip()
        acoes = []
        fala = ""

        # --- Abrir aplicativo ---
        if any(t in comando for t in ["abrir", "abre", "abra", "iniciar", "inicia", "lançar", "executar", "abrindo"]):
            app = self._match_app(comando)
            if app:
                nome, cmd = app
                acoes.append({"tipo": "abrir_app", "parametro": cmd})
                fala = f"Abrindo {nome}."
            else:
                site = self._match_site(comando)
                if site:
                    nome, url = site
                    acoes.append({"tipo": "abrir_site", "parametro": url})
                    fala = f"Abrindo {nome}."
                else:
                    fala = "Não reconheci qual aplicativo abrir."

        # --- Fechar aplicativo ---
        elif any(t in comando for t in ["fechar", "fecha", "encerrar", "encerra", "matar processo"]):
            app = self._match_app(comando)
            if app:
                nome, cmd = app
                acoes.append({"tipo": "fechar_app", "parametro": cmd})
                fala = f"Fechando {nome}."
            else:
                fala = "Não reconheci qual aplicativo fechar."

        # --- Navegar para site ---
        elif any(t in comando for t in ["ir para", "entrar no", "acessar", "navegar", "abrir site"]):
            site = self._match_site(comando)
            if site:
                nome, url = site
                acoes.append({"tipo": "abrir_site", "parametro": url})
                fala = f"Abrindo {nome}."
            else:
                fala = "Não reconheci qual site acessar."

        # --- Pesquisar ---
        elif any(t in comando for t in ["pesquisar", "pesquisa", "buscar", "busca", "procurar", "procura", "googlar"]):
            query = self._extract_search_query(comando)
            if query:
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                acoes.append({"tipo": "abrir_site", "parametro": url})
                fala = f"Pesquisando por {query}."
            else:
                fala = "Não entendi o que pesquisar."

        # --- Pesquisa no YouTube ---
        elif "youtube" in comando and any(t in comando for t in ["tocar", "toca", "colocar", "coloca", "buscar", "pesquisar"]):
            query = self._extract_after(comando, ["tocar", "toca", "colocar", "coloca", "buscar", "pesquisar", "no youtube", "youtube"])
            if query:
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                acoes.append({"tipo": "abrir_site", "parametro": url})
                fala = f"Buscando {query} no YouTube."

        # --- Volume ---
        elif any(t in comando for t in ["volume", "aumentar som", "diminuir som", "silenciar", "mudo", "mute"]):
            nivel, fala_vol = self._parse_volume(comando)
            if nivel is not None:
                acoes.append({"tipo": "volume", "parametro": nivel})
                fala = fala_vol
            else:
                fala = fala_vol

        # --- Bloquear tela ---
        elif any(t in comando for t in ["bloquear", "bloqueia", "travar tela", "lock", "bloquear tela"]):
            acoes.append({"tipo": "bloquear_tela"})
            fala = "Bloqueando a tela."

        # --- Desligar ---
        elif any(t in comando for t in ["desligar computador", "desligar pc", "desligar o pc", "encerrar sistema", "desligar o computador"]):
            acoes.append({"tipo": "desligar"})
            fala = "Desligando o computador em 30 segundos."

        # --- Reiniciar ---
        elif any(t in comando for t in ["reiniciar", "reinicia", "restart", "reiniciar o computador", "reiniciar o pc"]):
            acoes.append({"tipo": "reiniciar"})
            fala = "Reiniciando o computador."

        # --- Captura de tela ---
        elif any(t in comando for t in ["screenshot", "print", "captura de tela", "printscreen", "tirar print"]):
            acoes.append({"tipo": "comando_shell", "parametro": 'powershell -c "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait(\'%{PRTSC}\')"'})
            fala = "Captura de tela realizada."

        # --- Abrir pasta de downloads ---
        elif any(t in comando for t in ["abrir downloads", "pasta de downloads", "meus downloads"]):
            acoes.append({"tipo": "abrir_app", "parametro": f"explorer {os.path.expanduser('~/Downloads')}"})
            fala = "Abrindo pasta de downloads."

        # --- Abrir área de trabalho ---
        elif any(t in comando for t in ["área de trabalho", "desktop", "mostrar desktop"]):
            acoes.append({"tipo": "comando_shell", "parametro": 'powershell -c "(New-Object -ComObject Shell.Application).ToggleDesktop()"'})
            fala = "Mostrando a área de trabalho."

        # --- Sem intenção local reconhecida — deixa pro LLM ---
        else:
            fala = ""
            logger.info(f"[Intent] Sem intenção local para: '{comando}' — encaminhando ao LLM.")

        return acoes, fala

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _match_app(self, comando: str) -> tuple[str, str] | None:
        """Tenta encontrar um app no APP_MAP pelo nome mais longo primeiro."""
        # Ordena por comprimento decrescente para evitar match parcial curto
        for nome, cmd in sorted(APP_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if nome in comando:
                return nome, cmd
        return None

    def _match_site(self, comando: str) -> tuple[str, str] | None:
        """Tenta encontrar um site no SITE_MAP."""
        for nome, url in SITE_MAP.items():
            if nome in comando:
                return nome, url
        return None

    def _extract_after(self, comando: str, triggers: list[str]) -> str:
        """Extrai o texto após qualquer um dos triggers, retornando o maior fragmento."""
        resultado = ""
        for trigger in triggers:
            if trigger in comando:
                parte = comando.split(trigger, 1)[-1].strip()
                if len(parte) > len(resultado):
                    resultado = parte
        return resultado

    def _extract_search_query(self, comando: str) -> str:
        """Extrai a query de pesquisa removendo os verbos de trigger."""
        triggers = ["pesquisar por", "pesquisar sobre", "pesquisar", "buscar por",
                    "buscar sobre", "buscar", "procurar por", "procurar sobre", "procurar"]
        for trigger in triggers:
            if trigger in comando:
                return comando.split(trigger, 1)[-1].strip()
        return ""

    def _parse_volume(self, comando: str) -> tuple[int | None, str]:
        """Extrai nível de volume do comando."""
        # Tenta extrair número ("volume 70", "volume para 50")
        match = re.search(r'\d+', comando)
        if match:
            nivel = max(0, min(100, int(match.group())))
            return nivel, f"Ajustando volume para {nivel} por cento."

        if "mudo" in comando or "silenciar" in comando or "mute" in comando:
            return 0, "Silenciando o áudio."
        if "aumentar" in comando or "mais alto" in comando:
            return None, "Use 'volume 70' para definir o nível exato."
        if "diminuir" in comando or "mais baixo" in comando:
            return None, "Use 'volume 30' para definir o nível exato."

        return None, "Não entendi o nível de volume desejado."