/*
 * Cortex Brain — Arduino Nano Hardware Firmware (Pins 2 to 19: D2-D13 and A0-A5)
 * Supports full 16-LED binary clock shields (Hours, Minutes, Seconds) and direct control.
 */

#define START_BYTE 0x02
#define END_BYTE   0x03

#define CMD_SET_PIN    0x01
#define CMD_READ_PIN   0x02
#define CMD_SET_ALL    0x04
#define CMD_PING       0x05

#define STATUS_ACK  0x00
#define STATUS_NACK 0x01

String inputString = "";

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }

    // Initialize all controllable pins (D2 through D13, and A0 through A5)
    for (int p = 2; p <= 19; p++) {
        pinMode(p, OUTPUT);
        digitalWrite(p, LOW);
    }
    inputString.reserve(64);
    Serial.println("CORTEX_ARDUINO_READY");
}

void loop() {
    // 1. Process Binary Packets
    if (Serial.available() >= 6) {
        if (Serial.peek() == START_BYTE) {
            Serial.read();
            byte cmd = Serial.read();
            byte pin = Serial.read();
            byte val = Serial.read();
            byte cs  = Serial.read();
            byte end = Serial.read();

            if (end == END_BYTE && cs == ((cmd ^ pin ^ val) & 0xFF)) {
                handleBinaryCommand(cmd, pin, val);
                return;
            }
        }
    }

    // 2. Process ASCII Stream Line by Line
    while (Serial.available()) {
        char inChar = (char)Serial.read();
        if (inChar == '\n' || inChar == '\r') {
            if (inputString.length() > 0) {
                handleAsciiCommand(inputString);
                inputString = "";
            }
        } else {
            inputString += inChar;
        }
    }
}

void handleBinaryCommand(byte cmd, byte pin, byte val) {
    if (cmd == CMD_SET_PIN) {
        if (pin >= 2 && pin <= 19) {
            digitalWrite(pin, val ? HIGH : LOW);
            sendBinaryResponse(cmd, STATUS_ACK, val);
        }
    } else if (cmd == CMD_READ_PIN) {
        if (pin >= 2 && pin <= 19) {
            sendBinaryResponse(cmd, STATUS_ACK, digitalRead(pin));
        }
    } else if (cmd == CMD_SET_ALL) {
        for (int p = 2; p <= 19; p++) {
            digitalWrite(p, val ? HIGH : LOW);
        }
        sendBinaryResponse(cmd, STATUS_ACK, val);
    } else if (cmd == CMD_PING) {
        sendBinaryResponse(cmd, STATUS_ACK, 0x42);
    }
}

void handleAsciiCommand(String cmd) {
    cmd.trim();
    cmd.toUpperCase();

    if (cmd.startsWith("SET")) {
        // e.g. "SET 3 1" or "SET A0 1" (A0=14, A1=15, A2=16, A3=17, A4=18, A5=19)
        int firstSpace = cmd.indexOf(' ');
        int secondSpace = cmd.indexOf(' ', firstSpace + 1);
        if (firstSpace > 0 && secondSpace > 0) {
            String pinStr = cmd.substring(firstSpace + 1, secondSpace);
            int pin = -1;
            if (pinStr.startsWith("A")) {
                int aNum = pinStr.substring(1).toInt();
                if (aNum >= 0 && aNum <= 5) pin = 14 + aNum;
            } else {
                pin = pinStr.toInt();
            }

            int val = cmd.substring(secondSpace + 1).toInt();
            if (pin >= 2 && pin <= 19) {
                digitalWrite(pin, val ? HIGH : LOW);
                Serial.print("ACK SET PIN ");
                Serial.print(pin);
                Serial.print(" = ");
                Serial.println(val);
                return;
            }
        }
    } else if (cmd.startsWith("ALL")) {
        int space = cmd.indexOf(' ');
        int val = 0;
        if (space > 0) {
            val = cmd.substring(space + 1).toInt();
        }
        for (int p = 2; p <= 19; p++) {
            digitalWrite(p, val ? HIGH : LOW);
        }
        Serial.print("ACK ALL PINS = ");
        Serial.println(val);
        return;
    } else if (cmd == "SCAN") {
        Serial.println("STARTING PIN SCAN (D2 to A5)...");
        for (int p = 2; p <= 19; p++) {
            digitalWrite(p, HIGH);
            delay(350);
            digitalWrite(p, LOW);
            delay(50);
        }
        Serial.println("PIN SCAN COMPLETE");
        return;
    } else if (cmd == "PING") {
        Serial.println("PONG CORTEX_NANO");
        return;
    }
}

void sendBinaryResponse(byte cmd, byte status, byte data) {
    byte cs = (cmd ^ status ^ data) & 0xFF;
    byte packet[6] = {START_BYTE, cmd, status, data, cs, END_BYTE};
    Serial.write(packet, 6);
}
