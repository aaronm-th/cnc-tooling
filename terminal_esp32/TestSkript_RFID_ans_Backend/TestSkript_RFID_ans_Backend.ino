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
const char* ssid = "WLAN_NAME";
const char* password = "password123";
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
  updateDisplay("STEMPELUHR READY", "Bitte Karte", "anlegen...");
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

// --- ARDUINO SETUP ---
void setup() {
  Serial.begin(115200);

  // Hardware initialisieren
  pinMode(BUZZER_PIN, OUTPUT);
  SPI.begin();          
  rfrc522.PCD_Init();    

  // Display initialisieren
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306-Display konnte nicht gestartet werden"));
    for(;;); // Stoppen, falls Display fehlt
  }
  display.setRotation(2); 
  display.clearDisplay();
  updateDisplay("BOOTING...", "Verbinde", "WLAN...");

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
 
  Serial.println("\nWLAN verbunden!");
  updateDisplay("WLAN OK!", "Bereit für", "Scans...");
 
  playTone(1500, 100); delay(50); playTone(2500, 150);
  delay(1000);
  showReadyMessage();
}

// --- API REQEST FUNCTION ---
void sendeStempelRequest(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    updateDisplay("NETZWERKFEHLER", "Kein WLAN", "Verbindung weg");
    signalError();
    delay(3000);
    showReadyMessage();
    return;
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
      
      // 1. ERFOLGREICHES EIN- ODER AUSSTEMPELN (HTTP 200 OK)
      if (httpResponseCode == 200) {
        if (statusField && String(statusField) == "warning") {
          // Timer-Sperre aktiv
          updateDisplay("WARNUNG", "Zu schnell!", "Bitte warten...");
          signalWarning();
        } else {
          // Erfolgreich gestempelt -> Holt den Usernamen aus dem JSON
          const char* newStatus = resDoc["new_status"]; // "Anwesend" oder "Abwesend"
          
          // Liest primär 'username' aus. Falls Backend 'employee_name' sendet, greift der Fallback
          const char* usernameField = resDoc["username"];
          if (!usernameField) {
            usernameField = resDoc["employee_name"];
          }
         
          String displayUser = usernameField ? String(usernameField) : "Mitarbeiter";
          
          updateDisplay(newStatus, displayUser, "Status geändert!");
          signalSuccess();
        }
      }
      // 2. UNBEKANNTER CHIP (HTTP 404 NOT FOUND)
      else if (httpResponseCode == 404) {
        // Holt die vom Backend zurückgegebene ID (falls vorhanden) oder nutzt die lokale UID
        const char* backendChipId = resDoc["chip_id"];
        String displayUid = backendChipId ? String(backendChipId) : uid;
        
        // Zeigt die rohe Chip-ID groß auf dem Display an
        updateDisplay("UNBEKANNTER CHIP", displayUid, "Bitte registrieren");
        signalError();
      }
      // 3. ABWESENHEIT DURCH SPERREN WIE KRANK/URLAUB (HTTP 403 FORBIDDEN)
      else if (httpResponseCode == 403) {
        updateDisplay("GEBLOCKT", "Urlaub/Krank", "Kein Check-In");
        signalError();
      }
    } else {
      updateDisplay("FEHLER", "JSON Error", "Parser Fehler");
      signalError();
    }
  } else {
    updateDisplay("SERVER ERROR", "Keine Antwort", "Vom Backend");
    signalError();
  }

  http.end();
 
  // 4 Sekunden Wartezeit (Lesezeit für ID / Namen), danach wieder Standard-Bereitschaft
  delay(4000);
  showReadyMessage();
}

// --- MAIN LOOP ---
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

  // Sofortiges visuelles Feedback für den Mitarbeiter
  updateDisplay("SCAN ERKANNT", "Verarbeite", "Bitte warten...");

  sendeStempelRequest(uidString);

  rfrc522.PICC_HaltA();
}