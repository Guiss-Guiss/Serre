# main.py
"""
Point d'entrée principal de l'application.
"""

import threading
import time
from typing import Optional
from services.logging_service import ServiceLogging
from controllers.serre_controller import ControleurSerre
from controllers.api_controller import ControleurAPI
from models.exceptions import ErreurCapteur
from services.pushover_service import NotificationMessage

class Application:
    """
    Classe principale de l'application.
    
    Gère le cycle de vie de l'application et coordonne
    les différents composants.
    """

    def __init__(self):
        """Initialise l'application."""
        # Configuration du logging
        self.logging_service = ServiceLogging("serre")
        self.logger = self.logging_service.get_logger
        
        self.logger.info("Démarrage de l'application")
        
        # Initialisation des contrôleurs
        self.serre_controller = ControleurSerre()
        self.api_controller = ControleurAPI(self.serre_controller)
        
        # Notification de démarrage
        notification = NotificationMessage(
            "🌱 Système de gestion de la serre démarré",
            priorité=0
        )
        self.serre_controller.pushover.envoyer_notification(notification)
        
        self.echecs_consecutifs = 0
        self.SEUIL_ECHECS = 3
        
        # Thread de contrôle
        self.thread_controle: Optional[threading.Thread] = None

    def boucle_controle(self) -> None:
        """Boucle principale de contrôle."""
        self.logger.info("Démarrage de la boucle de contrôle")
        
        while not self.serre_controller.systemd.arret_en_cours:
            try:
                données = self.serre_controller.lire_capteur()
                
                if données:
                    if self.echecs_consecutifs > 0:
                        self.logger.info(
                            f"Connexion rétablie après {self.echecs_consecutifs} échecs"
                        )
                        # Notification de rétablissement
                        notification = NotificationMessage(
                            "✅ Connexion aux capteurs rétablie",
                            priorité=0
                        )
                        self.serre_controller.pushover.envoyer_notification(notification)
                        self.echecs_consecutifs = 0
                        
                    self.serre_controller.gérer_environnement(données)
                    
                else:
                    self.echecs_consecutifs += 1
                    self.logger.warning(
                        f"Aucune donnée reçue (échec {self.echecs_consecutifs}/{self.SEUIL_ECHECS})"
                    )
                    
                    if self.echecs_consecutifs >= self.SEUIL_ECHECS:
                        self.logger.error("Activation du mode sécurité")
                        notification = NotificationMessage(
                            "⚠️ Échec de lecture des capteurs - Activation du mode sécurité",
                            priorité=1
                        )
                        self.serre_controller.pushover.envoyer_notification(notification)
                        self.serre_controller.mode_sécurité()
                        
            except ErreurCapteur as e:
                self.echecs_consecutifs += 1
                self.logger.error(
                    f"Erreur lecture capteur (échec {self.echecs_consecutifs}/"
                    f"{self.SEUIL_ECHECS}): {str(e)}"
                )
                
                if self.echecs_consecutifs >= self.SEUIL_ECHECS:
                    notification = NotificationMessage(
                        f"⚠️ Erreur capteur - Activation du mode sécurité: {str(e)}",
                        priorité=1
                    )
                    self.serre_controller.pushover.envoyer_notification(notification)
                    self.serre_controller.mode_sécurité()
                    
            except Exception as e:
                self.logger.error(f"Erreur inattendue: {str(e)}")
                notification = NotificationMessage(
                    f"🚨 Erreur système inattendue - Activation du mode sécurité: {str(e)}",
                    priorité=2
                )
                self.serre_controller.pushover.envoyer_notification(notification)
                self.serre_controller.mode_sécurité()
                
            finally:
                time.sleep(60)  # Attente d'une minute entre les lectures

    def démarrer(self) -> None:
        """Démarre l'application."""
        try:
            # Démarrage du thread de contrôle
            self.thread_controle = threading.Thread(
                target=self.boucle_controle,
                daemon=True
            )
            self.thread_controle.start()
            self.logger.info("Thread de contrôle démarré")
            
            # Démarrage de l'API
            self.logger.info("Démarrage de l'API")
            self.api_controller.démarrer()
            
        except Exception as e:
            self.logger.critical(f"Erreur fatale au démarrage: {str(e)}")
            notification = NotificationMessage(
                f"🚨 Erreur fatale au démarrage: {str(e)}",
                priorité=2
            )
            self.serre_controller.pushover.envoyer_notification(notification)
            raise

    def arrêter(self) -> None:
        """Arrête l'application."""
        self.logger.info("Arrêt de l'application")
        notification = NotificationMessage(
            "⚠️ Arrêt du système de gestion de la serre",
            priorité=1
        )
        self.serre_controller.pushover.envoyer_notification(notification)
        
        if self.thread_controle and self.thread_controle.is_alive():
            self.thread_controle.join(timeout=5)
            
        self.serre_controller.nettoyer()

def main():
    """Point d'entrée du programme."""
    app = Application()
    try:
        app.démarrer()
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"Erreur fatale: {str(e)}")
    finally:
        app.arrêter()

if __name__ == "__main__":
    main()