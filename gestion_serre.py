import RPi.GPIO as GPIO
import requests
from dataclasses import dataclass
from typing import Dict, Optional
import time
import logging
from logging.handlers import RotatingFileHandler
import threading
from datetime import datetime, time as dtime
from flask import Flask, jsonify
from flask_cors import CORS
import http.client
import urllib
import json
import subprocess

app = Flask(__name__)
CORS(app)

# Classe pour les données de l'environnement
@dataclass
class DonnéesEnvironnement:
    température: float
    humidité: float
    pression: float

# Classe pour la gestion des notifications Pushover
class GestionnairePushover:
    def __init__(self):
        self.APP_TOKEN = "a6wyghegybu13ffhcuv4c5p8d8usxy"   # Remplacer par votre clé d'application
        self.USER_KEY = "u4qgs6ppwbe1o2vbz8oxepzohyxpeh"    # Remplacer par votre clé utilisateur
        self.logger = logging.getLogger('serre.pushover')
        self._dernière_alerte = {
            'temp_basse': 0,
            'temp_haute': 0
        }
        self.DÉLAI_MIN_ALERTE = 30

    def envoyer_notification(self, message: str, priorité: int = 0) -> bool:
        try:
            conn = http.client.HTTPSConnection("api.pushover.net:443")
            conn.request("POST", "/1/messages.json",
                urllib.parse.urlencode({
                    "token": self.APP_TOKEN,
                    "user": self.USER_KEY,
                    "message": message,
                    "priority": priorité
                }), {"Content-type": "application/x-www-form-urlencoded"})
            resp = conn.getresponse()

            if resp.status == 200:
                self.logger.info(f"Notification Pushover envoyée avec succès: {message}")
                return True
            else:
                self.logger.error(f"Échec envoi Pushover ({resp.status}): {message}")
                return False

        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi de la notification Pushover: {str(e)}")
            return False

    def peut_envoyer_alerte(self, type_alerte: str) -> bool:
        maintenant = time.time()
        if maintenant - self._dernière_alerte[type_alerte] > self.DÉLAI_MIN_ALERTE:
            self._dernière_alerte[type_alerte] = maintenant
            return True
        return False

# Classe principale de gestion de la serre
class GestionnaireSerre:
    def __init__(self):
        self.RELAIS = {
            'chauffage': 17,    # GPIO 17, PIN 11, relais chauffage
            'éclairage': 23,    # GPIO 23, PIN 16, relais éclairage
            'brumisation': 22,  # GPIO 22, PIN 15, relais brumisation
            'ventilation': 27,  # GPIO 27. PIN 13, relais ventilation
        }

        self.SEUILS = {
            'temp_max': 25.0,           # Température maximale
            'temp_min': 18.0,           # Température minimale
            'temp_critique_max': 30.0,  # Température critique haute
            'temp_critique_min': 16.0,  # Température critique basse
            'humid_max': 60.0,          # Humidité maximale
            'humid_min': 40.0,          # Humidité minimale
            'humid_normale': 50.0,      # Humidité normale
            'heure_début_jour': 6,      # Heure de début de la période de jour
            'heure_fin_jour': 22        # Heure de fin de la période de jour
        }

        self.ESP32_URL = "http://192.168.1.121/donnees" # Remplacer par l'adresse IP de l'ESP32
        self.configurer_logging()
        self.logger = logging.getLogger('serre')
        self.configurer_gpio()
        self.pushover = GestionnairePushover()

        self.en_mode_sécurité = False
        self.alerte_temp_haute = False
        self.alerte_temp_basse = False
        self.RELAIS_ACTIF_BAS = True

    def configurer_logging(self):
        try:
            logger = logging.getLogger('serre')
            logger.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            
            gestionnaire_fichier = RotatingFileHandler(
                'serre.log',
                maxBytes=1_000_000, 
                backupCount=5,
                encoding='utf-8'
            )
            gestionnaire_fichier.setLevel(logging.INFO)
            gestionnaire_fichier.setFormatter(formatter)

            gestionnaire_console = logging.StreamHandler()
            gestionnaire_console.setLevel(logging.INFO)
            gestionnaire_console.setFormatter(formatter)

            logger.addHandler(gestionnaire_fichier)
            logger.addHandler(gestionnaire_console)

            logger.info("Système de logging initialisé")

        except Exception as e:
            print(f"Erreur critique lors de l'initialisation du logging: {str(e)}")
            raise

    def configurer_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for nom_relais, pin in self.RELAIS.items():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
                self.logger.info(f"GPIO {pin} configuré pour le relais {nom_relais}")
            self.logger.info("Configuration GPIO terminée avec succès")
        except Exception as e:
            self.logger.critical(f"Erreur fatale lors de la configuration GPIO: {str(e)}", exc_info=True)
            raise

    def lire_capteur(self) -> Optional[DonnéesEnvironnement]:
            self.logger.debug(f"Tentative de lecture du capteur à l'URL: {self.ESP32_URL}")
            try:
                headers = {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
                réponse = requests.get(self.ESP32_URL, timeout=3, headers=headers)
                self.logger.debug(f"Code de réponse: {réponse.status_code}")
                self.logger.debug(f"Contenu de la réponse: {réponse.text}")
                
                if réponse.status_code != 200:
                    self.logger.error(f"Erreur HTTP lors de la lecture du capteur: {réponse.status_code}")
                    return None

                try:
                    données = réponse.json()
                except json.JSONDecodeError as e:
                    self.logger.error(f"Erreur de décodage JSON: {e}\nRéponse reçue: {réponse.text}")
                    return None

                température= float(données.get('temperature', 0))
                pression = float(données.get('pression', 0))
                humidité = float(données.get('humidite', 0))

                if not (température and pression and humidité):
                    self.logger.error(f"Données invalides reçues: {données}")
                    return None

                if not (-40 <= température<= 80 and
                        300 <= pression <= 1100 and
                        0 <= humidité <= 100):
                    self.logger.warning(f"Valeurs hors plages normales: T={température}°C, P={pression}hPa, H={humidité}%")

                return DonnéesEnvironnement(
                    température,
                    humidité,
                    pression
                )

            except requests.Timeout:
                self.logger.error(f"Timeout lors de la lecture du capteur ({self.ESP32_URL})")
                return None
            except requests.ConnectionError as e:
                self.logger.error(f"Erreur de connexion au capteur: {str(e)}")
                self.logger.debug("Vérifiez que l'ESP32 est accessible sur le réseau")
                return None
            except Exception as e:
                self.logger.error(f"Erreur inattendue lors de la lecture du capteur: {str(e)}", exc_info=True)
                return None

    def contrôler_relais(self, nom_relais: str, activer: bool):
        if nom_relais in self.RELAIS:
            try:
                état_gpio = not activer if self.RELAIS_ACTIF_BAS else activer
                GPIO.output(self.RELAIS[nom_relais], état_gpio)
                self.logger.info(
                    f"Relais {nom_relais} {'activé' if activer else 'désactivé'} "
                    f"(GPIO {self.RELAIS[nom_relais]} = {état_gpio})"
                )
            except Exception as e:
                self.logger.error(f"Erreur lors du contrôle du relais {nom_relais}", exc_info=True)
                raise
        else:
            self.logger.error(f"Tentative de contrôle d'un relais inconnu: {nom_relais}")

    def est_période_jour(self) -> bool:
        try:
            heure_actuelle = datetime.now().time()
            heure_début = dtime(self.SEUILS['heure_début_jour'], 0)
            heure_fin = dtime(self.SEUILS['heure_fin_jour'], 0)
            
            est_jour = heure_début <= heure_actuelle <= heure_fin
            
            self.logger.debug(
                f"Vérification période éclairage - "
                f"Début: {heure_début.strftime('%H:%M')}, "
                f"Fin: {heure_fin.strftime('%H:%M')}, "
                f"Actuelle: {heure_actuelle.strftime('%H:%M')}, "
                f"Est jour: {est_jour}"
            )
            return est_jour

        except Exception as e:
            self.logger.error(
                "Erreur lors de la vérification de la période d'éclairage", 
                exc_info=True
            )
            return False

    def gérer_température_critique(self, température: float) -> None:
        try:
            if température < self.SEUILS['temp_critique_min']:
                if not self.alerte_temp_basse and self.pushover.peut_envoyer_alerte('temp_basse'):
                    message = f"🥶 ALERTE: Température critique basse dans la serre: {température}°C"
                    self.pushover.envoyer_notification(message, priorité=1)
                    self.alerte_temp_basse = True
            elif température > self.SEUILS['temp_critique_max']:
                if not self.alerte_temp_haute and self.pushover.peut_envoyer_alerte('temp_haute'):
                    message = f"🔥 ALERTE: Température critique haute dans la serre: {température}°C"
                    self.pushover.envoyer_notification(message, priorité=1)
                    self.alerte_temp_haute = True
            else:
                if self.alerte_temp_basse or self.alerte_temp_haute:
                    message = f"✅ RETOUR NORMAL: Température revenue à {température}°C (dans les limites acceptables)"
                    self.pushover.envoyer_notification(message, priorité=0)
                    self.alerte_temp_basse = False
                    self.alerte_temp_haute = False
        except Exception as e:
            self.logger.error("Erreur dans la gestion des alertes température", exc_info=True)

    def gérer_chauffage(self, température: float) -> None:
        try:
            if température < self.SEUILS['temp_min']:
                self.logger.warning(f"Température trop basse: {température}°C < {self.SEUILS['temp_min']}°C")
                self.contrôler_relais('chauffage', True)
            else:
                self.contrôler_relais('chauffage', False)
        except Exception as e:
            self.logger.error("Erreur dans la gestion du chauffage", exc_info=True)
            self.contrôler_relais('chauffage', False)

    def gérer_ventilation(self, température: float, humidité: float) -> None:
        try:
            ventilation_requise = False

            # Ventilation pour température
            if température > self.SEUILS['temp_max']:
                self.logger.warning(f"Température trop élevée: {température}°C > {self.SEUILS['temp_max']}°C")
                ventilation_requise = True
            elif température < self.SEUILS['temp_min']:
                self.logger.warning(f"Température trop basse: {température}°C < {self.SEUILS['temp_min']}°C")
                ventilation_requise = False
            
            # Ventilation pour humidité
            if humidité > self.SEUILS['humid_max'] and self.SEUILS['temp_min'] < température < self.SEUILS['temp_max']:
                self.logger.warning(f"Humidité trop élevée: {humidité}% > {self.SEUILS['humid_max']}%")
                ventilation_requise = True

            self.contrôler_relais('ventilation', ventilation_requise)
            
            if not ventilation_requise:
                self.logger.info("Conditions dans les limites normales")

        except Exception as e:
            self.logger.error("Erreur dans la gestion de la ventilation", exc_info=True)
            self.contrôler_relais('ventilation', False)

    def gérer_humidité(self, humidité: float) -> None:
        try:
            if humidité < self.SEUILS['humid_normale']:
                self.logger.warning(f"Humidité trop basse: {humidité}% < {self.SEUILS['humid_normale']}%")
                self.contrôler_relais('brumisation', True)
            else:
                self.contrôler_relais('brumisation', False)
        except Exception as e:
            self.logger.error("Erreur dans la gestion de l'humidité", exc_info=True)
            self.contrôler_relais('brumisation', False)

    def contrôler_éclairage(self):
        try:
            if self.est_période_jour():
                self.contrôler_relais('éclairage', True)
                self.logger.info("Période de jour, éclairage activé")
            else:
                self.contrôler_relais('éclairage', False)
                self.logger.info("Période de nuit, éclairage désactivé")
        except Exception as e:
            self.logger.error("Erreur dans le contrôle de l'éclairage", exc_info=True)
            self.contrôler_relais('éclairage', False)

    def gérer_mode_sécurité(self, données: DonnéesEnvironnement) -> None:
        try:
            if self.en_mode_sécurité and données:
                message = "✅ FIN ALERTE: Système sorti du mode sécurité, fonctionnement normal rétabli"
                self.pushover.envoyer_notification(message, priorité=0)
                self.en_mode_sécurité = False
        except Exception as e:
            self.logger.error("Erreur dans la gestion du mode sécurité", exc_info=True)

    def gérer_environnement(self, données: DonnéesEnvironnement) -> None:
            if not données:
                self.logger.error("Données nulles reçues, activation du mode sécurité")
                self.mode_sécurité()
                return

            try:
                self.logger.info(f"Gestion environnement - T: {données.température}°C, H: {données.humidité}%, P: {données.pression}kPa")

                # Gestion des différents aspects de l'environnement
                self.gérer_température_critique(données.température)
                self.gérer_chauffage(données.température)
                self.gérer_ventilation(données.température, données.humidité)
                self.gérer_humidité(données.humidité)
                self.contrôler_éclairage()
                self.gérer_mode_sécurité(données)

            except Exception as e:
                self.logger.error("Erreur lors de la gestion de l'environnement", exc_info=True)
                self.mode_sécurité()

    def mode_sécurité(self):
        if not self.en_mode_sécurité:
            self.logger.warning("ACTIVATION DU MODE SÉCURITÉ")
            try:
                self.contrôler_relais('chauffage', True)
                self.contrôler_relais('ventilation', False)
                self.contrôler_relais('brumisation', False)
                self.contrôler_relais('éclairage', not self.est_période_jour())
                
                self.logger.info("Mode sécurité appliqué avec succès")
                message = "⚠️ ALERTE: Mode sécurité activé dans la serre"
                self.pushover.envoyer_notification(message, priorité=1)
                self.en_mode_sécurité = True

            except Exception as e:
                self.logger.critical("Erreur lors de l'activation du mode sécurité", exc_info=True)

    def obtenir_état_actuel(self):
        self.logger.debug("Récupération de l'état actuel du système")
        try:
            données = self.lire_capteur()
            état = {
                "température_serre": f"{données.température:.1f}" if données else "N/A",
                "humidité_serre": f"{données.humidité:.1f}" if données else "N/A",
                "pression_serre": f"{données.pression:.1f}" if données else "N/A",
                "chauffage_serre": not GPIO.input(self.RELAIS['chauffage']),
                "éclairage_serre": not GPIO.input(self.RELAIS['éclairage']),
                "ventilation_serre": not GPIO.input(self.RELAIS['ventilation']),
                "brumisation_serre": not GPIO.input(self.RELAIS['brumisation']),
                "dernier_update_serre": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "erreur_serre": None if données else "Erreur de lecture des capteurs"
            }
            self.logger.info(f"État actuel du système: {état}")
            return état
        except Exception as e:
            self.logger.error("Erreur lors de la récupération de l'état", exc_info=True)
            return {
                "température_serre": "N/A",
                "humidité_serre": "N/A",
                "pression_serre": "N/A",
                "chauffage_serre": False,
                "éclairage_serre": False,
                "ventilation_serre": False,
                "brumisation_serre": False,
                "dernier_update_serre": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "erreur_serre": str(e)
            }

    def nettoyer(self):
        self.logger.info("Début du nettoyage du système")
        try:
            for relais in self.RELAIS:
                self.contrôler_relais(relais, False)
            GPIO.cleanup()
            self.logger.info("Nettoyage GPIO terminé avec succès")
        except Exception as e:
            self.logger.error("Erreur lors du nettoyage", exc_info=True)

# Variables globales et routes API
gestionnaire_serre = None

@app.route('/api/serre', methods=['GET'])
def api_serre():
    logger = logging.getLogger('serre')
    logger.debug("Requête API reçue pour l'état de la serre")
    try:
        return jsonify(gestionnaire_serre.obtenir_état_actuel())
    except Exception as e:
        logger.error("Erreur lors du traitement de la requête API", exc_info=True)
        return jsonify({
            "température_serre": "N/A",
            "humidité_serre": "N/A",
            "pression_serre": "N/A",
            "chauffage_serre": False,
            "éclairage_serre": False,
            "ventilation_serre": False,
            "brumisation_serre": False,
            "dernier_update_serre": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "erreur_serre": str(e)
        }), 500

def boucle_contrôle():
    logger = logging.getLogger('serre')
    logger.info("Démarrage de la boucle de contrôle")

    echecs_consecutifs = 0
    SEUIL_ECHECS = 3

    while True:
        try:
            données = gestionnaire_serre.lire_capteur()
            if données:
                if echecs_consecutifs > 0:
                    logger.info(f"Connexion rétablie après {echecs_consecutifs} échecs")
                    echecs_consecutifs = 0
                gestionnaire_serre.gérer_environnement(données)
            else:
                echecs_consecutifs += 1
                logger.warning(f"Aucune donnée reçue des capteurs (échec {echecs_consecutifs}/{SEUIL_ECHECS})")
                
                if echecs_consecutifs >= SEUIL_ECHECS:
                    logger.error(f"Activation du mode sécurité après {SEUIL_ECHECS} échecs consécutifs")
                    gestionnaire_serre.mode_sécurité()
                else:
                    logger.info(f"En attente de la prochaine tentative ({SEUIL_ECHECS - echecs_consecutifs} restantes avant mode sécurité)")

        except Exception as e:
            echecs_consecutifs += 1
            logger.error(f"Erreur dans la boucle de contrôle (échec {echecs_consecutifs}/{SEUIL_ECHECS}): {str(e)}")
            
            if echecs_consecutifs >= SEUIL_ECHECS:
                logger.error(f"Activation du mode sécurité après {SEUIL_ECHECS} échecs consécutifs")
                gestionnaire_serre.mode_sécurité()

        finally:
            time.sleep(60)

def planifier_reboot():
    logger = logging.getLogger('serre')
    logger.info("Démarrage du planificateur de reboot")

    while True:
        try:
            maintenant = datetime.now()
            if maintenant.hour == 12 and maintenant.minute == 0:
                logger.info("Heure du reboot journalier (12:00)")
                if gestionnaire_serre:
                    message = "🔄 Redémarrage quotidien programmé du système"
                    gestionnaire_serre.pushover.envoyer_notification(message, priorité=0)
                    time.sleep(5)
                
                logger.info("Exécution du reboot système")
                subprocess.run(['sudo', 'reboot'])

            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Erreur dans le planificateur de reboot: {str(e)}")
            time.sleep(60)

def main():
    logger = logging.getLogger('serre')
    try:
        global gestionnaire_serre
        logger.info("Démarrage du système de gestion de la serre")
        gestionnaire_serre = GestionnaireSerre()

        message = "🌱 Système de gestion de la serre démarré"
        gestionnaire_serre.pushover.envoyer_notification(message, priorité=0)

        thread_controle = threading.Thread(target=boucle_contrôle, daemon=True)
        thread_controle.start()
        logger.info("Thread de contrôle démarré")

        thread_reboot = threading.Thread(target=planifier_reboot, daemon=True)
        thread_reboot.start()
        logger.info("Thread de planification du reboot démarré")

        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.critical("Erreur fatale dans la fonction principale", exc_info=True)
        if gestionnaire_serre:
            message = "❌ Erreur critique du système de gestion de la serre"
            gestionnaire_serre.pushover.envoyer_notification(message, priorité=2)
    finally:
        if gestionnaire_serre:
            logger.info("Nettoyage du système avant arrêt")
            gestionnaire_serre.nettoyer()

if __name__ == "__main__":
    main()