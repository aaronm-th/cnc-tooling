#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// RFID Pin-Definitionen (deine neuen, freien Pins)
#define RST_PIN         12   
#define SS_PIN          13   
MFRC522 mfrc522(SS_PIN, RST_PIN); 

// Display-Definitionen (Größe 128x64 Pixel)
#define SCREEN_WIDTH 128 
#define SCREEN_HEIGHT 64 
#define OLED_RESET    -1 // Reset-Pin teilen wir uns nicht
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(115200); 
  while (!Serial); 
  
  // SPI-Bus und RFID initialisieren
  SPI.begin(); 
  mfrc522.PCD_Init(); 
  
  // I2C-Display initialisieren (Standard-Adresse ist oft 0x3C)
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { 
    Serial.println(F("SSD1306 Display konnte nicht gestartet werden"));
    for(;;); // Stoppe das Programm, falls das Display fehlt
  }
  
  // Startbildschirm auf dem Display anzeigen
  display.clearDisplay();
  display.setTextSize(1);             
  display.setTextColor(SSD1306_WHITE);        
  display.setCursor(0, 20);             
  display.println("Bereit zum Scannen...");
  display.display();
  
  Serial.println(F("Bereit! Scanne eine Karte..."));
} 

void loop() { 
  // Suche nach neuen RFID-Karten
  if (!mfrc522.PICC_IsNewCardPresent()) { 
    return; 
  } 
  
  // Versuche die UID zu lesen
  if (!mfrc522.PICC_ReadCardSerial()) { 
    return; 
  } 
  
  // UID in einen String umwandeln
  String gescannteUID = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    gescannteUID += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    gescannteUID += String(mfrc522.uid.uidByte[i], HEX);
  }
  gescannteUID.toUpperCase();

  // Ausgabe auf dem Seriellen Monitor
  Serial.print("Gescannte UID: ");
  Serial.println(gescannteUID);
  
  // Ausgabe auf dem Display
  display.clearDisplay(); // Altes Bild löschen
  
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("--- RFID SCANNER ---");
  
  display.setTextSize(2); // Größere Schrift für die UID
  display.setCursor(0, 25);
  display.println(gescannteUID);
  
  display.display(); // Änderungen auf dem Display sichtbar machen
  
  // 3 Sekunden warten, bevor der nächste Scan erlaubt ist
  delay(3000);
}