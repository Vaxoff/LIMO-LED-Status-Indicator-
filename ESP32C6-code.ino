// CRITICAL: Must be the very first line!
#define MQTT_MAX_PACKET_SIZE 16384
#define MOSFET_GATE_PIN 7

#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

// --- WIFI CONFIGURATION ---
const char* ssid = "rastic";
const char* password = "botbotbot";

// --- MQTT CONFIGURATION ---
const char* mqtt_server = "rasticvm.internal";
const int mqtt_port = 1883;
const char* MOCAP_HEALTH_TOPIC = "mocap/health/available";
// Per-robot tracking topic (rb/<LIMO_ID>) is built at runtime once we know LIMO_ID.

// --- LIMO CONFIGURATION ---
String LIMO_ID = "UNKNOWN";
String connectedAsID = "";
String macSuffix = "";

// --- LED CONFIGURATION ---
#define PIN        8
#define NUMPIXELS  1
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

WiFiClient espClient;
PubSubClient client(espClient);

// --- TIMING & STATE ---
unsigned long lastMyTrackTime = 0;
const long trackingTimeout = 10000; // 10 seconds

// Mocap availability via mocap/health/available (online/offline, retained)
bool mocapOnline = false;

// NEW: periodically nag the host for our ID instead of waiting silently
unsigned long lastIdRequestTime = 0;
const long idRequestInterval = 1000; // ask once a second while unknown

bool hasEverBeenTracked = false;

enum LedState { STATE_IDLE, STATE_TRACKED, STATE_NOT_TRACKED, STATE_ERROR, STATE_WAITING_FOR_ID };
LedState currentState = STATE_ERROR;

String serialBuffer = "";

void setColor(int r, int g, int b) {
  pixels.setPixelColor(0, pixels.Color(r, g, b));
  pixels.show();
}

void setLedState(LedState newState) {
  if (newState == currentState) return;
  currentState = newState;

  switch (newState) {
    case STATE_TRACKED:
      Serial.println("[LED] State -> TRACKED (Green)");
      setColor(0, 150, 0);
      break;
    case STATE_NOT_TRACKED:
      Serial.println("[LED] State -> NOT TRACKED (Magenta)");
      setColor(255, 0, 255);
      break;
    case STATE_IDLE:
      Serial.println("[LED] State -> IDLE (Blue)");
      setColor(0, 0, 150);
      break;
    case STATE_ERROR:
      Serial.println("[LED] State -> ERROR (Red)");
      setColor(150, 0, 0);
      break;
    case STATE_WAITING_FOR_ID:
      // Distinct from a real error, so you're not chasing a phantom fault
      // every time you unplug/replug the USB cable.
      Serial.println("[LED] State -> WAITING FOR ID (White)");
      setColor(150, 150, 150);
      break;
  }

  // Publish our state to our own permanent topic so the visualizer has a solid node
  if (client.connected() && LIMO_ID != "UNKNOWN") {
    String statusTopic = "esp32_status/" + LIMO_ID;
    const char* stateStr = "UNKNOWN";
    if (newState == STATE_TRACKED) stateStr = "TRACKED";
    else if (newState == STATE_NOT_TRACKED) stateStr = "NOT_TRACKED";
    else if (newState == STATE_IDLE) stateStr = "IDLE";
    else if (newState == STATE_ERROR) stateStr = "ERROR";

    client.publish(statusTopic.c_str(), stateStr, true);
  }
}

// --------------------------------------------------------------------------
// Drives MOSFET_GATE_PIN with the ESP32's hardware LEDC (PWM) peripheral
// instead of software millis() toggling. Once configured, the waveform is
// generated entirely by dedicated PWM hardware -- it can't drift, stutter,
// or get delayed by other work happening in loop() (WiFi/MQTT handling,
// delay() calls, etc.), which is what made a millis()-based toggle brittle.
//
//   freqHz       -> PWM frequency in Hz (ignored if dutyPercent is 0 or 100)
//   dutyPercent  -> 0-100
//                     0   -> pin held solid LOW  (PWM hardware detached)
//                     100 -> pin held solid HIGH (PWM hardware detached)
//                     1-99 -> real hardware PWM at freqHz / dutyPercent
//
// Written for Arduino-ESP32 core 3.x's pin-based LEDC API
// (ledcAttach/ledcWrite/ledcChangeFrequency, no channel argument).
// --------------------------------------------------------------------------
const int MOSFET_PWM_RESOLUTION = 8; // 8-bit duty resolution (0-255)
bool mosfetPwmAttached = false;
double currentFreqHz = -1;
int currentDutyPercent = -1; // -1 = not yet configured

void blinkMosfet(double freqHz, uint8_t dutyPercent) {
  if (dutyPercent > 100) dutyPercent = 100;

  // Fully off or fully on -> drive the pin directly, no PWM hardware needed
  if (dutyPercent == 0 || dutyPercent == 100) {
    if (mosfetPwmAttached) {
      ledcDetach(MOSFET_GATE_PIN);
      mosfetPwmAttached = false;
    }
    pinMode(MOSFET_GATE_PIN, OUTPUT);
    digitalWrite(MOSFET_GATE_PIN, dutyPercent == 100 ? HIGH : LOW);
    currentFreqHz = 0;
    currentDutyPercent = dutyPercent;
    return;
  }

  if (freqHz == currentFreqHz && dutyPercent == currentDutyPercent) return; // already configured

  if (!mosfetPwmAttached) {
    ledcAttach(MOSFET_GATE_PIN, freqHz, MOSFET_PWM_RESOLUTION);
    mosfetPwmAttached = true;
  } else if (freqHz != currentFreqHz) {
    ledcChangeFrequency(MOSFET_GATE_PIN, freqHz, MOSFET_PWM_RESOLUTION);
  }

  uint32_t maxDuty = (1u << MOSFET_PWM_RESOLUTION) - 1; // 255 at 8-bit
  uint32_t dutyValue = (maxDuty * dutyPercent) / 100;
  ledcWrite(MOSFET_GATE_PIN, dutyValue);

  currentFreqHz = freqHz;
  currentDutyPercent = dutyPercent;
}

void checkSerialForID() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      serialBuffer.trim();
      if (serialBuffer.startsWith("LIMO_ID:")) {
        String newId = serialBuffer.substring(8);
        newId.trim();
        if (newId.length() > 0 && newId != LIMO_ID) {
          LIMO_ID = newId;
          hasEverBeenTracked = false;
          lastMyTrackTime = 0;
          Serial.println("[INFO] Received LIMO_ID from Jetson: " + LIMO_ID);

          // NEW: tell the host we actually got it, so it can stop retrying
          Serial.println("ACK:" + LIMO_ID);

          if (client.connected() && connectedAsID != ("ESP32_" + LIMO_ID + "_" + macSuffix)) {
            Serial.println("[MQTT] ID changed, forcing reconnect...");
            client.disconnect();
          }
        } else if (newId.length() > 0) {
          // We already have this ID (e.g. host resent after a REQUEST_ID) —
          // still ACK it so the host's retry loop can stop.
          Serial.println("ACK:" + LIMO_ID);
        }
      }
      serialBuffer = "";
    } else {
      serialBuffer += c;
    }
  }
}

void setup_wifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("[WIFI] Connecting to "); Serial.println(ssid);
  WiFi.begin(ssid, password);

  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    setLedState(STATE_ERROR);
  }

  Serial.println("\n[WIFI] Connected! IP: " + WiFi.localIP().toString());

  macSuffix = WiFi.macAddress();
  macSuffix.replace(":", "");
  macSuffix = macSuffix.substring(6);
}

void reconnect() {
  if (LIMO_ID == "UNKNOWN") {
    setLedState(STATE_WAITING_FOR_ID);
    return;
  }

  if (!client.connected()) {
    Serial.print("[MQTT] Attempting connection... ");

    String clientId = "ESP32_" + LIMO_ID + "_" + macSuffix;
    String statusTopic = "esp32_status/" + LIMO_ID;
    // FIX: this was "test/" + LIMO_ID (leftover debug value) -- that's why
    // green never lit up. Mocap publishes tracking data to rb/<LIMO_ID>.
    String trackTopic = "rb/" + LIMO_ID;

    if (client.connect(clientId.c_str(), statusTopic.c_str(), 1, true, "OFFLINE")) {
      Serial.println("Connected!");
      connectedAsID = clientId;

      // Only subscribe to OUR tracking topic and the shared health heartbeat --
      // no more "#". The broker does the filtering now instead of us doing it
      // client-side, so every other robot's traffic (and printers, doors, etc.)
      // never even reaches this board.
      Serial.print("[MQTT] Subscribing to: ");
      Serial.println(trackTopic);
      client.subscribe(trackTopic.c_str());

      Serial.print("[MQTT] Subscribing to: ");
      Serial.println(MOCAP_HEALTH_TOPIC);
      client.subscribe(MOCAP_HEALTH_TOPIC);

      setLedState(STATE_IDLE);
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      setLedState(STATE_ERROR);
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String topicStr = String(topic);

  if (topicStr == MOCAP_HEALTH_TOPIC) {
    // "available" is retained/LWT-backed on mocap's side, so the broker
    // itself guarantees this flips to offline on a real crash/disconnect --
    // we can trust it directly without our own staleness timeout.
    char buf[length + 1];
    memcpy(buf, payload, length);
    buf[length] = '\0';

    mocapOnline = (String(buf) == "online");
    Serial.print("[MOCAP] available -> ");
    Serial.println(mocapOnline ? "online" : "offline");
    return;
  }

  // Anything else we're subscribed to can only be our own rb/<LIMO_ID> topic --
  // the broker already filtered it for us, no client-side ID matching needed.
  lastMyTrackTime = millis();
  hasEverBeenTracked = true;
  Serial.print("[TRACK] Update from: ");
  Serial.println(topic);
}

void setup() {
  pinMode(MOSFET_GATE_PIN, OUTPUT);
  digitalWrite(MOSFET_GATE_PIN, HIGH); // matches blinkMosfet()'s default "solid on" state (currentBlinkIntervalMs = 0)

  Serial.begin(115200);
  pixels.begin();
  setLedState(STATE_WAITING_FOR_ID);
  Serial.println("[SYSTEM] Booting ESP32...");

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(60);
  client.setBufferSize(16384);
}

void loop() {
  checkSerialForID();

  // NEW: while we don't have an ID, keep asking for one instead of
  // silently hoping the one shot the host sent actually landed.
  if (LIMO_ID == "UNKNOWN") {
    unsigned long now = millis();
    if (now - lastIdRequestTime > idRequestInterval) {
      Serial.println("REQUEST_ID");
      lastIdRequestTime = now;
    }
  }

  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
  }

  if (!client.connected()) {
    reconnect();
  }

  client.loop();

  if (client.connected()) {
    unsigned long currentTime = millis();

    if (hasEverBeenTracked && (currentTime - lastMyTrackTime < trackingTimeout)) {
      setLedState(STATE_TRACKED); // Green -- this robot is tracked
    }
    else if (mocapOnline) {
      setLedState(STATE_NOT_TRACKED); // Magenta -- able to track, just not tracking me
    }
    else {
      setLedState(STATE_IDLE); // Blue -- not able to track right now
    }
  }

  blinkMosfet(1000, 75);
}