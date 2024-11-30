# 🌱 Système de surveillance de serre
Ce système permet de surveiller la température, l'humidité et la pression atmosphérique dans une serre, avec des alertes en cas de conditions critiques et contrôle automatique via un Raspberry Pi Zero W.
#
## 📦 Matériel requis
#
### 📊 Système de surveillance
- 🔌 ESP32 (board compatible Arduino)
- 🌡️ Capteur BME280 (température, humidité, pression)
- 🔄 Câbles dupont femelle-femelle pour les connexions I2C
- ⚡ Alimentation USB pour l'ESP32
- 🏠 Boîtier (Répertoire 3D)
#
### 🎮 Système de contrôle
- 🫐 Raspberry Pi Zero W
- 💾 Carte microSD
- 🔌 Module relais 5V (4 canaux) : [Relais 4 canaux 5V 30A](https://a.co/d/dthXTfq) 
- 🔄 Câbles dupont mâle-femelle pour les connexions GPIO
- ⚡ Alimentation 5V pour le Raspberry Pi
- 📦 Boîtier pour le Raspberry Pi et le module relais (Répertoire 3D)
#
## 🔧 Installation physique
#
### 🌡️ Connexions du BME280 sur ESP32
Le capteur BME280 utilise le protocole I2C avec les connexions suivantes sur l'ESP32 :
- VIN → 3.3V
- GND → GND
- SDA → Pin 21
- SCL → Pin 22
### ⚡ Connexions du module relais sur Raspberry Pi
Le module relais 4 canaux (5V 30A) se connecte aux GPIO du Raspberry Pi Zero W comme suit :
#
#### 🔌 Alimentation et contrôle
GND → Pin 6 (GND)
#
#### 🎮 Connexions des relais
Par défaut, les relais sont configurés comme suit :

- IN1 → GPIO 17 (Pin 11) : Contrôle chauffage
- IN2 → GPIO 23 (Pin 16) : Contrôle éclairage
- IN3 → GPIO 22 (Pin 15) : Contrôle humidificateur
- IN4 → GPIO 27 (Pin 13) : Contrôle ventilation

🔧 Notes importantes de câblage

Le module relais est actif à l'état bas (LOW)
Assurez-vous qu'il n'y a pas de cavalier connecté sur le VCC (5V) du relais.
#
### 📍 Positionnement

##### 1. 🌡️ Placer le capteur BME280 à l'abri du soleil direct et des projections d'eau
##### 2. 🔌 Positionner l'ESP32 dans un boîtier (Répertoire 3D)
##### 3. 📦 Installer le Raspberry Pi et le module relais dans un boîtier (Répertoire 3D)
##### 4. 📡 S'assurer que les deux systèmes sont à portée du signal WiFi
##### 5. 🔌 Connecter les appareils à contrôler (ventilateurs, chauffage, etc.) aux relais
#
## 💻 Installation logicielle
#
### 🔔 Configuration de Pushover

##### 1. 📱 Créer un compte Pushover :
   - Rendez-vous sur [pushover.net](https://pushover.net)
   - Créez un compte
   - Installez l'application Pushover sur votre smartphone
   - Connectez-vous à l'application avec vos identifiants

##### 2. 🔑 Obtenir votre clé utilisateur (User Key) :
   - Connectez-vous sur [pushover.net](https://pushover.net)
   - Votre clé utilisateur est affichée sur la page principale
   - Cette clé sera utilisée comme `pushoverUser` dans le code

##### 3. 📲 Créer une application :
   - Sur pushover.net, cliquez sur "Create an Application/API Token"
   - Remplissez les informations :
     - Name: "Surveillance Serre" (ou autre nom de votre choix)
     - Type: Application
     - Description: "Système de surveillance de serre"
     - Optionnel : Uploadez une icône
   - Validez la création
   - Le token généré sera utilisé comme `pushoverToken` dans le code

##### 4. ⚙️ Configuration dans le code ESP32 :
```cpp
   const char* pushoverToken = "Votre token d'application";  // Token généré à l'étape 3
   const char* pushoverUser = "Votre clé d'utilisateur";      // Clé obtenue à l'étape 2
```

##### 5. 🧪 Test des notifications :
   - Après le déploiement, le système enverra :
     - Une notification de démarrage : "🌱 Système ESP32-BME280 démarré"
     - Des alertes en cas de température critique : "🥶 ALERTE: Température critique..."
     - Des notifications de retour à la normale : "✅ RETOUR NORMAL: Température..."
#
### ⚙️ Configuration de l'ESP32

##### 1. 📥 Installer les bibliothèques Arduino requises :
```Wire
Adafruit_Sensor
Adafruit_BME280
WiFi
WebServer
HTTPClient
```
##### 2. 🔧 Configurer les paramètres WiFi :
```cpp
   const char* ssid = "Votre SSID";
   const char* password = "Votre mot de passe";
```

##### 3. 🔔 Configurer Pushover pour les notifications :
```cpp
   const char* pushoverToken = "Votre jeton d'application";
   const char* pushoverUser = "Votre clé utilisateur";
```

##### 4. 🌡️ Ajuster le seuil de température critique si nécessaire :
```cpp
   const float TEMP_CRITIQUE = 12.0;  // Seuil en °C
```

#
### 🔄 Configuration du service système

##### 1. ⚙️ Vérifier le fichier `serre.service`  pour y modifier votre_nom_utilisateur :
```bash
   [Unit]
   Description=Service de gestion de la serre
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=votre_nom_utilisateur
   WorkingDirectory=/home/votre_nom_utilisateur
   ExecStart=/bin/bash /home/votre_nom_utilisateur/start_serre.sh
   Restart=always
   RestartSec=30

   [Install]
   WantedBy=multi-user.target
```
##### 2. ⚙️ Vérifier le fichier `start_serre.sh`  pour y modifier **votre_nom_utilisateur**:
```bash
#!/bin/bash
source /home/votre_nom_utilisateur/env/bin/activate
python /home/votre_nom_utilisateur/gestion_serre.py
```
#
### 🫐 Configuration du Raspberry Pi Zero W

##### 1. 💿 Installer Raspberry Pi OS Lite sur la carte microSD
##### 2. 🔑 Activer SSH et WiFi lors de l'installation initiale
##### 3. 🌐 Connecter le Raspberry Pi au réseau

##### 4. 📥 Installation des dépendances système :
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3-venv python3-pip git
   ```

##### 5. 🐍 Créer l'environnement Python :
   ```bash
   cd /home/votre_nom_utilisateur
   python3 -m venv env
   ```

##### 6. 📚 Installer les dépendances Python depuis requirements.txt :
```bash
   source env/bin/activate
   pip install -r requirements.txt
```

   Le fichier requirements.txt contient :
```
   RPi.GPIO
   requests
   flask
   flask_cors
   pushover
```

##### 7. 📋 Copier les fichiers de service :
```bash
   sudo cp serre.service /etc/systemd/system/
   chmod +x start_serre.sh
```

##### 8. 🔧 Configurer les permissions GPIO :
```bash
   sudo usermod -a -G gpio votre_nom_utilisateur
```
##### 9. ⚙️ Vérifier le fichier gestion_serre.py  à la ligne 92 pour y modifier **http://192.168.1.121/donnees** avec l'adresse IP du ESP32
#
## ▶️ Activer et démarrer le service :
```bash
   sudo systemctl enable serre.service
   sudo systemctl start serre.service
```
#
## ✨ Fonctionnalités

- 📊 Surveillance continue de la température, humidité et pression
- 🌐 Interface web accessible à l'adresse IP de l'ESP32
- 🔔 Alertes Pushover en cas de température critique
- 🔄 Endpoint JSON pour l'intégration avec d'autres systèmes (/donnees)
- 📝 Logs détaillés avec horodatage
- 🎮 Contrôle automatique via relais des équipements
- 🖥️ Interface de gestion sur le Raspberry Pi
- 🤖 Automatisation basée sur les données du capteur BME280
#
## 🛠️ Maintenance
#
### 🔧 Maintenance générale
- ✅ Vérifier régulièrement l'état physique du capteur
- 📊 Contrôler les logs via la console série (115200 bauds)
- 🔄 Le système redémarre automatiquement en cas de perte de connexion WiFi
- ⏰ Les alertes sont envoyées au maximum toutes les 30 minutes
#
### 🫐 Maintenance du Raspberry Pi
- 📋 Vérifier les logs :
```bash
  sudo journalctl -u serre.service
```
- ⚡ Contrôler l'état des relais périodiquement
- 🔄 Maintenir le système à jour :
```bash
  sudo apt update && sudo apt upgrade
```
#
## ❗ Dépannage

##### 1. 🌡️ Si le BME280 n'est pas détecté :
   - Vérifier les connexions I2C
   - Le code essaiera les deux adresses (0x76 et 0x77)

##### 2. 📡 Problèmes de WiFi :
   - L'ESP32 fait 20 tentatives avant de redémarrer
   - Vérifier la force du signal dans la serre

##### 3. 🔔 Si Pushover ne fonctionne pas :
   - Vérifier les tokens dans le code
   - Contrôler les logs

##### 4. ⚡ Problèmes avec les relais :
   - Vérifier les connexions GPIO
   - Contrôler les logs du service
   - Test manuel des relais :
   
```python
   import RPi.GPIO as GPIO
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(17, GPIO.OUT)
   GPIO.output(17, GPIO.LOW)  # Active le relais
   GPIO.output(17, GPIO.HIGH)   # Désactive le relais
```

##### 5. 🫐 Si le Raspberry Pi ne répond pas :
   - Vérifier l'alimentation
   - Contrôler la connexion réseau
   - Examiner les logs système
