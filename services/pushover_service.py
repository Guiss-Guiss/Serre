import http.client
import urllib
import time
from typing import Optional
from dataclasses import dataclass
import logging
from models.exceptions import ErreurNotification
from config import PUSHOVER_CONFIG


@dataclass
class NotificationMessage:
    message: str
    priorité: int = 0
    titre: Optional[str] = None
    son: Optional[str] = None

class ServicePushover:
    def __init__(self):
        self.app_token = PUSHOVER_CONFIG["app_token"]
        self.user_key = PUSHOVER_CONFIG["user_key"]
        self.delai_min_alerte = int(PUSHOVER_CONFIG["delai_min_alerte"])
        self.logger = logging.getLogger("serre.pushover")
        self._dernière_alerte = {}
        self._dernière_tentative = 0
        self.MIN_INTERVAL = 1

    def envoyer_notification(self, notification: NotificationMessage, retry: int = 3) -> bool:
        self._respecter_rate_limit()
        self.logger.debug(f"Tentative d'envoi notification: {notification.message}")
        
        for tentative in range(retry):
            try:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                
                données = {
                    "token": self.app_token,
                    "user": self.user_key,
                    "message": notification.message,
                    "priority": notification.priorité
                }
                if notification.titre:
                    données["title"] = notification.titre
                if notification.son:
                    données["sound"] = notification.son
                
                self.logger.debug("Envoi de la requête à l'API Pushover...")
                conn.request(
                    "POST",
                    "/1/messages.json",
                    urllib.parse.urlencode(données),
                    {"Content-type": "application/x-www-form-urlencoded"}
                )
                
                resp = conn.getresponse()
                body = resp.read().decode()
                self.logger.debug(f"Réponse Pushover: Status={resp.status}, Body={body}")
                
                if resp.status == 200:
                    self.logger.info(f"Notification envoyée: {notification.message}")
                    return True
                    
                self.logger.warning(
                    f"Échec envoi (tentative {tentative + 1}/{retry}): "
                    f"Status {resp.status}, Réponse: {body}"
                )
                
            except Exception as e:
                self.logger.error(f"Erreur envoi (tentative {tentative + 1}/{retry}): {str(e)}")
                
            if tentative < retry - 1:
                time.sleep(2 ** tentative)
                
        return False

    def peut_envoyer_alerte(self, type_alerte: str) -> bool:
        maintenant = time.time()
        if type_alerte not in self._dernière_alerte:
            self._dernière_alerte[type_alerte] = 0
            return True
            
        if maintenant - self._dernière_alerte[type_alerte] > self.delai_min_alerte:
            self._dernière_alerte[type_alerte] = maintenant
            return True
            
        return False

    def _respecter_rate_limit(self) -> None:
        temps_écoulé = time.time() - self._dernière_tentative
        if temps_écoulé < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - temps_écoulé)
        self._dernière_tentative = time.time()


    def envoyer_notification(self, notification: NotificationMessage, retry: int = 3) -> bool:
        self._respecter_rate_limit()
        self.logger.debug(f"Tentative d'envoi notification: {notification.message}")
        
        for tentative in range(retry):
            try:
                self.logger.debug(f"Tentative {tentative + 1}/{retry}")
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                
                données = {
                    "token": self.app_token,
                    "user": self.user_key,
                    "message": notification.message,
                    "priority": notification.priorité
                }
                if notification.titre:
                    données["title"] = notification.titre
                if notification.son:
                    données["sound"] = notification.son
                    
                données_log = données.copy()
                données_log["token"] = "***"
                données_log["user"] = "***"
                self.logger.debug(f"Données envoyées: {données_log}")
                
                conn.request(
                    "POST",
                    "/1/messages.json",
                    urllib.parse.urlencode(données),
                    {"Content-type": "application/x-www-form-urlencoded"}
                )
                
                resp = conn.getresponse()
                body = resp.read().decode()
                self.logger.debug(f"Réponse Pushover: Status={resp.status}, Body={body}")
                
                if resp.status == 200:
                    self.logger.info(f"Notification envoyée avec succès: {notification.message}")
                    return True
                    
                self.logger.warning(
                    f"Échec envoi notification (tentative {tentative + 1}/{retry}): "
                    f"Status {resp.status}, Réponse: {body}"
                )
                
            except Exception as e:
                self.logger.error(
                    f"Erreur lors de l'envoi (tentative {tentative + 1}/{retry}): {str(e)}"
                )
                if tentative < retry - 1:
                    time.sleep(2 ** tentative) 
                
            finally:
                try:
                    conn.close()
                except:
                    pass
                    
        raise ErreurNotification(
            f"Échec de l'envoi de la notification après {retry} tentatives"
        )