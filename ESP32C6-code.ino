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
const char* mqtt_topic = "rb/#";         // Listen to everything

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
unsigned long lastAnyTrackTime = 0;
const long trackingTimeout = 10000; // 10 seconds

// NEW: periodically nag the host for our ID instead of waiting silently
unsigned long lastIdRequestTime = 0;
const long idRequestInterval = 1000; // ask once a second while unknown

bool hasEverBeenTracked = false;
bool hasEverReceivedAny = false;

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
    String statusTopic = "esp32_status/limo" + LIMO_ID;
    const char* stateStr = "UNKNOWN";
    if (newState == STATE_TRACKED) stateStr = "TRACKED";
    else if (newState == STATE_NOT_TRACKED) stateStr = "NOT_TRACKED";
    else if (newState == STATE_IDLE) stateStr = "IDLE";
    else if (newState == STATE_ERROR) stateStr = "ERROR";

    client.publish(statusTopic.c_str(), stateStr, true);
  }
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
    String statusTopic = "esp32_status/limo" + LIMO_ID;

    if (client.connect(clientId.c_str(), statusTopic.c_str(), 1, true, "OFFLINE")) {
      Serial.println("Connected!");
      connectedAsID = clientId;
      Serial.print("[MQTT] Subscribing to: ");
      Serial.println(mqtt_topic);
      client.subscribe(mqtt_topic);
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
  // CRITICAL FIX: Ignore our own published status messages!
  // Since we subscribe to "#", we hear our own messages. We must skip them
  // so we don't falsely trigger our own tracking state.
  if (strncmp(topic, "esp32_status/", 13) == 0) {
    return;
  }

  // 1. ANY message means the system is alive
  lastAnyTrackTime = millis();
  hasEverReceivedAny = true;

  // 2. Ultra-fast C-string check for our ID
  if (LIMO_ID != "UNKNOWN") {
    char targetId[20];
    snprintf(targetId, sizeof(targetId), "limo%s", LIMO_ID.c_str());
    size_t targetLen = strlen(targetId);

    char* match = strstr(topic, targetId);
    if (match != NULL) {
      char nextChar = *(match + targetLen);
      if (nextChar == '\0' || nextChar == '/') {
        lastMyTrackTime = millis();
        hasEverBeenTracked = true;

        // DEBUG: This will print exactly what topic is making us Green
        Serial.print("[TRACK] Update from: ");
        Serial.println(topic);
      }
    }
  }
}

void setup() {
  pinMode(MOSFET_GATE_PIN, OUTPUT);
  digitalWrite(MOSFET_GATE_PIN, HIGH);

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
      setLedState(STATE_TRACKED); // Green
    }
    else if (hasEverReceivedAny && (currentTime - lastAnyTrackTime < trackingTimeout)) {
      setLedState(STATE_NOT_TRACKED); // Magenta
    }
    else {
      setLedState(STATE_IDLE); // Blue
    }
  }
}
