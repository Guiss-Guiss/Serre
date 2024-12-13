from typing import Dict, Final
from pathlib import Path
from dataclasses import dataclass

# Chemins du système
BASE_DIR: Final[Path] = Path(__file__).parent
LOG_DIR: Final[Path] = Path("/var/log/serre")
PID_FILE: Final[Path] = Path("/var/log/serre/serre.pid")

# Configuration des GPIO
GPIO_CONFIG: Final[Dict[str, int]] = {
    'chauffage': 17,
    'eclairage': 23,
    'brumisation': 22,
    'ventilation': 27,
}

@dataclass(frozen=True)
class SeuilsEnvironnementaux:
    TEMP_MAX: float = 25.0
    TEMP_MIN: float = 18.0 
    TEMP_CRITIQUE_MAX: float = 30.0
    TEMP_CRITIQUE_MIN: float = 16.0
    HUMID_MAX: float = 60.0
    HUMID_MIN: float = 40.0
    HUMID_NORMALE: float = 50.0
@dataclass(frozen=True)
class LimitesValidation:
    TEMP_MAX: float = 50.0
    TEMP_MIN: float = -20.0
    HUMID_MAX: float = 100.0
    HUMID_MIN: float = 0.0
    PRES_MAX: float = 1200.0
    PRES_MIN: float = 800.0 

SEUILS: Final[SeuilsEnvironnementaux] = SeuilsEnvironnementaux()
LIMITES: Final[LimitesValidation] = LimitesValidation()

SEUILS_ENVIRONNEMENT: Final[Dict[str, float]] = {
    'temp_max': SEUILS.TEMP_MAX,
    'temp_min': SEUILS.TEMP_MIN,
    'temp_critique_max': SEUILS.TEMP_CRITIQUE_MAX,
    'temp_critique_min': SEUILS.TEMP_CRITIQUE_MIN,
    'humid_max': SEUILS.HUMID_MAX,
    'humid_min': SEUILS.HUMID_MIN,
    'humid_normale': SEUILS.HUMID_NORMALE,
}

HORAIRES: Final[Dict[str, int]] = {
    'heure_debut_jour': 6,
    'heure_fin_jour': 22,
}

ESP32_CONFIG: Final[Dict[str, str]] = {
    'url': "http://adresse_IP_du_ESP32/donnees",
    'timeout': "5",
}

PUSHOVER_CONFIG: Final[Dict[str, str]] = {
    'app_token': "votre_app_token",
    'user_key': "votre_user_key",
    'delai_min_alerte': "30",
}

API_CONFIG: Final[Dict[str, str]] = {
    'host': "0.0.0.0",
    'port': "5000",
}