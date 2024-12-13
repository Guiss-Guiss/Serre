import unittest
from unittest.mock import Mock, patch
from controllers.serre_controller import ControleurSerre
from controllers.api_controller import ControleurAPI, app
from models.donnees_environnement import DonnéesEnvironnement
from flask import Flask
from config import API_CONFIG, GPIO_CONFIG


class TestControleurSerre(unittest.TestCase):
    def setUp(self):
        self.gpio_patcher = patch('controllers.serre_controller.GPIO', autospec=True)
        self.mock_gpio = self.gpio_patcher.start()
        self.addCleanup(self.gpio_patcher.stop)
        
        self.pid_patcher = patch('services.systemd_service.PID_FILE')
        self.mock_pid_file = self.pid_patcher.start()
        self.addCleanup(self.pid_patcher.stop)
        
        self.mock_gpio.BCM = 11
        self.mock_gpio.OUT = 0
        self.mock_gpio.HIGH = 1
        self.mock_gpio.LOW = 0
        self.mock_gpio.setup = Mock()
        self.mock_gpio.output = Mock()
        
        self.controller = ControleurSerre()
        
        self.données_test = DonnéesEnvironnement(
            température=20.0,
            humidité=50.0,
            pression=1013.0
        )

    def test_controle_relais(self):
        self.mock_gpio.reset_mock()
        
        self.controller.contrôler_relais('chauffage', True)
        
        expected_state = 0 if self.controller.RELAIS_ACTIF_BAS else 1
        self.mock_gpio.output.assert_called_once_with(
            GPIO_CONFIG['chauffage'],
            expected_state
        )

class TestControleurAPI(unittest.TestCase):
    @patch('services.systemd_service.PID_FILE')
    def setUp(self, mock_pid_file):

        self.app = Flask(__name__)
        self.serre_mock = Mock()
        self.api = ControleurAPI(self.serre_mock, app=self.app)
        self.client = self.app.test_client()

    def test_etat_serre_success(self):
        état_test = {
            "temperature": "20.0",
            "humidite": "50.0",
            "erreur": None
        }
        self.serre_mock.obtenir_état.return_value = état_test
        
        response = self.client.get('/api/serre')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), état_test)

