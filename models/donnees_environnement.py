from dataclasses import dataclass
from datetime import datetime
from typing import Dict
import logging
from .exceptions import ErreurValidation

logger = logging.getLogger(__name__)

@dataclass
class DonnéesEnvironnement:
    température: float
    humidité: float
    pression: float
    horodatage: datetime = datetime.now()

    TEMP_MIN: float = -20.0
    TEMP_MAX: float = 50.0
    HUMID_MIN: float = 0.0
    HUMID_MAX: float = 100.0
    PRES_MIN: float = 800.0
    PRES_MAX: float = 1200.0

    def __post_init__(self) -> None:
        try:
            self._valider_donnees()
            logger.debug(f"Données environnementales validées: {self}")
        except ErreurValidation as e:
            logger.error(f"Erreur de validation: {e}")
            raise

    def _valider_donnees(self) -> None:
        self._valider_temperature()
        self._valider_humidite()
        self._valider_pression()

    def _valider_temperature(self) -> None:
        if not isinstance(self.température, (int, float)):
            raise ErreurValidation("La température doit être un nombre")
        if not self.TEMP_MIN <= self.température <= self.TEMP_MAX:
            raise ErreurValidation(
                f"Température {self.température}°C hors limites "
                f"[{self.TEMP_MIN}°C, {self.TEMP_MAX}°C]"
            )

    def _valider_humidite(self) -> None:
        if not isinstance(self.humidité, (int, float)):
            raise ErreurValidation("L'humidité doit être un nombre")
        if not self.HUMID_MIN <= self.humidité <= self.HUMID_MAX:
            raise ErreurValidation(
                f"Humidité {self.humidité}% hors limites "
                f"[{self.HUMID_MIN}%, {self.HUMID_MAX}%]"
            )

    def _valider_pression(self) -> None:
        if not isinstance(self.pression, (int, float)):
            raise ErreurValidation("La pression doit être un nombre")
        if not self.PRES_MIN <= self.pression <= self.PRES_MAX:
            raise ErreurValidation(
                f"Pression {self.pression}hPa hors limites "
                f"[{self.PRES_MIN}hPa, {self.PRES_MAX}hPa]"
            )

    def to_dict(self) -> Dict[str, any]:
        return {
            'température': round(self.température, 1),
            'humidité': round(self.humidité, 1),
            'pression': round(self.pression, 1),
            'horodatage': self.horodatage.isoformat()
        }