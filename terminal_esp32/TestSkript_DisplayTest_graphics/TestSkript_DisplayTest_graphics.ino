// Definiere den Pin, an dem der Buzzer angeschlossen ist
#define BUZZER_PIN 4 

void setup() {
  // Setze den Buzzer-Pin als Ausgang
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Kleiner Start-Sound: 3 kurze Pieptöne beim Einschalten/Reset
  for(int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH); // Ton an
    delay(100);                     // 100 Millisekunden warten
    digitalWrite(BUZZER_PIN, LOW);  // Ton aus
    delay(100);                     // 100 Millisekunden Pause
  }
}

void loop() {
  // Ein einfacher, regelmäßiger Piepton im Loop
  digitalWrite(BUZZER_PIN, HIGH); // Ton an
  delay(200);                     // 200 Millisekunden lang piepen
  digitalWrite(BUZZER_PIN, LOW);  // Ton aus
  
  delay(2000);                    // 2 Sekunden warten, bis es von vorne losgeht
}