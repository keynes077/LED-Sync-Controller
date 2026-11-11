/*
  LED CNTRL serial protocol example — adapt to your exact LED chipset and wiring.
  Receives one line with 3 * NUM_LEDS decimal values, RGB per LED.
  Default setup is WS2812B-compatible, 42 LEDs, data pin GPIO 2, 115200 baud.

  IMPORTANT:
  - Use an appropriately rated external 5V supply for the LED strip.
  - Connect external supply GND and ESP32 GND together.
  - Never power a long strip from the ESP32 board's 5V/VIN pin.
*/
#include <FastLED.h>

#define DATA_PIN 2
#define NUM_LEDS 42
#define LED_TYPE WS2812B
#define CHIPSET_ORDER GRB
#define MAX_LINE 1800

CRGB leds[NUM_LEDS];
char lineBuffer[MAX_LINE];
size_t linePos = 0;

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<LED_TYPE, DATA_PIN, CHIPSET_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(255);
  FastLED.clear(true);
}

void processLine(char *line) {
  int values[NUM_LEDS * 3];
  int count = 0;
  char *token = strtok(line, ",");
  while (token != nullptr && count < NUM_LEDS * 3) {
    values[count++] = constrain(atoi(token), 0, 255);
    token = strtok(nullptr, ",");
  }
  if (count != NUM_LEDS * 3) return;
  for (int i = 0; i < NUM_LEDS; ++i) {
    leds[i] = CRGB(values[i * 3], values[i * 3 + 1], values[i * 3 + 2]);
  }
  FastLED.show();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      lineBuffer[linePos] = '\0';
      processLine(lineBuffer);
      linePos = 0;
    } else if (c != '\r') {
      if (linePos < MAX_LINE - 1) lineBuffer[linePos++] = c;
      else linePos = 0;
    }
  }
}
