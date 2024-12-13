import signal
import sys
import os
from typing import Optional, Callable
import logging
from config import PID_FILE

class ServiceSystemd:

    def __init__(self, gestion_nettoyage: Optional[Callable] = None):
        self.logger = logging.getLogger("serre.systemd")
        self.gestion_nettoyage = gestion_nettoyage
        self.arret_en_cours = False
        self._configurer_pid()
        self._configurer_signaux()

    def _configurer_pid(self) -> None:
        try:
            PID_FILE.write_text(str(os.getpid()))
            self.logger.info(f"Fichier PID créé: {PID_FILE}")
        except Exception as e:
            self.logger.error(f"Erreur création fichier PID: {str(e)}")
            raise

    def _configurer_signaux(self) -> None:
        signal.signal(signal.SIGTERM, self._gerer_arret)
        signal.signal(signal.SIGINT, self._gerer_arret)
        self.logger.info("Gestionnaires de signaux configurés")

    def _gerer_arret(self, signum: int, frame) -> None:
        nom_signal = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
        self.logger.info(f"Signal {nom_signal} reçu, début de l'arrêt gracieux")
        self.arret_en_cours = True

        if self.gestion_nettoyage:
            try:
                self.gestion_nettoyage()
            except Exception as e:
                self.logger.error(f"Erreur pendant le nettoyage: {str(e)}")

        try:
            existe = PID_FILE.exists()
            if existe:
                PID_FILE.unlink()
                self.logger.info("Fichier PID supprimé")
        except Exception as e:
            self.logger.error(f"Erreur suppression fichier PID: {str(e)}")

        sys.exit(0)

