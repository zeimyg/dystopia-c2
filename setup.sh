#!/usr/bin/env bash

# --- Configuracion Global ---
set -eo pipefail  # Detener en errores y capturar pipes
PYTHON_WINE_VERSION="3.10.4"  # Version parametrizada
WINE_PATHS=("/root/.wine" "$HOME/.wine")  # Rutas alternativas de Wine

# --- Funciones Auxiliares ---

# Funcion para imprimir mensajes formateados
print_msg() {
    local color_code prefix msg_type
    msg_type="$2"
    msg="$1"

    case "$msg_type" in
        "success") color_code="\033[1;32m"; prefix="[+] " ;;
        "error") color_code="\033[1;31m"; prefix="[!] " ;;
        "info") color_code="\033[1;34m"; prefix="[*] " ;;
        "query") color_code="\033[1;35m"; prefix="[?] " ;;
        *) color_code="\033[0m"; prefix="" ;;
    esac

    echo -e "\n${color_code}${prefix}${msg}\033[0m"
}

# Verificar existencia de comandos con mensaje
command_exists() {
    if ! command -v "$1" &>/dev/null; then
        print_msg "Comando no encontrado: $1" "error"
        return 1
    fi
}

# Verificar privilegios de sudo
check_sudo() {
    if ! sudo -v &>/dev/null; then
        print_msg "Este script necesita ser ejecutado como root." "error"
        exit 1
    fi
}

# --- Funciones Principales ---

# Detectar distribucion del sistema
get_distro() {
    if [[ -f /etc/os-release ]]; then
        DISTRO=$(awk -F= '/^ID=/{print $2}' /etc/os-release | tr -d '"')
    elif [[ -f /etc/lsb-release ]]; then
        DISTRO=$(awk -F= '/^DISTRIB_ID/{print $2}' /etc/lsb-release | tr -d '"')
    else
        DISTRO="unknown"
    fi
}

# Instalar dependencias del sistema
install_system_dependencies() {
    get_distro
    check_sudo

    case "$DISTRO" in
        "ubuntu"|"debian"|"kali")
            print_msg "Instalando dependencias para Debian/Ubuntu..." "info"
            # Eliminar archivos de bloqueo de dpkg y apt e instalar dependencias
            sudo rm -f /var/lib/dpkg/lock /var/cache/apt/archives/lock /var/lib/apt/lists/lock
            sudo dpkg --add-architecture i386
            sudo apt update
            sudo apt install -y --no-install-recommends \
                python3.9 python3-pip git wget curl # wine
            sudo apt install winetricks
	    winetricks vcrun2015
	    winetricks vcrun2013

            ;;
        "arch"|"manjaro")
            print_msg "Instalando dependencias para Arch/Manjaro..." "info"
            sudo pacman -Syyu
            sudo pacman -S base-devel --needed
            sudo pacman -Sy --noconfirm \
                yay python python-pip python-virtualenv wine git wget curl
            ;;
        *)
            print_msg "Distribucion no soportada." "error"
            exit 1
            ;;
    esac || { print_msg "Error en instalacion de dependencias." "error"; exit 1; }
}

# Funcion para instalar dependencias en Wine
install_dependencies_in_wine() {
    local dependencies=("$@")
    local failed_dependencies=()
    local log_file="install_log.txt"
    
    # Crear o vaciar el archivo de log
    > "$log_file"

    # Usar la funcion existente para encontrar Python en Wine
    if ! python_exe=$(find_python_in_wine); then
        print_msg "Error: Python no encontrado en Wine." "error" | tee -a "$log_file"
        exit 1
    fi

    # Funcion interna para intentar instalar una dependencia
    install_dependency() {
        local dependency="$1"
        if ! wine "$python_exe" -m pip install --upgrade "$dependency" 2>>"$log_file"; then
            print_msg "Error al instalar $dependency. Registrado en el log." "error" | tee -a "$log_file"
            return 1
        fi
        print_msg "$dependency instalado correctamente." "success"
        return 0
    }

    # Instalar cada dependencia
    for dependency in "${dependencies[@]}"; do
        print_msg "Instalando $dependency..." "info"
        if ! install_dependency "$dependency"; then
            print_msg "No se pudo instalar $dependency..." "error"
            failed_dependencies+=("$dependency")
            # Detener si PyInstaller falla
            if [[ "$dependency" == "pyinstaller"* ]]; then
                print_msg "PyInstaller es critico. Abortando instalacion." "error"
                break
            fi
        fi
    done

    if [[ ${#failed_dependencies[@]} -ne 0 ]]; then
        print_msg "Las siguientes dependencias deben instalarse manualmente:" "error" | tee -a "$log_file"
        for dependency in "${failed_dependencies[@]}"; do
            print_msg "$dependency" "error" | tee -a "$log_file"
        done
    fi

    print_msg "Instalacion completada. Revisa el log en $log_file para más detalles." "info"
}

# Buscar Python en Wine dinamicamente
find_python_in_wine() {
    local python_exe
    for wine_path in "${WINE_PATHS[@]}"; do
        python_exe=$(find "$wine_path" -path "*/drive_c/*/Python*/python.exe" -print -quit 2>/dev/null)
        [[ -n "$python_exe" ]] && break
    done

    [[ -z "$python_exe" ]] && { 
        print_msg "Python no encontrado en Wine." "error"
        return 1
    }
    echo "$python_exe"
}

# Instalar Python en Wine
install_python_for_wine() {
    
    # Instalar Visual Studio Build Tools
    print_msg "Descargando Visual Studio Build Tools..." "info"
    wget -O vs_buildtools.exe https://aka.ms/vs/17/release/vs_buildtools.exe || return 1

    local installer="python-${PYTHON_WINE_VERSION}.exe"
    print_msg "Descargando Python ${PYTHON_WINE_VERSION}..." "info"
    wget "https://www.python.org/ftp/python/${PYTHON_WINE_VERSION}/${installer}" -O "$installer" || return 1
    

    print_msg "Instalando Python en Wine..." "info"
    wine "$installer" /quiet InstallAllUsers=0 PrependPath=1 || return 1
    wine vs_buildtools.exe --quiet --wait --norestart --nocache --installPath C:\\BuildTools --add Microsoft.VisualStudio.Workload.VCTools || return 1
    rm -f "$installer"
}

# --- Ejecucion Principal ---
main() {
    check_sudo
    install_system_dependencies

    # Configurar Wine
    if ! command_exists wine; then
        print_msg "Instalando Wine..." "info"
        install_system_dependencies  # Ya verificado en la primera llamada
    fi

    # Configurar Python en Wine
    if ! python_exe=$(find_python_in_wine); then
        install_python_for_wine || exit 1
        python_exe=$(find_python_in_wine) || exit 1
    fi

    # Instalar dependencias en Wine
    print_msg "Instalando dependencias en Wine..." "info"
    install_dependencies_in_wine pip==25.0.1 pyinstaller==5.6.0 pillow==9.5.0 pyscreeze==0.1.28 pyautogui==0.9.52 psutil==5.9.0 keyboard==0.13.5 pywin32==305 pycryptodome==3.18.0 discord_webhook==0.14.0 discord.py==2.0.0 opencv-python==4.7.0.72 sounddevice==0.4.4 scipy==1.10.0 pyTelegramBotAPI==4.7.0 PyGithub==1.56

    # Buscar PyInstaller en Wine dinamicamente
    find_pyinstaller_in_wine() {
        local pyinstaller_exe
        for wine_path in "${WINE_PATHS[@]}"; do
            pyinstaller_exe=$(find "$wine_path" -path "*/drive_c/*/Scripts/pyinstaller.exe" -print -quit 2>/dev/null)
            [[ -n "$pyinstaller_exe" ]] && break
        done

        [[ -z "$pyinstaller_exe" ]] && { 
            print_msg "PyInstaller no encontrado en Wine." "error"
            return 1
        }
        echo "$pyinstaller_exe"
    }

    # Buscar PyInstaller en Wine
    if ! pyinstaller_path=$(find_pyinstaller_in_wine "$python_exe"); then
        exit 1 # Salir si no se encuentra PyInstaller
    fi

    # Establecer PYINSTALLER_PATH
    export PYINSTALLER_PATH="$pyinstaller_path"

    # Entorno virtual local
    attempts=0
    max_attempts=2
   

    while [[ $attempts -lt $max_attempts ]]; do
        print_msg "¿Quieres configurar un entorno virtual? (s/n)" "query"
        read -r confirmation_env

        confirmation_env=$(echo "$confirmation_env" | tr '[:upper:]' '[:lower:]')

        if [[ "$confirmation_env" == "s" ]]; then
            sudo apt install -y --no-install-recommends python3-venv
            python3 -m venv .venv || { print_msg "Error al crear el entorno virtual." "error"; exit 1; }
            source .venv/bin/activate || { print_msg "Error al activar el entorno virtual." "error"; exit 1; }
            pip install -r requirements.txt || { print_msg "Error al instalar las dependencias." "error"; exit 1; }
            break
        elif [[ "$confirmation_env" == "n" ]]; then
            pip install --break-system-packages -r requirements.txt || { print_msg "Error al instalar las dependencias." "error"; exit 1; }
            break
        else
            print_msg "Entrada invalida. Vuelve a intentarlo." "query"
            ((attempts++))
        fi
    done

    # Si se agotaron los intentos y no se eligio 's' o 'n'
    if [[ $attempts -ge $max_attempts ]]; then
        print_msg "Numero maximo de intentos alcanzado.  Saliendo." "error"
        exit 1
    fi

    # Ejecutar la construccion
    print_msg "¿Quieres empezar a construir el BackDoor? (s/n)" "query"
    read -r confirmation_build

    confirmation_build=$(echo "$confirmation_build" | tr '[:upper:]' '[:lower:]')

    if [ "$confirmation_build" == "s" ]; then
        python3 builder.py || { print_msg "Error al ejecutar 'builder.py'." "error"; exit 1; }
    else
        print_msg "Configuracion completada exitosamente." "success"
    fi

}

main "$@"