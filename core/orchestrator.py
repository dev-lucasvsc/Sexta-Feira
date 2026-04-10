"""
JARVIS v2.0 - Orquestrador Central (Cérebro)
============================================
Responsável por unir todos os módulos e gerenciar o loop principal.
"""

import json
import time
import logging
from config import Config
from core.listener import Listener
from core.speaker import Speaker
from core.memory import ObsidianMemory
from core.automation import OSAutomation, SmartHomeController
from core.interface_bridge import InterfaceBridge
from core.intent_parser import IntentParser

# Configuração de log global
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Orchestrator")


class JarvisOrchestrator:
    """
    Orquestrador central do assistente.
    Integra todos os módulos e executa o loop principal de escuta e resposta.
    """

    WAKE_WORD = "jarvis"

    def __init__(self, obsidian_vault_path: str, interface_host: str = "localhost", interface_port: int = 5005):
        logger.info("Inicializando JARVIS v2.0...")

        self.listener = Listener(
            wake_word=self.WAKE_WORD,
            model_path=Config.VOSK_MODEL_PATH,
            language=Config.SPEECH_LANGUAGE,
            command_timeout=Config.COMMAND_TIMEOUT,
        )
        self.speaker  = Speaker(
            voice=Config.TTS_VOICE,
            rate=Config.TTS_RATE,
            pitch=Config.TTS_PITCH,
            volume=Config.TTS_VOLUME,
        )
        self.memory = ObsidianMemory(vault_path=obsidian_vault_path)
        self.os_automation = OSAutomation()
        self.smart_home = SmartHomeController()
        self.interface = InterfaceBridge(host=interface_host, port=interface_port)
        self.intent_parser = IntentParser()

        self.running = False
        logger.info("Todos os módulos carregados. JARVIS pronto.")

    # ------------------------------------------------------------------
    # MOCK: Simula chamada ao LLM (Claude, GPT, Ollama, etc.)
    # ------------------------------------------------------------------
    def _call_llm(self, transcricao: str, contexto_obsidian: str) -> dict:
        """
        Processamento central do comando.

        Fluxo:
        1. IntentParser resolve ações locais (abrir app, site, volume, etc.)
        2. Se não houver ação local → envia para Claude API com contexto do Obsidian
        3. Claude retorna JSON estruturado com fala_vocal, controle_interface, acoes_sistema
        """
        logger.info(f"[LLM] Processando: '{transcricao}'")

        # --- Passo 1: Tenta resolver intenção local primeiro ---
        acoes, fala_intent = self.intent_parser.parse(transcricao)
        if acoes:
            return {
                "fala_vocal": fala_intent,
                "controle_interface": {
                    "estado": "ativo",
                    "animacao": "pulso",
                    "dados_para_projetar": {"comando": transcricao}
                },
                "acoes_sistema": acoes
            }

        # --- Passo 2: Roteamento para o LLM configurado ---
        modo = Config.LLM_PROVIDER.lower()

        if modo == "claude" and Config.ANTHROPIC_API_KEY != "SUA_CHAVE_AQUI":
            return self._call_claude(transcricao, contexto_obsidian)

        if modo == "ollama":
            return self._call_ollama(transcricao, contexto_obsidian)

        # --- Passo 3: Nenhum LLM configurado ---
        logger.warning("[LLM] Nenhum provider configurado. Defina LLM_PROVIDER no config.py.")
        fala = "Nenhum modelo de linguagem configurado. Edite o config ponto py para ativar o Claude ou o Ollama."
        if contexto_obsidian:
            fala = f"Encontrei isso nas suas notas: {contexto_obsidian[:200]}"
        return {
            "fala_vocal": fala,
            "controle_interface": {"estado": "ativo", "animacao": "idle", "dados_para_projetar": {}},
            "acoes_sistema": []
        }

    # ------------------------------------------------------------------
    # Prompt compartilhado entre os dois providers
    # ------------------------------------------------------------------

    def _build_prompt(self, transcricao: str, contexto_obsidian: str) -> tuple[str, str]:
        """Retorna (system_prompt, user_prompt) usados por Claude e Ollama."""
        system = """Você é JARVIS, um assistente pessoal avançado, direto e eficiente.
Responda SEMPRE em português brasileiro.
Responda APENAS com um objeto JSON válido, sem markdown, sem texto fora do JSON.

Formato obrigatório:
{
  "fala_vocal": "texto curto e direto para ser falado em voz alta",
  "controle_interface": {
    "estado": "ativo",
    "animacao": "pulso",
    "dados_para_projetar": {"titulo": "...", "conteudo": "..."}
  },
  "acoes_sistema": []
}

Regras:
- fala_vocal: máximo 2 frases, natural, sem formatação especial
- acoes_sistema: lista vazia [] se não houver ação de sistema
- Use o contexto do Obsidian para enriquecer a resposta quando relevante
- Seja direto, sem introduções desnecessárias"""

        user = f"""Contexto do segundo cérebro (Obsidian):
{contexto_obsidian if contexto_obsidian else 'Nenhuma nota relevante encontrada.'}

Comando do usuário: {transcricao}"""

        return system, user

    def _parse_llm_response(self, raw: str, provider: str) -> dict:
        """Parseia e valida o JSON retornado pelo LLM."""
        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Tenta extrair JSON de dentro de texto corrido
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.error(f"[{provider}] JSON inválido: {raw[:120]}")
                return {"fala_vocal": "Erro ao interpretar a resposta do modelo.", "controle_interface": {"estado": "erro"}, "acoes_sistema": []}

        data.setdefault("fala_vocal", "Processado.")
        data.setdefault("controle_interface", {"estado": "ativo", "animacao": "idle", "dados_para_projetar": {}})
        data.setdefault("acoes_sistema", [])
        logger.info(f"[{provider}] Resposta: '{data['fala_vocal'][:80]}'")
        return data

    # ------------------------------------------------------------------
    # Provider: Claude API (Anthropic)
    # ------------------------------------------------------------------

    def _call_claude(self, transcricao: str, contexto_obsidian: str) -> dict:
        """Chama a API da Anthropic e retorna o JSON estruturado."""
        try:
            import anthropic
            system, user = self._build_prompt(transcricao, contexto_obsidian)
            client   = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=Config.LLM_MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return self._parse_llm_response(response.content[0].text, "Claude")
        except Exception as e:
            logger.error(f"[Claude] Erro na API: {e}")
            return {"fala_vocal": "Não consegui me conectar ao servidor Claude.", "controle_interface": {"estado": "erro"}, "acoes_sistema": []}

    # ------------------------------------------------------------------
    # Provider: Ollama (local, gratuito)
    # ------------------------------------------------------------------

    def _call_ollama(self, transcricao: str, contexto_obsidian: str) -> dict:
        """
        Chama o Ollama local e retorna o JSON estruturado.
        Requer Ollama rodando: https://ollama.com
        Modelo recomendado: ollama pull llama3.2
        """
        try:
            import requests as req
            system, user = self._build_prompt(transcricao, contexto_obsidian)

            # Ollama aceita system + user em formato de chat
            response = req.post(
                f"{Config.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": Config.OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user}
                    ]
                },
                timeout=30
            )
            response.raise_for_status()
            raw = response.json()["message"]["content"]
            return self._parse_llm_response(raw, "Ollama")
        except Exception as e:
            logger.error(f"[Ollama] Erro: {e}")
            return {"fala_vocal": "Não consegui me conectar ao Ollama local.", "controle_interface": {"estado": "erro"}, "acoes_sistema": []}

    # ------------------------------------------------------------------
    # Executor de ações do sistema
    # ------------------------------------------------------------------
    def _executar_acoes(self, acoes: list):
        """Interpreta e executa a lista de ações retornadas pelo processador de intenções / LLM."""
        for acao in acoes:
            tipo = acao.get("tipo")

            if tipo == "abrir_app":
                self.os_automation.open_application(acao.get("parametro", ""))

            elif tipo == "fechar_app":
                self.os_automation.close_application(acao.get("parametro", ""))

            elif tipo == "abrir_site":
                self.os_automation.open_url(acao.get("parametro", ""))

            elif tipo == "volume":
                self.os_automation.set_volume(int(acao.get("parametro", 50)))

            elif tipo == "bloquear_tela":
                self.os_automation.lock_screen()

            elif tipo == "desligar":
                self.os_automation.shutdown()

            elif tipo == "reiniciar":
                self.os_automation.restart()

            elif tipo == "comando_shell":
                self.os_automation.run_shell_command(acao.get("parametro", ""))

            elif tipo == "smartthings":
                dispositivo = acao.get("dispositivo", "")
                comando = acao.get("acao", "")
                if comando == "ligar":
                    self.smart_home.turn_on_device(dispositivo)
                elif comando == "desligar":
                    self.smart_home.turn_off_device(dispositivo)
                else:
                    self.smart_home.send_command(dispositivo, comando)

            else:
                logger.warning(f"Ação desconhecida ignorada: {tipo}")

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def start(self):
        """Inicia o loop principal do assistente."""
        self.running = True
        self.interface.connect()
        self.interface.send_state("standby")
        self.speaker.speak("JARVIS v2.0 online. Aguardando sua palavra de ativação.")

        logger.info(f"Loop principal iniciado. Wake word: '{self.WAKE_WORD}'")

        try:
            while self.running:
                # 1. Aguarda a wake word e captura o comando
                comando = self.listener.listen_for_command()

                if not comando:
                    continue  # Timeout ou ruído — volta para escuta

                logger.info(f"Comando capturado: '{comando}'")
                self.interface.send_state("processando")

                # 2. Busca contexto relevante no Obsidian
                contexto = self.memory.search(query=comando)
                logger.info(f"Contexto Obsidian encontrado: {len(contexto)} chars")

                # 3. Envia para o LLM (mock ou real)
                resposta = self._call_llm(transcricao=comando, contexto_obsidian=contexto)

                # 4. Atualiza a interface holográfica
                controle = resposta.get("controle_interface", {})
                self.interface.send_state(
                    estado=controle.get("estado", "ativo"),
                    payload=controle
                )

                # 5. Fala a resposta
                fala = resposta.get("fala_vocal", "")
                if fala:
                    self.speaker.speak(fala)

                # 6. Executa ações no sistema
                self._executar_acoes(resposta.get("acoes_sistema", []))

                # Breve pausa antes de voltar ao standby
                time.sleep(0.5)
                self.interface.send_state("standby")

        except KeyboardInterrupt:
            logger.info("Encerrando JARVIS por interrupção do usuário.")
        finally:
            self.stop()

    def stop(self):
        """Encerra os recursos do assistente de forma limpa."""
        self.running = False
        self.interface.disconnect()
        self.speaker.speak("Até logo.")
        logger.info("JARVIS encerrado.")