#include <SPI.h>
#include <MFRC522.h>

// Pin-Definitionen für den RFID-Reader
#define RST_PIN         9  
#define SS_PIN         10  

MFRC522 mfrc522(SS_PIN, RST_PIN); 

void setup() {
  // Seriellen Monitor mit 115200 Baud starten
  Serial.begin(115200); 
  while (!Serial); // Warten, bis der serielle Monitor bereit ist
  
  // SPI-Bus und RFID-Modul initialisieren
  SPI.begin(); 
  mfrc522.PCD_Init(); 
  
  // Details des Typs und der Firmware-Version im Monitor ausgeben
  mfrc522.PCD_DumpVersionToSerial(); 
  Serial.println(F("Scanne eine Karte/Key-Fob, um UID, Typ und Datenbloecke zu sehen..."));
} 

void loop() { 
  // Suche nach neuen RFID-Karten. Wenn keine da ist, bricht der Loop hier ab.
  if (!mfrc522.PICC_IsNewCardPresent()) { 
    return; 
  } 
  
  // Versuche die Seriennummer (UID) der Karte zu lesen. Wenn fehlgeschlagen, brich ab.
  if (!mfrc522.PICC_ReadCardSerial()) { 
    return; 
  } 
  
  // Alle Daten der erkannten Karte im Seriellen Monitor ausgeben
  mfrc522.PICC_DumpToSerial(&(mfrc522.uid));
}