#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// Paramètres WiFi
const char* ssid = "Votre SSID";
const char* password = "Votre mot de passe";

// Pushover settings
const char* pushoverToken = "Votre jeton  d'application";  // Remplacez par votre jeton d'application Pushover
const char* pushoverUser = "Votre clé utilisateur";  // Remplacez par votre clé utilisateur Pushover

// Capteur BME280
Adafruit_BME280 bme;
#define PRESSION_NIVEAU_MER_HPA (1013.25)

// Calibration des capteurs
const float TEMP_OFFSET = -3.7;   // Offset de température en °C
const float HUM_OFFSET = -25.0;   // Offset d'humidité en %

// Seuils de température
const float TEMP_CRITIQUE = 12.0;  // Seuil de température critique en °C

// Serveur web sur le port 80
WebServer server(80);

// Buffer pour les messages de log
char logBuffer[150];

// Variable pour suivre l'état de l'alerte
bool alerteTemperatureActive = false;
unsigned long dernierEnvoiAlerte = 0;
const unsigned long DELAI_MIN_ALERTE = 1800000; // 30 minutes en millisecondes

// Fonctions de lecture avec calibration
float lireTemperature() {
    return bme.readTemperature() - TEMP_OFFSET;
}

float lireHumidite() {
    float humidite = bme.readHumidity() - HUM_OFFSET;
    return constrain(humidite, 0.0, 100.0);  // Limite entre 0 et 100%
}

// Fonction pour envoyer une notification Pushover
void envoyerNotificationPushover(const char* message, int priority = 1) {
  HTTPClient http;
  http.begin("https://api.pushover.net/1/messages.json");
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  
  String postData = "token=" + String(pushoverToken) +
                   "&user=" + String(pushoverUser) +
                   "&message=" + String(message) +
                   "&priority=" + String(priority);
  
  int httpCode = http.POST(postData);
  
  if (httpCode > 0) {
    String payload = http.getString();
    logInfo("Notification Pushover envoyée avec succès");
  } else {
    logError("Échec de l'envoi de la notification Pushover");
  }
  
  http.end();
}

// Fonction de logging avec niveau et timestamp
void logMessage(const char* level, const char* message) {
  unsigned long currentMillis = millis();
  unsigned long seconds = currentMillis / 1000;
  unsigned long minutes = seconds / 60;
  unsigned long hours = minutes / 60;
  
  sprintf(logBuffer, "[%02lu:%02lu:%02lu][%s] %s", 
    hours, minutes % 60, seconds % 60,
    level,
    message);
  Serial.println(logBuffer);
}

void logError(const char* message) {
  logMessage("ERROR", message);
}

void logInfo(const char* message) {
  logMessage("INFO", message);
}

void logDebug(const char* message) {
  logMessage("DEBUG", message);
}

void logWarn(const char* message) {
  logMessage("WARN", message);
}

// Fonction pour formatter les valeurs flottantes en messages
void logSensorValue(const char* sensor, float value, const char* unit) {
  char valueBuffer[50];
  sprintf(valueBuffer, "%s: %.2f %s", sensor, value, unit);
  logDebug(valueBuffer);
}

// Fonction pour vérifier la température et envoyer une alerte si nécessaire
void verifierTemperature(float temperature) {
  unsigned long maintenant = millis();
  
  if (temperature < TEMP_CRITIQUE) {
    if (!alerteTemperatureActive || 
        (maintenant - dernierEnvoiAlerte > DELAI_MIN_ALERTE)) {
      char messageAlerte[100];
      sprintf(messageAlerte, "🥶 ALERTE: Température critique dans la serre: %.1f°C", temperature);
      envoyerNotificationPushover(messageAlerte, 1);
      
      alerteTemperatureActive = true;
      dernierEnvoiAlerte = maintenant;
      logWarn(messageAlerte);
    }
  } else if (alerteTemperatureActive && temperature >= TEMP_CRITIQUE + 1.0) {
    // Ajouter une hystérésis de 1°C pour éviter les oscillations
    char messageRetour[100];
    sprintf(messageRetour, "✅ RETOUR NORMAL: Température revenue à %.1f°C", temperature);
    envoyerNotificationPushover(messageRetour, 0);
    
    alerteTemperatureActive = false;
    logInfo(messageRetour);
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);  // Délai pour stabilisation
  logInfo("Démarrage du système");
  
  // Initialisation I2C
  Wire.begin(21, 22);  // SDA, SCL
  logInfo("I2C initialisé sur les pins SDA=21, SCL=22");
  
  logInfo("Initialisation BME280...");
  // Initialisation du BME280
  bool status = bme.begin(0x76);  // Essayez d'abord 0x76
  if (!status) {
    logWarn("Échec avec l'adresse 0x76, tentative avec 0x77...");
    status = bme.begin(0x77);
    if (!status) {
      logError("Impossible de trouver un capteur BME280 valide!");
      while (1) {
        delay(10000);
        logError("BME280 toujours non détecté");
      }
    }
  }
  logInfo("BME280 initialisé avec succès");
  
  // Connexion au WiFi
  logInfo("Tentative de connexion WiFi...");
  WiFi.begin(ssid, password);
  
  int tentatives = 0;
  while (WiFi.status() != WL_CONNECTED && tentatives < 20) {
    delay(1000);
    tentatives++;
    sprintf(logBuffer, "Tentative de connexion WiFi: %d/20", tentatives);
    logInfo(logBuffer);
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    sprintf(logBuffer, "Connecté au WiFi. IP: %s", WiFi.localIP().toString().c_str());
    logInfo(logBuffer);
    envoyerNotificationPushover("🌱 Système ESP32-BME280 démarré", 0);
  } else {
    logError("Échec de connexion WiFi après 20 tentatives");
    ESP.restart();
  }
  
  // Définition des routes du serveur web
  server.on("/", handleRoot);
  server.on("/donnees", handleData);
  
  // Démarrage du serveur web
  server.begin();
  logInfo("Serveur Web démarré");
}

void loop() {
  server.handleClient();
  
  // Log périodique des valeurs (toutes les 5 secondes)
  static unsigned long lastLog = 0;
  if (millis() - lastLog > 5000) {
    // Lecture et log des valeurs des capteurs
    float temperature = lireTemperature();
    float humidity = lireHumidite();
    float pressure = bme.readPressure() / 100.0F;
    
    logSensorValue("Temperature", temperature, "°C");
    logSensorValue("Humidité", humidity, "%");
    logSensorValue("Pression", pressure, "hPa");
    
    // Vérification de la température critique
    verifierTemperature(temperature);
    
    // Vérification de la connexion WiFi
    if (WiFi.status() != WL_CONNECTED) {
      logWarn("Connexion WiFi perdue!");
    }
    
    lastLog = millis();
  }
  
  delay(100);
}

void handleRoot() {
  logDebug("Requête reçue sur /");
  
  float temperature = lireTemperature();
  float humidity = lireHumidite();
  float pressure = bme.readPressure() / 1000.0F;
  
  String html = "<!DOCTYPE html><html>"
                "<head><title>Données du capteur BME280</title>"
                "<meta charset='UTF-8'>"
                "<meta http-equiv='refresh' content='5'>"
                "<style>"
                "body { font-family: Arial, sans-serif; margin: 20px; }"
                ".sensor-data { font-size: 1.2em; margin: 10px 0; }"
                "</style></head>"
                "<body>"
                "<h1>Conditions Actuelles dans la serre</h1>"
                "<div class='sensor-data'>"
                "Température: " + String(temperature) + " °C</div>"
                "<div class='sensor-data'>"
                "Humidité: " + String(humidity) + " %</div>"
                "<div class='sensor-data'>"
                "Pression: " + String(pressure) + " kPa</div>"
                "</body></html>";
                
  server.send(200, "text/html", html);
  
  // Log des valeurs envoyées
  logSensorValue("Temperature (envoyée)", temperature, "°C");
  logSensorValue("Humidité (envoyée)", humidity, "%");
  logSensorValue("Pression (envoyée)", pressure, "kPa");
}

void handleData() {
  logDebug("Requête reçue sur /donnees");
  
  float temperature = lireTemperature();
  float humidity = lireHumidite();
  float pressure = bme.readPressure() / 1000.0F;
  
  String json = "{\"temperature\":" + String(temperature) + 
                ",\"pression\":" + String(pressure) + 
                ",\"humidite\":" + String(humidity) + "}";
                
  server.send(200, "application/json", json);
  
  // Log des valeurs envoyées en JSON
  logSensorValue("Temperature (JSON)", temperature, "°C");
  logSensorValue("Humidité (JSON)", humidity, "%");
  logSensorValue("Pression (JSON)", pressure, "kPa");
}
