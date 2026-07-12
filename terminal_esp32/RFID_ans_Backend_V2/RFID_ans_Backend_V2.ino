#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- HARDWARE CONFIGURATION ---
#define SS_PIN    12  // RFID SDA/SS Pin
#define RST_PIN   13  // RFID Reset Pin
#define BUZZER_PIN 4  // Piezo Buzzer Pin

// OLED Display Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C // Typische I2C-Adresse für 0.96" OLEDs

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
MFRC522 rfrc522(SS_PIN, RST_PIN);

// --- NETWORK CONFIGURATION ---
// Hier sind jetzt beide WLANs hinterlegt (0 = Primär, 1 = Backup)
const int NUM_NETWORKS = 2;
const char* ssids[NUM_NETWORKS] = {"PRIMARY_WLAN", "Vodafone-D63A"};
const char* passwords[NUM_NETWORKS] = {"Carla+2012", "Voradelberg+20"};

const char* serverUrl = "http://192.168.0.179:80/api/terminal/toggle/"; 

// --- TIMING FOR RFID READS ---
unsigned long lastScanTime = 0;
const unsigned long scanDelay = 2000; 

// --- DISPLAY HELPER FUNCTIONS ---
void updateDisplay(String line1, String line2, String line3 = "") {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  
  // Zeile 1 (Überschrift / Status)
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(line1);
  
  // Trennlinie
  display.drawFastHLine(0, 12, 128, SSD1306_WHITE);
  
  // Zeile 2 (Hauptinhalt, etwas größer)
  display.setTextSize(2);
  display.setCursor(0, 20);
  display.println(line2);
  
  // Zeile 3 (Zusatzinfo)
  if (line3 != "") {
    display.setTextSize(1);
    display.setCursor(0, 48);
    display.println(line3);
  }
  
  display.display();
}

void showReadyMessage() {
  showReadyMessage("STEMPELUHR READY");
}

// Überladene Funktion, um den Netzwerknamen im Bereitschaftsmodus anzuzeigen
void showReadyMessage(String statusText) {
  updateDisplay(statusText, "Bitte Karte", "anlegen...");
}

// --- BUZZER FUNCTIONS ---
void playTone(int frequency, int duration) {
  tone(BUZZER_PIN, frequency, duration);
  delay(duration);
  noTone(BUZZER_PIN);
}

void signalSuccess() {
  playTone(2000, 150);
}

void signalWarning() {
  playTone(1000, 100); delay(50); playTone(1000, 100);
}

void signalError() {
  playTone(400, 500);
}

// --- WLAN VERBINDUNGS-LOGIK ---
void connectToWiFi() {
  for (int i = 0; i < NUM_NETWORKS; i++) {
    Serial.print("Versuche Verbindung mit: ");
    Serial.println(ssids[i]);
    
    updateDisplay("BOOTING...", "Verbinde", ssids[i]);
    
    WiFi.begin(ssids[i], passwords[i]);
    
    int maxAttempts = 15; // 15 Versuche x 500ms = 7.5 Sekunden pro WLAN
    int attempts = 0;
    
    while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWLAN verbunden!");
      String okMsg = "WLAN OK: " + String(ssids[i]);
      updateDisplay("BEREIT", "Erfolgreich", "verbunden!");
      return; // Verbindung steht, breche die Schleife ab
    }
    
    Serial.println("\nVerbindung fehlgeschlagen. Versuche nächstes Netzwerk...");
  }
  
  // Wenn kein WLAN funktioniert hat
  updateDisplay("CRITICAL ERROR", "Kein WLAN", "verfügbar!");
  signalError();
  // Endlosschleife oder ESP-Neustart (hier Neustart nach 5 Sek)
  delay(5000);
  ESP.restart();
}

void setup() {
  Serial.begin(115200);

  // Hardware initialisieren
  pinMode(BUZZER_PIN, OUTPUT);
  SPI.begin();           
  rfrc522.PCD_Init();    

  // Display initialisieren
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306-Display konnte nicht gestartet werden"));
    for(;;); 
  }
  
  // 1) DISPLAY UM 180 GRAD DREHEN
  display.setRotation(2); 
  
  display.clearDisplay();

  // 2) WLAN-VERBINDUNG MIT BACKUP
  connectToWiFi();
  
  playTone(1500, 100); delay(50); playTone(2500, 150);
  delay(1000);
  showReadyMessage();
}

void loop() {
  if (!rfrc522.PICC_IsNewCardPresent() || !rfrc522.PICC_ReadCardSerial()) {
    return;
  }

  if (millis() - lastScanTime < scanDelay) {
    rfrc522.PICC_HaltA();
    return;
  }
  lastScanTime = millis();

  String uidString = "";
  for (byte i = 0; i < rfrc522.uid.size; i++) {
    if (rfrc522.uid.uidByte[i] < 0x10) uidString += "0";
    uidString += String(rfrc522.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();

  updateDisplay("SCAN ERKANNT", "Verarbeite", "Bitte warten...");

  sendeStempelRequest(uidString);

  rfrc522.PICC_HaltA();
}

void sendeStempelRequest(String uid) {
  // Wenn die Verbindung im Betrieb abreißt, versuchen wir den Reconnect
  if (WiFi.status() != WL_CONNECTED) {
    updateDisplay("RECONNECTING", "WLAN verloren", "Suche Netz...");
    signalWarning();
    connectToWiFi();
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc;
  doc["chip_id"] = uid;
  String requestBody;
  serializeJson(doc, requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {
    String response = http.getString();
    StaticJsonDocument<300> resDoc;
    DeserializationError error = deserializeJson(resDoc, response);

    if (!error) {
      const char* statusField = resDoc["status"];
      const char* empName = resDoc["employee_name"];
      
      if (httpResponseCode == 200) {
        if (statusField && String(statusField) == "warning") {
          updateDisplay("WARNUNG", "Zu schnell!", "Bitte warten...");
          signalWarning();
        } else {
          const char* newStatus = resDoc["new_status"]; 
          updateDisplay(newStatus, empName, "Schönen Tag!");
          signalSuccess();
        }
      } 
      else if (httpResponseCode == 404) {
        updateDisplay("GEBLOCKT", "Unbekannt", "Chip registrieren");
        signalError();
      } 
      else if (httpResponseCode == 403) {
        updateDisplay("GEBLOCKT", "Urlaub/Krank", "Kein Check-In");
        signalError();
      }
    } else {
      updateDisplay("FEHLER", "JSON Error", "Parser Fehler");
      signalError();
    }
  } else {
    updateDisplay("SERVER ERROR", "Keine Antwort", "Vom MiniPC");
    signalError();
  }

  http.end();
  
  delay(3000);
  showReadyMessage();
}