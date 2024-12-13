# 🌱 Système de Gestion de Serre Automatisé

Ce système permet de surveiller et contrôler automatiquement la température, l'humidité et l'éclairage avec des alertes en cas de conditions critiques via un Raspberry Pi Zero 2W et un ESP32.

## 📦 Matériel requis

### 📊 Système de surveillance
- 🔌 ESP32 (board compatible Arduino)
- 🌡️ Capteur BME280 (température, humidité, pression)
- 🔄 Câbles dupont femelle-femelle pour les connexions I2C
- ⚡ Alimentation USB pour l'ESP32
- 🏠 Boîtier (Répertoire 3D)

### 🎮 Système de contrôle
- 🫐 Raspberry Pi Zero 2W
- 💾 Carte microSD
- 🔌 Module relais 5V (4 canaux) : [Relais 4 canaux 5V 30A](https://a.co/d/dthXTfq)
- 🔄 Câbles dupont mâle-femelle pour les connexions GPIO
- ⚡ Alimentation 5V pour le Raspberry Pi
- 📦 Boîtier pour le Raspberry Pi et le module relais (Répertoire 3D)

## 1. Installation du système de base

### 1.1 Préparation de la carte SD

1. Téléchargez le Raspberry Pi Imager depuis [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. Lancez Raspberry Pi Imager
3. Sélectionnez "CHOOSE OS" > "Raspberry Pi OS (other)" > "Raspberry Pi OS Lite(64-bit)"
4. Cliquez sur l'icône ⚙️ pour configurer :
   - Activez SSH
   - Définissez un nom d'utilisateur et mot de passe
   - Configurez le Wi-Fi si nécessaire
   - Définissez le hostname (ex: serre-pi)
   - Définissez le fuseau horaire

### 1.2 Premier démarrage

1. Insérez la carte SD dans le Raspberry Pi
2. Connectez les câbles nécessaires
3. Attendez le démarrage complet (~1 minute)
4. Connectez-vous en SSH:
```bash
ssh votre_utilisateur@serre-pi
```

## 2. 🔧 Installation physique

### 2.1 🌡️ Connexions du BME280 sur ESP32

Le capteur BME280 utilise le protocole I2C avec les connexions suivantes :
- VIN → 3.3V
- GND → GND
- SDA → Pin 21
- SCL → Pin 22

### 2.2 ⚡ Connexions du module relais sur Raspberry Pi

#### 🔌 Alimentation
- GND → Pin 6 (GND)

#### 🎮 Connexions des relais
- IN1 → GPIO 17 (Pin 11) : Contrôle chauffage
- IN2 → GPIO 23 (Pin 16) : Contrôle éclairage
- IN3 → GPIO 22 (Pin 15) : Contrôle humidificateur
- IN4 → GPIO 27 (Pin 13) : Contrôle ventilation

🔧 Notes importantes :
- Le module relais est actif à l'état bas (LOW)
- Pas de cavalier sur le VCC (5V) du relais

### 2.3 📍 Positionnement
1. Placer le capteur BME280 à l'abri du soleil direct et des projections d'eau
2. Positionner l'ESP32 dans son boîtier
3. Installer le Raspberry Pi et le module relais dans leur boîtier
4. S'assurer de la portée WiFi
5. Connecter les appareils aux relais

## 3. 💻 Installation logicielle

### 3.1 🔔 Configuration de Pushover

1. Créer un compte sur [pushover.net](https://pushover.net)
2. Installer l'application mobile
3. Noter la clé utilisateur (User Key)
4. Créer une application pour obtenir le token
5. Configurer les tokens dans config.py :
```python
PUSHOVER_CONFIG = {
    'app_token': "votre_app_token",
    'user_key': "votre_user_key",
    'delai_min_alerte': "30",
}
```
### 3.2 Configuration du système

1. Ajustez les paramètres dans config.py selon votre installation :
```python
# Adresse de l'ESP32
ESP32_CONFIG = {
    'url': "http://Adresse_ESP32/donnees",
    'timeout': "5",
}

# Configuration Pushover
PUSHOVER_CONFIG = {
    'app_token': "votre_app_token",
    'user_key': "votre_user_key",
    'delai_min_alerte': "30",
}

```
### 3.3 Installation du système

1. Clonez le dépôt :
```bash
git clone https://github.com/Guiss-Guiss/Serre.git
cd serre
```

2. Rendez le script d'installation exécutable :
```bash
chmod +x setup.sh
```

3. Lancez l'installation automatisée :
```bash
sudo ./setup.sh
```

Le script setup.sh effectue automatiquement :
- mise à jour système
- Installation des dépendances système
- Configuration du service systemd
- Configuration des permissions GPIO
- Création des répertoires de logs

```

## 4. ✨ Fonctionnalités

- 📊 Surveillance continue des conditions environnementales
- 🌐 Interface web accessible
- 🔔 Alertes Pushover en cas de conditions critiques
- 🔄 API REST pour l'intégration
- 📝 Logs détaillés
- 🎮 Contrôle automatique des équipements
- 🤖 Automatisation intelligente

## 5. 🛠️ Maintenance

### 5.1 Maintenance générale
- Vérification régulière des capteurs
- Contrôle des logs
- Mises à jour système

### 5.2 Commandes utiles
```bash
# Voir les logs
sudo journalctl -u serre.service

# Redémarrer le service
sudo systemctl restart serre.service

# Mise à jour système
sudo apt update && sudo apt upgrade
```

## 6. ❗ Dépannage

### 6.1 Problèmes courants

1. BME280 non détecté :
   - Vérifier les connexions I2C
   - Tester les adresses 0x76 et 0x77

2. Problèmes WiFi :
   - Vérifier la force du signal
   - Contrôler les logs

3. Pushover :
   - Vérifier les tokens
   - Contrôler les logs d'envoi

4. Relais :
   - Test manuel des GPIO :
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.LOW)  # Active
GPIO.output(17, GPIO.HIGH) # Désactive
```

5. Raspberry Pi :
   - Vérifier l'alimentation
   - Contrôler le réseau
   - Examiner les logs système

### 6.2 Logs et diagnostics

- Logs service : `sudo journalctl -u serre.service`
- Logs application : `/var/log/serre/serre.log`
- État du service : `sudo systemctl status serre.service`

## 7. API REST

Endpoint principal : `GET /api/serre`
```json
{
    "temperature": "22.5",
    "humidite": "55.0",
    "pression": "1013.2",
    "chauffage": false,
    "eclairage": true,
    "ventilation": false,
    "brumisation": false,
    "mode_securite": false,
    "derniere_mise_a_jour": "2024-01-01T12:00:00"
}
```
