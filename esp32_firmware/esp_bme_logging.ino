#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <WiFi.h>
#include <WebServer.h>

// Paramètres WiFi
const char* ssid = "VOTRE_SSID_WIFI";      // Remplacer par votre SSID WiFi
const char* password = "VOTRE_MOT_DE_PASSE_WIFI";  // Remplacer par votre mot de passe WiFi

// Capteur BME280
Adafruit_BME280 bme;
#define PRESSION_NIVEAU_MER_HPA (1013.25)

// Serveur web sur le port 80
WebServer server(80);

// Buffer pour les messages de log
char logBuffer[150];

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
    float temperature = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;
    
    logSensorValue("Temperature", temperature, "°C");
    logSensorValue("Humidité", humidity, "%");
    logSensorValue("Pression", pressure, "hPa");
    
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
  
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
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
                "<h1>Conditions extérieur</h1>"
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
  
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
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
