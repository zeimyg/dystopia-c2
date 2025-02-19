#!/bin/bash
# Script para instalar WineHQ en Kali Linux de manera segura, compatible y eficiente

# Configuración de opciones de depuración y manejo de errores
set -euo pipefail

# Variables de configuración
WINE_KEY_URL="https://dl.winehq.org/wine-builds/winehq.key"
KEY_PATH="/usr/share/keyrings/winehq-archive.gpg"
LOG_FILE="/var/log/winehq_install.log"
DEPENDENCIES=(
  libgnutls30:i386 libldap-2.4-2:i386 libgpg-error0:i386
  libxml2:i386 libasound2-plugins:i386 libsdl2-2.0-0:i386
  libfreetype6:i386 libdbus-1-3:i386 libsqlite3-0:i386
)

# Configurar log: redirigir salida estándar y de error al log y a la consola
exec > >(tee -a "$LOG_FILE") 2>&1

# Verificar si se ejecuta como root; de lo contrario, reejecutar con sudo
if [ "$EUID" -ne 0 ]; then
  echo "El script no se está ejecutando como root. Intentando con sudo..."
  exec sudo "$0" "$@"
fi

# Detectar el codename de la distribución (compatibilidad con diferentes versiones)
CODENAME=$(lsb_release -cs)
echo "### Iniciando instalación de WineHQ en $CODENAME ###"

# Función para habilitar la arquitectura de 32 bits
habilitar_architectura() {
  echo "### Habilitando la arquitectura de 32 bits ###"
  dpkg --add-architecture i386 || { echo "Error: No se pudo habilitar la arquitectura i386"; exit 1; }
}

# Función para agregar la clave GPG de WineHQ de forma segura
agregar_clave_gpg() {
  echo "### Descargando y agregando la clave GPG de WineHQ ###"
  if ! wget -qO- "$WINE_KEY_URL" | gpg --dearmor > "$KEY_PATH"; then
    echo "Error: No se pudo descargar o procesar la clave GPG."
    exit 1
  fi
}

# Función para agregar el repositorio de WineHQ según el codename detectado
agregar_repositorio() {
  local repo_path="/etc/apt/sources.list.d/winehq.list"
  echo "### Agregando el repositorio de WineHQ para $CODENAME ###"
  echo "deb [signed-by=$KEY_PATH] https://dl.winehq.org/wine-builds/debian/ $CODENAME main" > "$repo_path"
}

# Función para actualizar la lista de paquetes
actualizar_paquetes() {
  echo "### Actualizando la lista de paquetes ###"
  apt update || { echo "Error: Fallo al actualizar paquetes"; exit 1; }
}

# Función para instalar WineHQ
instalar_wine() {
  echo "### Instalando WineHQ ###"
  apt install --install-recommends winehq-stable -y || { echo "Error: Fallo al instalar WineHQ"; exit 1; }

  if ! command -v wine &> /dev/null; then
    echo "Error: WineHQ no se instaló correctamente."
    exit 1
  fi
}

# Función para instalar dependencias adicionales de 32 bits
instalar_dependencias() {
  echo "### Instalando dependencias adicionales ###"
  apt install -y "${DEPENDENCIES[@]}" || { echo "Error: Fallo al instalar dependencias"; exit 1; }
}

# Función principal que orquesta la instalación
main() {
  habilitar_architectura
  agregar_clave_gpg
  agregar_repositorio
  actualizar_paquetes
  instalar_wine
  instalar_dependencias
  echo "### Instalación completada con éxito ###"
  echo "Puedes verificar la instalación ejecutando:"
  echo "  wine --version"
  echo "  winecfg"
}

main
