import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
import signal
import shutil
from pathlib import Path
import tempfile
from services.logging_service import ServiceLogging
from services.pushover_service import ServicePushover, NotificationMessage
from services.systemd_service import ServiceSystemd



class TestServiceLogging(unittest.TestCase):

    def setUp(self):
        self.log_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: Path(self.log_dir).rmdir())

    def test_creation_logger(self):
        """Test de création du service de logging."""
        service = ServiceLogging("test")
        logger = service.get_logger
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test")

class TestServicePushover(unittest.TestCase):

    def setUp(self):
        self.service = ServicePushover()

    def test_rate_limiting(self):
        """Test du rate limiting."""
        self.assertTrue(self.service.peut_envoyer_alerte("test"))
        self.assertFalse(self.service.peut_envoyer_alerte("test"))

    @patch('http.client.HTTPSConnection')
    def test_envoi_notification(self, mock_conn):
        """Test d'envoi de notification."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_conn.return_value.getresponse.return_value = mock_response
        
        notification = NotificationMessage("Test", priorité=0)
        self.assertTrue(self.service.envoyer_notification(notification))

class TestServiceSystemd(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = Path(self.temp_dir) / "test.pid"
        
        # Create patches
        self.pid_patcher = patch('services.systemd_service.PID_FILE')
        self.mock_pid_file = self.pid_patcher.start()
        self.addCleanup(self.pid_patcher.stop)
        
        # Configure PID file mock
        self.mock_pid_file.exists.return_value = True
        
        # Create cleanup mock
        self.cleanup_mock = Mock()
        
        # Create service instance
        self.service = ServiceSystemd(self.cleanup_mock)

    def test_gestion_signal(self):
        """Test de la gestion des signaux."""
        # Reset mocks
        self.mock_pid_file.reset_mock()
        self.cleanup_mock.reset_mock()
        
        # Set up mock return values
        self.mock_pid_file.exists.return_value = True
        
        # Execute test
        with patch('sys.exit') as mock_exit:  # Prevent actual exit
            self.service._handle_shutdown(signal.SIGTERM, None)
            
            # Verify mock calls
            self.cleanup_mock.assert_called_once()
            self.mock_pid_file.exists.assert_called_once()
            self.mock_pid_file.unlink.assert_called_once()
            mock_exit.assert_called_once_with(0)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

if __name__ == '__main__':
    unittest.main()