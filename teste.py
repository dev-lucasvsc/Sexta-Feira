"""
Sexta-Feira v2.0 - Modo de Teste (sem microfone)
=================================================
Permite testar a Sexta-Feira digitando comandos no terminal,
sem precisar do microfone ou do Vosk.

Útil para:
- Testar novas intenções no intent_parser
- Debugar respostas do LLM
- Desenvolver sem precisar falar

Uso:
    python teste.py

Comandos especiais no modo teste:
    /sair       → encerra o teste
    /voz on     → ativa a fala (padrão: desativada no teste)
    /voz off    → desativa a fala
    /intent     → mostra o que o intent_parser retorna para o comando
    /historico  → mostra o histórico da sessão atual
    /limpar     → limpa o histórico da sessão
"""

import sys
import os
import logging

# Silencia logs desnecessários no modo teste
logging.basicConfig(
    level=logging.WARNING,
    format="[%(name)s] %(message)s"
)
# Mantém logs do Orchestrator e IntentParser visíveis
logging.getLogger("Orchestrator").setLevel(logging.INFO)
logging.getLogger("IntentParser").setLevel(logging.INFO)
logging.getLogger("Speaker").setLevel(logging.INFO)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.intent_parser import IntentParser
from core.orchestrator import SextaFeiraOrchestrator


class ModoTeste:
    """
    Modo interativo de teste via terminal.
    Injeta comandos diretamente no orchestrator,
    bypassando o microfone e o Vosk.
    """

    COR_USER  = "\033[94m"   # azul
    COR_SEXTA = "\033[92m"   # verde
    COR_INFO  = "\033[93m"   # amarelo
    COR_RESET = "\033[0m"
    COR_BOLD  = "\033[1m"

    def __init__(self):
        self.voz_ativa = False  # desativada por padrão no teste
        self.intent_parser = IntentParser()
        self._inicializar_orchestrator()

    def _inicializar_orchestrator(self):
        """Inicializa o orchestrator sem microfone."""
        print(f"\n{self.COR_BOLD}Sexta-Feira v2.0 — Modo Teste{self.COR_RESET}")
        print(f"{self.COR_INFO}Inicializando sem microfone...{self.COR_RESET}")

        self.orq = SextaFeiraOrchestrator(
            obsidian_vault_path=Config.OBSIDIAN_VAULT_PATH,
        )

        # Ativa modo silencioso por padrão no teste
        self.orq.silent_mode = not self.voz_ativa

        print(f"{self.COR_INFO}Sistema pronto. Digite um comando ou /ajuda{self.COR_RESET}\n")

    def _processar(self, comando: str) -> str:
        """Processa um comando e retorna a resposta falada."""
        contexto = self.orq.memory.search(query=comando)
        resposta  = self.orq._call_llm(transcricao=comando, contexto_obsidian=contexto)

        fala  = resposta.get("fala_vocal", "")
        acoes = resposta.get("acoes_sistema", [])

        # Registra na memória
        self.orq.session_memory.add_user(comando)
        self.orq.history.add("user", comando)

        if fala:
            self.orq.session_memory.add_assistant(fala)
            self.orq.history.add("assistant", fala)
            if self.voz_ativa:
                self.orq.speaker.speak(fala)

        # Executa ações
        if acoes:
            self.orq._executar_acoes(acoes)

        return fala, acoes

    def _comando_especial(self, cmd: str) -> bool:
        """Processa comandos especiais do modo teste. Retorna True se foi especial."""
        cmd = cmd.strip().lower()

        if cmd == "/ajuda":
            print(f"""
{self.COR_BOLD}Comandos especiais:{self.COR_RESET}
  /sair       → encerra o teste
  /voz on     → ativa a fala
  /voz off    → desativa a fala
  /intent     → analisa a próxima entrada com o intent_parser
  /historico  → mostra histórico da sessão
  /limpar     → limpa o histórico
  /config     → mostra configurações ativas
""")
            return True

        if cmd == "/sair":
            print(f"\n{self.COR_INFO}Encerrando modo teste.{self.COR_RESET}")
            sys.exit(0)

        if cmd == "/voz on":
            self.voz_ativa = True
            self.orq.silent_mode = False
            print(f"  {self.COR_INFO}Voz ativada.{self.COR_RESET}")
            return True

        if cmd == "/voz off":
            self.voz_ativa = False
            self.orq.silent_mode = True
            print(f"  {self.COR_INFO}Voz desativada.{self.COR_RESET}")
            return True

        if cmd == "/historico":
            resumo = self.orq.session_memory.get_summary()
            print(f"\n{self.COR_INFO}Histórico da sessão:{self.COR_RESET}")
            print(resumo if resumo else "  (vazio)")
            print()
            return True

        if cmd == "/limpar":
            self.orq.session_memory.clear()
            print(f"  {self.COR_INFO}Histórico limpo.{self.COR_RESET}")
            return True

        if cmd == "/config":
            print(f"""
{self.COR_BOLD}Configurações ativas:{self.COR_RESET}
  Wake word:    {Config.WAKE_WORD}
  LLM provider: {Config.LLM_PROVIDER}
  Voz:          {Config.TTS_VOICE} ({Config.TTS_PITCH})
  Vault:        {Config.OBSIDIAN_VAULT_PATH}
  Modo silencioso: {self.orq.silent_mode}
""")
            return True

        return False

    def run(self):
        """Loop principal do modo teste."""
        while True:
            try:
                entrada = input(f"{self.COR_USER}você → {self.COR_RESET}").strip()

                if not entrada:
                    continue

                # Comandos especiais
                if entrada.startswith("/"):

                    # Modo análise de intent
                    if entrada == "/intent":
                        cmd = input(f"  {self.COR_INFO}comando para analisar → {self.COR_RESET}").strip()
                        acoes, fala = self.intent_parser.parse(cmd)
                        print(f"  {self.COR_INFO}acoes: {acoes}{self.COR_RESET}")
                        print(f"  {self.COR_INFO}fala:  '{fala}'{self.COR_RESET}")
                        continue

                    if self._comando_especial(entrada):
                        continue

                # Processa como comando normal
                fala, acoes = self._processar(entrada)

                if fala:
                    print(f"{self.COR_SEXTA}sexta → {self.COR_RESET}{fala}")

                if acoes:
                    for acao in acoes:
                        tipo = acao.get("tipo", "?")
                        param = acao.get("parametro", acao.get("query", acao.get("conteudo", "")))
                        print(f"  {self.COR_INFO}[ação] {tipo}: {param}{self.COR_RESET}")

                if not fala and not acoes:
                    print(f"  {self.COR_INFO}(sem resposta gerada){self.COR_RESET}")

            except KeyboardInterrupt:
                print(f"\n{self.COR_INFO}Encerrando.{self.COR_RESET}")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"  {self.COR_INFO}Erro: {e}{self.COR_RESET}")


if __name__ == "__main__":
    ModoTeste().run()