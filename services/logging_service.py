import logging
from logging.handlers import RotatingFileHandler
from config import LOG_DIR

class ServiceLogging:

    def __init__(self, nom_logger: str = "serre"):
        self.nom_logger = nom_logger
        self.logger = logging.getLogger(nom_logger)
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        self._configurer_logger()

    def _configurer_logger(self) -> None:
        self.logger.setLevel(logging.INFO)
        
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{self.nom_logger}.log",
            maxBytes=1_000_000,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatter)
        file_handler.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        console_handler.setLevel(logging.INFO)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Service de logging initialisé")

    @property
    def get_logger(self) -> logging.Logger:

        return self.logger