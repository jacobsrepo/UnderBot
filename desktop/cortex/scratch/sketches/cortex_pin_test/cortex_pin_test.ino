void setup() {
  for (int pin = 2; pin <= 13; pin++) {
    pinMode(pin, OUTPUT);
  }
  for (int pin = 0; pin <= 5; pin++) {
    pinMode(pin + 14, OUTPUT);
  }
}

void loop() {
  for (int pin = 2; pin <= 13; pin++) {
    digitalWrite(pin, HIGH);
    delay(500);
    digitalWrite(pin, LOW);
  }
  for (int pin = 0; pin <= 5; pin++) {
    digitalWrite(pin + 14, HIGH);
    delay(500);
    digitalWrite(pin + 14, LOW);
  }
}