"""
JARVIS v2.0 - Módulo de Automação e Smart Home
===============================================
Classes para controle do Sistema Operacional (os/subprocess)
e integração com SmartThings via API REST.

Os métodos marcados como [MOCK] simulam o comportamento esperado.
Para ativá-los em produção, descomente as linhas reais indicadas.
"""

import os
import subprocess
import logging
import requests

logger = logging.getLogger("Automation")


# ==============================================================================
# Controle do Sistema Operacional
# ==============================================================================

class OSAutomation:
    """
    Encapsula operações de automação do sistema operacional local.
    Compatível com Windows (primário), com observações para Linux/macOS.
    """

    def open_application(self, app_name: str) -> bool:
        """
        Abre um aplicativo pelo nome ou caminho.
        
        Args:
            app_name: Nome do executável ou caminho completo (ex: 'notepad', 'chrome').
        
        Returns:
            True se o comando foi enviado com sucesso.
        """
        logger.info(f"[OS] Abrindo aplicativo: '{app_name}'")
        try:
            # Windows: os.startfile é nativo e mais confiável
            os.startfile(app_name)  # type: ignore[attr-defined]
            return True
        except AttributeError:
            # Fallback para Linux/macOS
            subprocess.Popen(["xdg-open", app_name])
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao abrir '{app_name}': {e}")
            return False

    def run_shell_command(self, command: str, capture_output: bool = False) -> str | None:
        """
        Executa um comando shell.
        
        ⚠️  ATENÇÃO: Valide/sanitize comandos antes de expor ao usuário final.
        
        Args:
            command: Comando a executar.
            capture_output: Se True, retorna o stdout do comando.
        
        Returns:
            stdout como string (se capture_output=True), None caso contrário.
        """
        logger.info(f"[OS] Executando comando: '{command}'")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=15
            )
            if capture_output:
                return result.stdout.strip()
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"[OS] Timeout ao executar: '{command}'")
            return None
        except Exception as e:
            logger.error(f"[OS] Erro no comando '{command}': {e}")
            return None

    def get_system_info(self) -> dict:
        """
        Retorna informações básicas do sistema operacional.
        Útil para contexto na resposta do LLM.
        """
        import platform
        return {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }

    def close_application(self, app_name: str) -> bool:
        """
        Fecha um processo pelo nome do executável.
        Args:
            app_name: Nome do processo (ex: 'chrome', 'notepad').
        """
        logger.info(f"[OS] Fechando processo: '{app_name}'")
        try:
            self.run_shell_command(f"taskkill /IM {app_name}.exe /F")
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao fechar '{app_name}': {e}")
            return False

    def open_url(self, url: str) -> bool:
        """
        Abre uma URL no browser padrão do sistema.
        
        Args:
            url: URL completa a abrir (ex: 'https://youtube.com').
        """
        import webbrowser
        logger.info(f"[OS] Abrindo URL: '{url}'")
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao abrir URL '{url}': {e}")
            return False

    def set_volume(self, level: int) -> bool:
        """
        Ajusta o volume do sistema via PowerShell (nativo no Windows, sem dependências extras).
        
        Args:
            level: Volume de 0 a 100.
        """
        level = max(0, min(100, level))
        logger.info(f"[OS] Ajustando volume para {level}%")
        # Converte 0-100 para 0.0-1.0 (escala do PowerShell)
        ps_level = round(level / 100, 2)
        cmd = (
            f'powershell -Command "'
            f'$wshShell = New-Object -ComObject WScript.Shell; '
            f'$vol = New-Object -ComObject SAPI.SpVoice; '
            f'(New-Object -ComObject Shell.Application).Windows() | Out-Null; '
            f'[audio]::Volume = {ps_level}'
            f'"'
        )
        # Abordagem mais simples e confiável via nircmd (se disponível) ou PowerShell
        # PowerShell puro para mute/unmute e volume:
        ps_script = (
            f"$obj = New-Object -ComObject WScript.Shell; "
            f"1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; "  # muta tudo primeiro
        )
        # Usa a API de áudio do Windows via PowerShell com SoundVolumeView ou direto
        try:
            # Método direto: seta via SetMasterVolumeLevelScalar
            powershell_cmd = (
                f'powershell -Command "Add-Type -TypeDefinition \\"'
                f'using System.Runtime.InteropServices;'
                f'[Guid(\\"5CDF2C82-841E-4546-9722-0CF74078229A\\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]'
                f'interface IAudioEndpointVolume {{ void a(); void b(); void c(); void d(); '
                f'int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext); }}'
                f'\\"; '
                f'"'
            )
            # Fallback mais simples: usa nircmd se instalado, senão loga
            result = self.run_shell_command(
                f'powershell -Command "[System.Media.SystemSounds]::Beep" 2>nul',
                capture_output=True
            )
            # Método mais direto e garantido:
            self.run_shell_command(
                f'powershell -c "$wsh = New-Object -ComObject WScript.Shell; '
                f'for($i=0;$i -lt 50;$i++){{$wsh.SendKeys([char]174)}}; '
                f'for($i=0;$i -lt {level // 2};$i++){{$wsh.SendKeys([char]175)}}"'
            )
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao ajustar volume: {e}")
            return False

    def lock_screen(self) -> bool:
        """Bloqueia a tela do Windows."""
        logger.info("[OS] Bloqueando tela.")
        try:
            self.run_shell_command("rundll32.exe user32.dll,LockWorkStation")
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao bloquear tela: {e}")
            return False

    def shutdown(self, delay_seconds: int = 30) -> bool:
        """Desliga o computador após delay_seconds segundos."""
        logger.info(f"[OS] Desligando PC em {delay_seconds}s.")
        try:
            self.run_shell_command(f"shutdown /s /t {delay_seconds}")
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao desligar: {e}")
            return False

    def restart(self, delay_seconds: int = 10) -> bool:
        """Reinicia o computador após delay_seconds segundos."""
        logger.info(f"[OS] Reiniciando PC em {delay_seconds}s.")
        try:
            self.run_shell_command(f"shutdown /r /t {delay_seconds}")
            return True
        except Exception as e:
            logger.error(f"[OS] Erro ao reiniciar: {e}")
            return False


# ==============================================================================
# Controle SmartHome via SmartThings API
# ==============================================================================

class SmartHomeController:
    """
    Integração com a API REST do Samsung SmartThings.
    
    Documentação: https://developer.smartthings.com/docs/api/public/
    
    Para ativar em produção:
    1. Crie um Personal Access Token em: https://account.smartthings.com/tokens
    2. Passe o token no construtor ou via variável de ambiente SMARTTHINGS_TOKEN.
    """

    BASE_URL = "https://api.smartthings.com/v1"

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.getenv("SMARTTHINGS_TOKEN", "SEU_TOKEN_AQUI")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self._mock_mode = self.api_token in ("SEU_TOKEN_AQUI", "", None)
        if self._mock_mode:
            logger.warning("[SmartHome] Token não configurado. Rodando em modo MOCK.")

    def _post(self, endpoint: str, payload: dict) -> dict | None:
        """Método interno para chamadas POST à API do SmartThings."""
        if self._mock_mode:
            logger.info(f"[SmartHome MOCK] POST {endpoint} | Payload: {payload}")
            return {"status": "mock_success"}

        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[SmartHome] Erro na requisição para {url}: {e}")
            return None

    def _get(self, endpoint: str) -> dict | None:
        """Método interno para chamadas GET à API do SmartThings."""
        if self._mock_mode:
            logger.info(f"[SmartHome MOCK] GET {endpoint}")
            return {"items": [], "status": "mock_success"}

        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[SmartHome] Erro na requisição para {url}: {e}")
            return None

    def list_devices(self) -> list[dict]:
        """Retorna todos os dispositivos cadastrados na conta SmartThings."""
        result = self._get("/devices")
        if result and "items" in result:
            return result["items"]
        return []

    def turn_on_device(self, device_id: str) -> bool:
        """Liga um dispositivo pelo ID."""
        logger.info(f"[SmartHome] Ligando dispositivo: {device_id}")
        payload = {"commands": [{"component": "main", "capability": "switch", "command": "on"}]}
        result = self._post(f"/devices/{device_id}/commands", payload)
        return result is not None

    def turn_off_device(self, device_id: str) -> bool:
        """Desliga um dispositivo pelo ID."""
        logger.info(f"[SmartHome] Desligando dispositivo: {device_id}")
        payload = {"commands": [{"component": "main", "capability": "switch", "command": "off"}]}
        result = self._post(f"/devices/{device_id}/commands", payload)
        return result is not None

    def send_command(self, device_id: str, capability: str, command: str, arguments: list | None = None) -> bool:
        """
        Envia um comando genérico para qualquer capability SmartThings.
        
        Args:
            device_id: ID do dispositivo.
            capability: Ex: 'switchLevel', 'colorControl', 'thermostatMode'.
            command: Ex: 'setLevel', 'setColor', 'setThermostatMode'.
            arguments: Lista de argumentos opcionais do comando.
        """
        logger.info(f"[SmartHome] Comando '{command}' → {device_id} ({capability})")
        cmd = {"component": "main", "capability": capability, "command": command}
        if arguments:
            cmd["arguments"] = arguments
        payload = {"commands": [cmd]}
        result = self._post(f"/devices/{device_id}/commands", payload)
        return result is not None

    def set_light_level(self, device_id: str, level: int) -> bool:
        """
        Define o brilho de uma luz (0-100).
        
        Args:
            device_id: ID do dispositivo.
            level: Nível de brilho de 0 a 100.
        """
        level = max(0, min(100, level))  # Garante range válido
        return self.send_command(device_id, "switchLevel", "setLevel", [level])