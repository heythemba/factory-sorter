// ESP8266 Arduino Sketch (NodeMCU 1.0)
// Libraries: ESP8266WiFi, ESP8266WebServer, ServoESP8266 (or Servo library compatible)

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

const char* ssid = "TUNISIETELECOM-2.4G-GVz3";
const char* pass = "t96cUyXC";

ESP8266WebServer server(80);

Servo servo1;
const int SERVO_PIN = D4;      // change as wired
const int RED_LED = D5;        // change as wired
const int GREEN_LED = D6;      // change as wired

void handle_servo() {
  if (server.hasArg("angle")) {
    int angle = server.arg("angle").toInt();
    angle = constrain(angle, 0, 180);
    servo1.write(angle);
    Serial.printf("Servo -> %d deg\n", angle);
    server.send(200, "text/plain", "OK");
  } else {
    server.send(400, "text/plain", "angle missing");
  }
}

void handle_led() {
  String color = server.arg("color");
  String state = server.arg("state");
  int pin = (color == "red") ? RED_LED : GREEN_LED;
  int val = (state == "on") ? HIGH : LOW;
  digitalWrite(pin, val);
  Serial.printf("LED %s -> %s\n", color.c_str(), state.c_str());
  server.send(200, "text/plain", "OK");
}

void handle_log() {
  String msg = server.arg("msg");
  Serial.println(msg);
  server.send(200, "text/plain", "OK");
}

void setup() {
  Serial.begin(115200);
  Serial.println("System init_______");
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, LOW);

  servo1.attach(SERVO_PIN);
  servo1.write(90); // INITIAL POSITION = 90° per your requirement

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("");
  Serial.print("IP: "); Serial.println(WiFi.localIP());

  server.on("/servo", HTTP_GET, handle_servo);
  server.on("/led", HTTP_GET, handle_led);
  server.on("/log", HTTP_GET, handle_log);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() { server.handleClient(); }
