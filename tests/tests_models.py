import unittest
from datetime import datetime
from models.donnees_environnement import DonnéesEnvironnement
from models.exceptions import ErreurValidation

class TestDonnéesEnvironnement(unittest.TestCase):

    def setUp(self):
        self.donnees_valides = {
            'température': 20.0,
            'humidité': 50.0,
            'pression': 1013.0
        }

    def test_creation_valide(self):
        donnees = DonnéesEnvironnement(**self.donnees_valides)
        self.assertEqual(donnees.température, 20.0)
        self.assertEqual(donnees.humidité, 50.0)
        self.assertEqual(donnees.pression, 1013.0)

    def test_temperature_invalide(self):
        donnees_invalides = self.donnees_valides.copy()
        donnees_invalides['température'] = 100.0
        with self.assertRaises(ErreurValidation):
            DonnéesEnvironnement(**donnees_invalides)

    def test_humidite_invalide(self):
        donnees_invalides = self.donnees_valides.copy()
        donnees_invalides['humidité'] = 150.0
        with self.assertRaises(ErreurValidation):
            DonnéesEnvironnement(**donnees_invalides)

    def test_pression_invalide(self):
        donnees_invalides = self.donnees_valides.copy()
        donnees_invalides['pression'] = 500.0
        with self.assertRaises(ErreurValidation):
            DonnéesEnvironnement(**donnees_invalides)

    def test_conversion_dict(self):
        date_test = datetime(2024, 1, 1, 12, 0)
        donnees = DonnéesEnvironnement(
            température=20.5,
            humidité=50.5,
            pression=1013.5,
            horodatage=date_test
        )
        dict_attendu = {
            'température': 20.5,
            'humidité': 50.5,
            'pression': 1013.5,
            'horodatage': '2024-01-01T12:00:00'
        }
        self.assertEqual(donnees.to_dict(), dict_attendu)

if __name__ == '__main__':
    unittest.main()