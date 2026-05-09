"""
Registro central de ferramentas da Sexta-Feira.

Cada acao tem metadados de seguranca para o orquestrador decidir quando
pode executar direto, quando pode vir do LLM e quando precisa confirmacao.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk: str = "low"
    allow_llm: bool = True
    requires_confirmation: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_ollama_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [],
                },
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._register_defaults()

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str | None) -> ToolDefinition | None:
        if not name:
            return None
        return self._tools.get(name)

    def is_allowed_from_llm(self, name: str | None) -> bool:
        tool = self.get(name)
        return bool(tool and tool.allow_llm)

    def needs_confirmation(self, action: dict) -> bool:
        if action.get("confirmado"):
            return False
        tool = self.get(action.get("tipo"))
        return bool(tool and tool.requires_confirmation)

    def allowed_llm_action_types(self) -> set[str]:
        return {name for name, tool in self._tools.items() if tool.allow_llm}

    def to_ollama_tools(self) -> list[dict]:
        return [tool.to_ollama_tool() for tool in self._tools.values() if tool.allow_llm]

    def summary_for_prompt(self) -> str:
        lines = []
        for tool in self._tools.values():
            if tool.allow_llm:
                lines.append(f"- {tool.name}: {tool.description}")
        return "Ferramentas disponiveis:\n" + "\n".join(lines)

    def _register_defaults(self):
        safe = [
            ("abrir_app", "Abre um aplicativo local pelo nome ou caminho.", {"parametro": {"type": "string"}}),
            ("abrir_site", "Abre uma URL no navegador padrao.", {"parametro": {"type": "string"}}),
            ("volume", "Ajusta o volume do sistema de 0 a 100.", {"parametro": {"type": "integer"}}),
            ("notificacao", "Mostra uma notificacao do Windows.", {"titulo": {"type": "string"}, "mensagem": {"type": "string"}}),
            ("spotify_play", "Busca e toca musica, artista ou playlist no Spotify.", {"query": {"type": "string"}}),
            ("spotify_pause", "Pausa o Spotify.", {}),
            ("spotify_next", "Avanca para a proxima musica no Spotify.", {}),
            ("spotify_prev", "Volta para a musica anterior no Spotify.", {}),
            ("spotify_volume", "Ajusta o volume do Spotify de 0 a 100.", {"parametro": {"type": "integer"}}),
            ("spotify_now", "Informa a musica atual do Spotify.", {}),
            ("spotify_shuffle", "Alterna o modo aleatorio do Spotify.", {}),
            ("obsidian_criar", "Cria uma nota no Obsidian.", {"titulo": {"type": "string"}, "conteudo": {"type": "string"}}),
            ("obsidian_anotar", "Adiciona texto ao diario do Obsidian.", {"conteudo": {"type": "string"}}),
            ("obsidian_tarefa", "Cria uma tarefa no Obsidian.", {"conteudo": {"type": "string"}}),
            ("lembrete", "Cria um lembrete temporizado.", {"texto": {"type": "string"}, "minutos": {"type": "integer"}, "segundos": {"type": "integer"}}),
            ("lembrete_listar", "Lista lembretes ativos.", {}),
            ("modo_silencioso", "Ativa ou desativa respostas por voz.", {"ativar": {"type": "boolean"}}),
            ("arquivo_listar", "Lista arquivos de uma pasta.", {"path": {"type": "string"}}),
            ("arquivo_criar_pasta", "Cria uma pasta.", {"path": {"type": "string"}}),
            ("arquivo_buscar", "Busca arquivos por nome ou extensao.", {"path": {"type": "string"}, "nome": {"type": "string"}}),
            ("janela_listar", "Lista janelas abertas.", {}),
            ("janela_focar", "Foca uma janela pelo nome.", {"nome": {"type": "string"}}),
            ("janela_alternar", "Alterna para outra janela.", {}),
            ("preferencia_set", "Salva uma preferencia do usuario.", {"chave": {"type": "string"}, "valor": {"type": "string"}}),
            ("diagnostico", "Mostra status da assistente e integracoes.", {}),
        ]
        for name, description, parameters in safe:
            self.register(ToolDefinition(name=name, description=description, parameters=parameters))

        confirmed = [
            ("fechar_app", "Fecha um aplicativo/processo.", "medium", {"parametro": {"type": "string"}}),
            ("bloquear_tela", "Bloqueia a tela do Windows.", "medium", {}),
            ("desligar", "Desliga o computador.", "critical", {}),
            ("reiniciar", "Reinicia o computador.", "critical", {}),
            ("comando_shell", "Executa comando de shell predefinido.", "critical", {"parametro": {"type": "string"}}),
            ("arquivo_mover", "Move arquivo ou pasta.", "high", {"origem": {"type": "string"}, "destino": {"type": "string"}}),
            ("arquivo_renomear", "Renomeia arquivo ou pasta.", "high", {"path": {"type": "string"}, "novo_nome": {"type": "string"}}),
            ("arquivo_organizar", "Organiza arquivos de uma pasta por tipo.", "high", {"path": {"type": "string"}}),
            ("arquivo_deletar", "Apaga arquivo ou pasta.", "critical", {"path": {"type": "string"}}),
            ("janela_fechar", "Fecha a janela ativa.", "medium", {}),
            ("janela_minimizar_tudo", "Minimiza todas as janelas.", "medium", {}),
            ("janela_maximizar", "Maximiza a janela ativa.", "medium", {}),
            ("janela_snap_esquerda", "Move janela ativa para esquerda.", "medium", {}),
            ("janela_snap_direita", "Move janela ativa para direita.", "medium", {}),
        ]
        for name, description, risk, parameters in confirmed:
            self.register(ToolDefinition(
                name=name,
                description=description,
                risk=risk,
                allow_llm=False,
                requires_confirmation=risk in {"high", "critical"},
                parameters=parameters,
            ))
