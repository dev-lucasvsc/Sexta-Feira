"""
Sexta-Feira v2.0 - Orquestrador Central (Cérebro)
============================================
Responsável por unir todos os módulos e gerenciar o loop principal.
"""

import json
import time
import logging
import datetime
from config import Config
from core.listener import Listener
from core.speaker import Speaker
from core.memory import ObsidianMemory
from core.automation import OSAutomation, SmartHomeController
from core.interface_bridge import InterfaceBridge
from core.intent_parser import IntentParser
from core.file_manager import FileManager
from core.reminder import ReminderManager
from core.session_memory import SessionMemory
from core.command_logger import CommandLogger

# Configuração de log global
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Orchestrator")


class SextaFeiraOrchestrator:
    """
    Orquestrador central do assistente.
    Integra todos os módulos e executa o loop principal de escuta e resposta.
    """

    WAKE_WORD = "sexta feira"

    def __init__(self, obsidian_vault_path: str, interface_host: str = "localhost", interface_port: int = 5005):
        logger.info("Inicializando Sexta-Feira...")

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
        # Callback: atualiza a interface holográfica em tempo real durante a fala
        self.speaker.on_speaking_change = self._on_speaking_change
        self.memory = ObsidianMemory(vault_path=obsidian_vault_path)
        self.os_automation  = OSAutomation()
        self.smart_home     = SmartHomeController()
        self.interface      = InterfaceBridge(host=interface_host, port=interface_port)
        self.intent_parser  = IntentParser()
        self.file_manager   = FileManager()
        self.session_memory = SessionMemory(max_turns=Config.SESSION_MEMORY_TURNS)
        self.cmd_logger     = CommandLogger(log_dir=Config.LOG_DIR)
        self.reminders      = ReminderManager(on_reminder=self._on_reminder)

        self.running = False
        logger.info("Todos os módulos carregados. Sexta-Feira pronta.")

    def _on_speaking_change(self, falando: bool):
        """
        Callback disparado pelo Speaker quando o estado de fala muda.
        Mantém a interface em modo 'speak' durante TODA a duração do áudio
        e volta ao 'standby' assim que termina.
        """
        if falando:
            self.interface.send_state("speak")
        else:
            self.interface.send_state("standby")

    def _on_reminder(self, texto: str):
        """Callback disparado quando um lembrete vence."""
        logger.info(f"[Reminder] Disparando: '{texto}'")
        self.interface.send_state("speak")
        self.speaker.speak(f"Lembrete: {texto}")

    # ------------------------------------------------------------------
    # Hora, data e clima (sem LLM)
    # ------------------------------------------------------------------

    def _get_datetime_response(self, comando: str) -> dict | None:
        """Responde perguntas de hora e data instantaneamente, sem LLM."""
        agora = datetime.datetime.now()
        cmd = comando.lower()

        if any(t in cmd for t in ["horas", "que horas", "hora atual", "horas são"]):
            fala = f"São {agora.strftime('%H horas e %M minutos')}."
            return self._resposta_simples(fala)

        if any(t in cmd for t in ["data", "que dia", "dia hoje", "hoje é"]):
            dias   = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]
            meses  = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
            fala   = f"Hoje é {dias[agora.weekday()]}, {agora.day} de {meses[agora.month-1]} de {agora.year}."
            return self._resposta_simples(fala)

        if any(t in cmd for t in ["dia da semana", "que dia da semana"]):
            dias = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]
            fala = f"Hoje é {dias[agora.weekday()]}."
            return self._resposta_simples(fala)

        return None

    def _get_weather_response(self) -> dict:
        """Busca o clima atual via OpenWeatherMap."""
        if Config.WEATHER_API_KEY == "SUA_CHAVE_AQUI":
            return self._resposta_simples(
                "A chave da API de clima não está configurada. Adicione WEATHER_API_KEY no config ponto py."
            )
        try:
            import requests as req
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={Config.WEATHER_CITY},{Config.WEATHER_COUNTRY}"
                f"&appid={Config.WEATHER_API_KEY}"
                f"&lang={Config.WEATHER_LANG}"
                f"&units={Config.WEATHER_UNITS}"
            )
            r = req.get(url, timeout=8)
            r.raise_for_status()
            d = r.json()
            temp     = round(d["main"]["temp"])
            sensacao = round(d["main"]["feels_like"])
            desc     = d["weather"][0]["description"]
            umidade  = d["main"]["humidity"]
            fala = (
                f"Em {Config.WEATHER_CITY}, agora são {temp} graus, "
                f"com {desc}. Sensação térmica de {sensacao} graus e umidade de {umidade} por cento."
            )
            return self._resposta_simples(fala, titulo="Clima", conteudo=fala)
        except Exception as e:
            logger.error(f"[Clima] Erro: {e}")
            return self._resposta_simples("Não consegui obter as informações do clima no momento.")

    def _resposta_simples(self, fala: str, titulo: str = "", conteudo: str = "") -> dict:
        """Helper para montar resposta sem LLM."""
        return {
            "fala_vocal": fala,
            "controle_interface": {
                "estado": "ativo", "animacao": "pulso",
                "dados_para_projetar": {"titulo": titulo, "conteudo": conteudo or fala}
            },
            "acoes_sistema": []
        }

    # ------------------------------------------------------------------
    # MOCK: Simula chamada ao LLM (Claude, GPT, Ollama, etc.)
    # ------------------------------------------------------------------
    def _call_llm(self, transcricao: str, contexto_obsidian: str) -> dict:
        """
        Processamento central do comando.

        Fluxo:
        1. Hora / data (sem LLM, instantâneo)
        2. Clima (sem LLM, API externa)
        3. IntentParser resolve ações locais
        4. LLM (Claude ou Ollama) com histórico de sessão
        """
        logger.info(f"[LLM] Processando: '{transcricao}'")
        cmd = transcricao.lower()

        # --- Hora e data (sem LLM) ---
        dt_resp = self._get_datetime_response(cmd)
        if dt_resp:
            return dt_resp

        # --- Clima (sem LLM) ---
        if any(t in cmd for t in ["clima", "tempo", "temperatura", "vai chover",
                                   "previsão", "graus", "como está o tempo"]):
            return self._get_weather_response()

        # --- Intenções locais ---
        acoes, fala_intent = self.intent_parser.parse(transcricao)
        if acoes:
            if fala_intent == "__apresentacao__":
                return self._resposta_apresentacao(acoes)
            if fala_intent == "__noticias__":
                return self._resposta_noticias(acoes)
            return {
                "fala_vocal": fala_intent,
                "controle_interface": {
                    "estado": "ativo", "animacao": "pulso",
                    "dados_para_projetar": {"comando": transcricao}
                },
                "acoes_sistema": acoes
            }

        # --- Roteamento para o LLM ---
        modo = Config.LLM_PROVIDER.lower()
        if modo == "claude" and Config.ANTHROPIC_API_KEY != "SUA_CHAVE_AQUI":
            return self._call_claude(transcricao, contexto_obsidian)
        if modo == "ollama":
            return self._call_ollama(transcricao, contexto_obsidian)

        # --- Sem LLM configurado ---
        logger.warning("[LLM] Nenhum provider configurado.")
        fala = "Nenhum modelo de linguagem configurado. Edite o config ponto py."
        if contexto_obsidian:
            fala = f"Encontrei isso nas suas notas: {contexto_obsidian[:200]}"
        return self._resposta_simples(fala)

    # ------------------------------------------------------------------
    # Prompt compartilhado entre os dois providers
    # ------------------------------------------------------------------

    def _build_prompt(self, transcricao: str, contexto_obsidian: str) -> tuple[str, str]:
        """Retorna (system_prompt, user_prompt) com personalidade e histórico de sessão."""

        # Tom de resposta baseado na configuração
        tons = {
            "formal":   "Use linguagem formal e profissional.",
            "casual":   "Use linguagem casual e amigável, como uma conversa entre amigos.",
            "técnico":  "Use linguagem técnica e precisa, com termos específicos quando relevante.",
            "conciso":  "Seja extremamente conciso. Máximo de 1 frase na fala_vocal.",
        }
        instrucao_tom = tons.get(Config.PERSONALITY_TONE, tons["casual"])
        max_frases    = Config.MAX_RESPONSE_SENTENCES

        system = f"""Você é {Config.ASSISTANT_NAME}, uma assistente pessoal de IA avançada.
Responda SEMPRE em português brasileiro.
Responda APENAS com um objeto JSON válido, sem markdown, sem texto fora do JSON.
{instrucao_tom}
Limite fala_vocal a no máximo {max_frases} frase(s).

Formato obrigatório:
{{
  "fala_vocal": "texto para ser falado em voz alta",
  "controle_interface": {{
    "estado": "ativo",
    "animacao": "pulso",
    "dados_para_projetar": {{"titulo": "...", "conteudo": "..."}}
  }},
  "acoes_sistema": []
}}

Regras:
- fala_vocal: natural, sem formatação especial, sem listas
- acoes_sistema: lista vazia [] se não houver ação de sistema
- Use o contexto do Obsidian para enriquecer a resposta quando relevante
- Use o histórico da conversa para manter continuidade"""

        # Histórico de sessão
        historico = self.session_memory.get_summary()

        user = f"""{f'Histórico recente:{chr(10)}{historico}{chr(10)}' if historico else ''}
Contexto do segundo cérebro (Obsidian):
{contexto_obsidian if contexto_obsidian else 'Nenhuma nota relevante encontrada.'}

Comando atual: {transcricao}"""

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
    # Respostas especiais
    # ------------------------------------------------------------------

    def _resposta_apresentacao(self, acoes: list) -> dict:
        """
        Resposta de apresentação da Sexta-Feira.
        Faz uma apresentação completa com demonstração dos estados da interface.
        """
        import threading

        fala = (
            "Olá. Eu sou a Sexta-Feira, sua assistente pessoal de inteligência artificial. "
            "Fui projetada para ser a interface central do seu ecossistema digital e do seu ambiente físico. "
            "Entre as minhas capacidades, eu posso gerenciar seus aplicativos, consultar sua base de dados, "
            "e operar a automação dos dispositivos inteligentes da sua casa. "
            "Além disso, estou pronta para realizar pesquisas na rede e responder às suas perguntas. "
            "Basta me dizer o que deseja."
        )

        # Dispara demonstração dos estados da interface em background
        def demo_interface():
            import time
            estados = [
                ("listen",  1.5),
                ("think",   2.0),
                ("speak",   3.0),
                ("idle",    0.0),
            ]
            time.sleep(0.5)
            for estado, duracao in estados:
                self.interface.send_state(estado)
                if duracao > 0:
                    time.sleep(duracao)

        threading.Thread(target=demo_interface, daemon=True).start()

        return {
            "fala_vocal": fala,
            "controle_interface": {
                "estado": "speak",
                "animacao": "pulso",
                "dados_para_projetar": {
                    "titulo": "Sexta-Feira",
                    "conteudo": "Assistente pessoal de IA — online e operacional."
                }
            },
            "acoes_sistema": acoes
        }

    def _resposta_noticias(self, acoes: list) -> dict:
        """Abre Google News e anuncia que está buscando as notícias."""
        import datetime
        hoje = datetime.datetime.now().strftime("%d de %B de %Y")

        fala = f"Buscando as principais notícias do dia {hoje}. Abrindo o Google Notícias para você."

        return {
            "fala_vocal": fala,
            "controle_interface": {
                "estado": "think",
                "animacao": "pulso",
                "dados_para_projetar": {
                    "titulo": "Notícias do dia",
                    "conteudo": hoje
                }
            },
            "acoes_sistema": acoes
        }

    # ------------------------------------------------------------------
    # Executor de ações do sistema
    # ------------------------------------------------------------------
    def _executar_acoes(self, acoes: list):
        """Interpreta e executa a lista de ações retornadas pelo processador de intenções / LLM."""
        for acao in acoes:
            tipo = acao.get("tipo")

            if tipo == "apresentacao":
                pass

            elif tipo == "lembrete":
                confirmacao = self.reminders.add(
                    texto=acao.get("texto", "lembrete"),
                    minutos=acao.get("minutos", 0),
                    segundos=acao.get("segundos", 0)
                )
                self.speaker.speak(confirmacao)

            elif tipo == "lembrete_listar":
                self.speaker.speak(self.reminders.list_active())

            elif tipo == "abrir_app":
                parametro = acao.get("parametro", "")
                # Se o WhatsApp não foi encontrado localmente, abre a versão web
                if parametro.startswith("http"):
                    self.os_automation.open_url(parametro)
                else:
                    self.os_automation.open_application(parametro)

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

            elif tipo == "arquivo_listar":
                ok, msg = self.file_manager.list_folder(acao.get("path", "~/Desktop"))
                self.speaker.speak(msg)

            elif tipo == "arquivo_criar_pasta":
                ok, msg = self.file_manager.create_folder(acao.get("path", ""))
                self.speaker.speak(msg)

            elif tipo == "arquivo_mover":
                ok, msg = self.file_manager.move(acao.get("origem", ""), acao.get("destino", ""))
                self.speaker.speak(msg)

            elif tipo == "arquivo_renomear":
                ok, msg = self.file_manager.rename(acao.get("path", ""), acao.get("novo_nome", ""))
                self.speaker.speak(msg)

            elif tipo == "arquivo_organizar":
                ok, msg = self.file_manager.organize_by_type(acao.get("path", "~/Downloads"))
                self.speaker.speak(msg)

            elif tipo == "arquivo_buscar":
                ok, msg = self.file_manager.search(
                    acao.get("path", "~/Desktop"),
                    nome=acao.get("nome", ""),
                    extensao=acao.get("extensao", "")
                )
                self.speaker.speak(msg)

            elif tipo == "arquivo_deletar":
                ok, msg = self.file_manager.delete(acao.get("path", ""), confirmar=acao.get("confirmar", False))
                self.speaker.speak(msg)

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
        self.speaker.speak("Olá chefe, como posso ajudar hoje?.")

        logger.info(f"Loop principal iniciado. Wake word: '{self.WAKE_WORD}'")

        try:
            while self.running:
                # 1. Aguarda wake word e captura o comando
                comando = self.listener.listen_for_command()
                if not comando:
                    continue

                logger.info(f"Comando capturado: '{comando}'")
                self.cmd_logger.log_command(comando)
                self.interface.send_state("listen")

                # 2. Busca contexto no Obsidian
                contexto = self.memory.search(query=comando)

                # 3. Registra na memória de sessão
                self.session_memory.add_user(comando)

                # 4. Processa o comando
                self.interface.send_state("think")
                resposta = self._call_llm(transcricao=comando, contexto_obsidian=contexto)

                # 5. Fala a resposta (interface reage via callback)
                fala = resposta.get("fala_vocal", "")
                if fala:
                    self.cmd_logger.log_response(fala)
                    self.session_memory.add_assistant(fala)
                    self.speaker.speak(fala)

                # 6. Executa ações
                acoes = resposta.get("acoes_sistema", [])
                for acao in acoes:
                    self.cmd_logger.log_action(acao.get("tipo", "?"), str(acao.get("parametro", "")))
                self._executar_acoes(acoes)

                self.cmd_logger.log_separator()

                # Garante standby se não houve fala
                if not fala.strip():
                    time.sleep(0.3)
                    self.interface.send_state("standby")

        except KeyboardInterrupt:
            logger.info("Encerrando Sexta-Feira por interrupção do usuário.")
        finally:
            self.stop()

    def stop(self):
        """Encerra os recursos do assistente de forma limpa."""
        self.running = False
        self.reminders.cancel_all()
        self.cmd_logger.log_session_end()
        self.interface.disconnect()
        self.speaker.speak("Até logo chefe.")
        logger.info("Sexta-Feira encerrada.")