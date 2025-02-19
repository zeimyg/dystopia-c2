#!/usr/bin/env bash

# --- Configuracion Global ---
set -euo pipefail  # Detener en errores, variables no definidas y pipes
trap 'handle_error $? $LINENO' ERR  # Capturar errores

# Versiones y rutas configurables
PYTHON_WINE_VERSION="3.10.4"
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
    print_msg "Error en linea $line_number. Codigo de salida: $exit_code" "error"
    exit "$exit_code"
}

# Imprimir mensajes formateados
print_msg() {
    local color_code prefix msg_type
    msg_type="${2:-info}"
    msg="$1"

    case "$msg_type" in
        "success") color_code="\033[1;32m"; prefix="[+] " ;;
        "error") color_code="\033[1;31m"; prefix="[!] " ;;
        "info") color_code="\033[1;34m"; prefix="[*] " ;;
        "query") color_code="\033[1;35m"; prefix="[?] " ;;
        *) color_code="\033[0m"; prefix="" ;;
    esac

    echo -e "\n${color_code}${prefix}${msg}\033[0m" | tee -a "$LOG_FILE"
}

# Verificar comandos esenciales
check_essentials() {
    local essentials=("wget" "sudo" "dpkg" "apt")
    for cmd in "${essentials[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            print_msg "Comando critico no encontrado: $cmd" "error"
            exit 1
        fi
    done
}

# Verificar privilegios
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        print_msg "Este script debe ejecutarse como root" "error"
        exit 1
    fi
}

# --- Funciones Principales ---

# Configurar repositorios
setup_repositories() {
    print_msg "Configurando repositorios..." "info"
    
    # Agregar arquitectura de 32 bits
    dpkg --add-architecture i386 | tee -a "$LOG_FILE"
    
    # Clave de WineHQ
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor | tee /usr/share/keyrings/winehq-archive.gpg >/dev/null
    
    # Repositorio WineHQ
    echo "deb [signed-by=/usr/share/keyrings/winehq-archive.gpg] https://dl.winehq.org/wine-builds/debian/ bookworm main" | tee /etc/apt/sources.list.d/winehq.list >/dev/null
    
    # Actualizar paquetes
    apt update | tee -a "$LOG_FILE"
}

# Instalar dependencias del sistema
install_system_deps() {
    print_msg "Instalando dependencias del sistema..." "info"
    
    local packages=(
        python3 python3-pip git wget curl 
        winetricks winehq-stable
    )
    
    apt install -y --no-install-recommends "${packages[@]}" | tee -a "$LOG_FILE"
    
    # Instalar componentes de Wine
    winetricks -q vcrun2015 vcrun2013 | tee -a "$LOG_FILE"
}

# Instalar Visual Studio Build Tools
install_vs_build_tools() {
    local installer="vs_buildtools.exe"
    print_msg "Instalando Visual Studio Build Tools..." "info"
    
    wget -qO "$installer" "https://aka.ms/vs/17/release/vs_buildtools.exe" || return 1
    wine "$installer" --quiet --wait --norestart --nocache \
        --installPath "C:\\BuildTools" \
        --add Microsoft.VisualStudio.Workload.VCTools | tee -a "$LOG_FILE"
    rm -f "$installer"
}

# Configurar Python en Wine
setup_wine_python() {
    local installer="python-${PYTHON_WINE_VERSION}.exe"
    print_msg "Instalando Python $PYTHON_WINE_VERSION en Wine..." "info"
    
    wget -q "https://www.python.org/ftp/python/${PYTHON_WINE_VERSION}/${installer}" || return 1
    wine "$installer" /quiet InstallAllUsers=0 PrependPath=1 | tee -a "$LOG_FILE"
    rm -f "$installer"
}

# Instalar dependencias en Wine
install_wine_deps() {
    local python_exe
    python_exe=$(find_python_in_wine) || return 1
    
    print_msg "Instalando dependencias en Wine..." "info"
    wine "$python_exe" -m pip install --upgrade "${DEPENDENCIES[@]}" | tee -a "$LOG_FILE"
}

# Buscar ejecutables en Wine
find_in_wine() {
    local pattern="$1"
    for wine_path in "${WINE_PATHS[@]}"; do
        found=$(find "$wine_path" -path "$pattern" -print -quit 2>/dev/null)
        [[ -n "$found" ]] && { echo "$found"; return 0; }
    done
    return 1
}

find_python_in_wine() { find_in_wine "*/drive_c/*/Python*/python.exe"; }
find_pyinstaller_in_wine() { find_in_wine "*/drive_c/*/Scripts/pyinstaller.exe"; }

# Configurar entorno virtual
setup_virtualenv() {
    print_msg "Configurando entorno virtual..." "info"
    
    if ! python3 -m venv .venv; then
        print_msg "Error al crear el entorno virtual" "error"
        return 1
    fi
    
    source .venv/bin/activate
    pip install -r requirements.txt | tee -a "$LOG_FILE"
}

# --- Ejecucion Principal ---
main() {
    exec > >(tee -a "$LOG_FILE") 2>&1  # Redirigir toda la salida al log
    
    check_essentials
    check_privileges
    setup_repositories
    install_system_deps
    
    # Instalar VS Build Tools
    if ! wine "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat" -? &>/dev/null; then
        install_vs_build_tools || exit 1
    fi
    
    # Configurar Python en Wine
    if ! find_python_in_wine; then
        setup_wine_python || exit 1
    fi
    
    install_wine_deps || exit 1

    PYINSTALLER_PATH=$(find_pyinstaller_in_wine)

    # Verificar si se encontro PyInstaller
    if [[ -z "$PYINSTALLER_PATH" ]]; then
        print_msg "PyInstaller no encontrado en Wine." "error"
        exit 1
    fi

    # Exportar la variable de entorno
    export PYINSTALLER_PATH
    
    # Configurar entorno virtual
    print_msg "¿Crear entorno virtual? (s/n)" "query"
    read -r -n 1 -p " " response
    [[ "$response" =~ [sS] ]] && setup_virtualenv
    
    # Ejecutar builder
    print_msg "¿Ejecutar builder.py? (s/n)" "query"
    read -r -n 1 -p " " response
    [[ "$response" =~ [sS] ]] && python3 builder.py "$find_pyinstaller_in_wine"
    
    print_msg "Configuracion completada exitosamente" "success"
}

main "$@"