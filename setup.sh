#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_message() {
    echo -e "${GREEN}[+]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[X]${NC} $1"
}

if [ "$EUID" -ne 0 ]; then 
    log_error "Ce script doit être exécuté en tant que root"
    exit 1
fi

log_message "Mise à jour du système..."
apt update || { log_error "Erreur lors de la mise à jour"; exit 1; }
apt upgrade -y || { log_error "Erreur lors de la mise à niveau"; exit 1; }

log_message "Installation des dépendances système..."
apt install -y \
    git \
    python3 \
    python3-flask \
    python3-flask-cors \
    python3-requests \
    python3-rpi.gpio \
    python3-dateutil \
    python3-typing-extensions \
    python3-psutil \
    python3-pytest \
    python3-pytest-cov \
    || { log_error "Erreur lors de l'installation des dépendances"; exit 1; }

log_message "Configuration du service systemd..."
cat > /etc/systemd/system/serre.service << EOL
[Unit]
Description=Système de Gestion de la Serre
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SUDO_USER
Group=gpio
WorkingDirectory=/home/$SUDO_USER
Environment=PYTHONUNBUFFERED=1
Environment=SERRE_CONFIG=/home/$SUDO_USER/serre/config.py
ExecStart=/usr/bin/python3 /home/$SUDO_USER/serre/main.py
Restart=always
RestartSec=5
TimeoutStopSec=60
StartLimitBurst=5
StartLimitIntervalSec=300


[Install]
WantedBy=multi-user.target
EOL

log_message "Configuration des permissions..."
usermod -a -G gpio $SUDO_USER || log_warning "Attention: Erreur lors de l'ajout au groupe gpio"

log_message "Création des répertoires de logs..."
mkdir -p /var/log/serre
chown $SUDO_USER:$SUDO_USER /var/log/serre

log_message "Rechargement de systemd..."
systemctl daemon-reload
systemctl enable serre.service || log_warning "Attention: Erreur lors de l'activation du service"

log_message "Vérification de l'installation..."
if python3 -c "import flask, RPi.GPIO" 2>/dev/null; then
    log_message "Installation réussie!"
    log_message "Le service peut être démarré avec: sudo systemctl start serre.service"
    log_message "Vous pouvez vérifier son état avec: sudo systemctl status serre.service"
else
    log_error "Des erreurs sont survenues lors de l'installation. Vérifiez les messages ci-dessus."
fi