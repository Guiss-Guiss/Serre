import threading
from typing import Optional, Dict, Any
from datetime import datetime, time as dtime
import logging
import RPi.GPIO as GPIO
from models.donnees_environnement import DonnéesEnvironnement
from models.exceptions import ErreurRelais, ErreurCapteur
from services.pushover_service import ServicePushover, NotificationMessage
from services.systemd_service import ServiceSystemd
from config import GPIO_CONFIG, SEUILS_ENVIRONNEMENT, HORAIRES, ESP32_CONFIG

class ControleurSerre:
    def __init__(self):
        self.logger = logging.getLogger("serre.controller")
        self.pushover = ServicePushover()
        self.systemd = ServiceSystemd(cleanup_handler=self.nettoyer)
        
        self.en_mode_sécurité = False
        self.alerte_temp_haute = False
        self.alerte_temp_basse = False
        self.RELAIS_ACTIF_BAS = True
        
        self._initialiser_gpio()
        self._dernieres_donnees: Optional[DonnéesEnvironnement] = None
        self._verrou = threading.Lock()

    def _initialiser_gpio(self) -> None:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for nom_relais, pin in GPIO_CONFIG.items():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
                self.logger.info(f"GPIO {pin} configuré pour {nom_relais}")
        except Exception as e:
            self.logger.critical(f"Erreur fatale GPIO: {str(e)}")
            raise ErreurRelais("Échec de l'initialisation GPIO")

    def contrôler_relais(self, nom_relais: str, activer: bool) -> None:
        with self._verrou:
            try:
                if nom_relais not in GPIO_CONFIG:
                    raise ErreurRelais(f"Relais inconnu: {nom_relais}")
                
                # Si RELAIS_ACTIF_BAS est True, on inverse l'état
                état_gpio = GPIO.HIGH if (activer != self.RELAIS_ACTIF_BAS) else GPIO.LOW
                GPIO.output(GPIO_CONFIG[nom_relais], état_gpio)
                
                self.logger.info(
                    f"Relais {nom_relais} {'activé' if activer else 'désactivé'}"
                )
                
            except Exception as e:
                self.logger.error(f"Erreur contrôle relais {nom_relais}: {str(e)}")
                raise ErreurRelais(f"Échec contrôle relais {nom_relais}")

    def lire_capteur(self) -> Optional[DonnéesEnvironnement]:
        try:
            import requests
            response = requests.get(
                ESP32_CONFIG['url'],
                timeout=int(ESP32_CONFIG['timeout'])
            )
            
            if response.status_code != 200:
                raise ErreurCapteur(f"Erreur HTTP: {response.status_code}")
                
            données = response.json()
            
            self._dernieres_donnees = DonnéesEnvironnement(
                température=float(données['temperature']),
                humidité=float(données['humidite']),
                pression=float(données['pression']) * 10
            )
            
            return self._dernieres_donnees
            
        except Exception as e:
            self.logger.error(f"Erreur lecture capteur: {str(e)}")
            raise ErreurCapteur(f"Échec lecture capteur: {str(e)}")

    def est_période_jour(self) -> bool:
        heure_actuelle = datetime.now().time()
        return dtime(
            # Gestion normale des équipements
        ) <= heure_actuelle <= dtime(
            HORAIRES['heure_fin_jour']
        )

    def mode_sécurité(self) -> None:
        if not self.en_mode_sécurité:
            self.logger.warning("ACTIVATION MODE SÉCURITÉ")
            try:
                self.contrôler_relais('chauffage', True)
                self.contrôler_relais('ventilation', False)
                self.contrôler_relais('brumisation', False)
                self.contrôler_relais('eclairage', not self.est_période_jour())
                
                notification = NotificationMessage(
                    "⚠️ ALERTE: Mode sécurité activé dans la serre",
                    priorité=1
                )
                self.pushover.envoyer_notification(notification)
                
                self.en_mode_sécurité = True
                
            except Exception as e:
                self.logger.critical(f"Erreur mode sécurité: {str(e)}")

    def gérer_environnement(self, données: DonnéesEnvironnement) -> None:
        try:
            self.logger.info(
                f"Gestion environnement - T: {données.température}°C, "
                f"H: {données.humidité}%, P: {données.pression}hPa"
            )

            if self.en_mode_sécurité:
                notification = NotificationMessage(
                    "✅ FIN ALERTE: Connexion capteurs rétablie",
                    priorité=0
                )
                self.pushover.envoyer_notification(notification)
                self.en_mode_sécurité = False

            self._gérer_alertes_température(données.température)

            self._gérer_chauffage(données)
            self._gérer_ventilation(données)
            self._gérer_brumisation(données)
            self._gérer_eclairage()

        except ErreurCapteur as e:
            self.logger.error(f"Erreur lecture capteur: {str(e)}")
            self.mode_sécurité()
        except Exception as e:
            self.logger.error(f"Erreur inattendue: {str(e)}")
            self.mode_sécurité()

    def _gérer_alertes_température(self, température: float) -> None:
        if température < SEUILS_ENVIRONNEMENT['temp_critique_min']:
            if not self.alerte_temp_basse and self.pushover.peut_envoyer_alerte('temp_basse'):
                self.logger.debug("Envoi alerte température basse")
                notification = NotificationMessage(
                    f"🥶 ALERTE: Température critique basse: {température}°C",
                    priorité=1
                )
                if self.pushover.envoyer_notification(notification):
                    self.alerte_temp_basse = True
                    
        elif température > SEUILS_ENVIRONNEMENT['temp_critique_max']:
            if not self.alerte_temp_haute and self.pushover.peut_envoyer_alerte('temp_haute'):
                self.logger.debug("Envoi alerte température haute")
            # Gestion normale des équipements
                notification = NotificationMessage(
                    f"🔥 ALERTE: Température critique haute: {température}°C",
                    priorité=1
                )
                if self.pushover.envoyer_notification(notification):
                    self.alerte_temp_haute = True
                    
        else:
            if self.alerte_temp_basse or self.alerte_temp_haute:
                notification = NotificationMessage(
                    f"✅ RETOUR NORMAL: Température: {température}°C",
                    priorité=0
                )
                if self.pushover.envoyer_notification(notification):
                    self.alerte_temp_basse = False
                    self.alerte_temp_haute = False

    def _gérer_chauffage(self, données: DonnéesEnvironnement) -> None:
        self.contrôler_relais('chauffage', données.température < SEUILS_ENVIRONNEMENT['temp_min'])
            

    def _gérer_ventilation(self, données: DonnéesEnvironnement) -> None:
        ventilation_nécessaire = (
            données.température > SEUILS_ENVIRONNEMENT['temp_max'] or
            (données.humidité > SEUILS_ENVIRONNEMENT['humid_max'] and
             SEUILS_ENVIRONNEMENT['temp_min'] < données.température < SEUILS_ENVIRONNEMENT['temp_max'])
        )
        self.contrôler_relais('ventilation', ventilation_nécessaire)

    def _gérer_brumisation(self, données: DonnéesEnvironnement) -> None:
        brumisation_nécessaire = données.humidité < SEUILS_ENVIRONNEMENT['humid_normale']
        self.contrôler_relais('brumisation', brumisation_nécessaire)

    def _gérer_eclairage(self) -> None:
        self.contrôler_relais('eclairage', self.est_période_jour())

    def obtenir_état(self) -> Dict[str, Any]:
        try:
            données = self._dernieres_donnees
            return {
                "temperature": f"{données.température:.1f}" if données else "N/A",
                "humidite": f"{données.humidité:.1f}" if données else "N/A",
                "pression": f"{données.pression:.1f}" if données else "N/A",
                "chauffage": not GPIO.input(GPIO_CONFIG['chauffage']),
                "eclairage": not GPIO.input(GPIO_CONFIG['eclairage']),
                "ventilation": not GPIO.input(GPIO_CONFIG['ventilation']),
                "brumisation": not GPIO.input(GPIO_CONFIG['brumisation']),
                "derniere_mise_a_jour": datetime.now().isoformat(),
                "mode_securite": self.en_mode_sécurité,
                "erreur": None
            }
        except Exception as e:
            self.logger.error(f"Erreur obtention état: {str(e)}")
            return {
                "erreur": str(e),
                "derniere_mise_a_jour": datetime.now().isoformat()
            }

    def nettoyer(self) -> None:
        """Nettoyage des ressources."""
        self.logger.info("Nettoyage du système")
        try:
            for nom_relais in GPIO_CONFIG:
                self.contrôler_relais(nom_relais, False)
            GPIO.cleanup()
            self.logger.info("Nettoyage terminé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur pendant le nettoyage: {str(e)}")