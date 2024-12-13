from flask import Flask, jsonify, Response
from flask_cors import CORS
from typing import Tuple, Dict, Any
import logging
from config import API_CONFIG

app = Flask(__name__)
CORS(app)

class ControleurAPI:
    def __init__(self, serre_controller, app=None):
        self.logger = logging.getLogger("serre.api")
        self.serre = serre_controller
        self.app = app or Flask(__name__)
        CORS(self.app)
        self._configurer_routes()

    def _configurer_routes(self) -> None:
        self.app.add_url_rule(
            '/api/serre',
            'état_serre',
            self.état_serre,
            methods=['GET']
        )

    def état_serre(self) -> Tuple[Response, int]:
        try:
            état = self.serre.obtenir_état()
            return jsonify(état), 200
        except Exception as e:
            self.logger.error(f"Erreur API: {str(e)}")
            return jsonify({
                "erreur": "Erreur serveur",
                "detail": str(e)
            }), 500

    def démarrer(self) -> None:
        self.app.run(
            host=API_CONFIG['host'],
            port=int(API_CONFIG['port'])
        )
