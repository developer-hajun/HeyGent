#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <U8g2_for_Adafruit_GFX.h>
#include <math.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define SDA_PIN 4
#define SCL_PIN 5
#define TOUCH_PIN 6
#define BUZZER_PIN 3   // 수동 압전 부저: GPIO3 사용
#define OLED_ADDRESS_PRIMARY 0x3C
#define OLED_ADDRESS_FALLBACK 0x3D
#define OLED_CMD_SET_CONTRAST 0x81
#define SSD1306_WHITE SH110X_WHITE
#define SSD1306_BLACK SH110X_BLACK

// 10: 09 통합 흐름 + 배터리/TP4056 전원 구성. 물리 스위치 입력 대기 없이 바로 부팅한다.
// 서버 display payload가 들어오면 5초 동안 표시하고, 이후 표정 idle 상태로 돌아간다.
// 로봇이 옆으로 넘어지면 자는 표정 또는 우는 표정을 우선 표시한다.
#define DEFAULT_WIFI_SSID ""
#define DEFAULT_WIFI_PASSWORD ""
#define BACKEND_BASE_URL "http://k14e105.p.ssafy.io:8080"
#define MQTT_HOST "k14e105.p.ssafy.io"
#define MQTT_PORT 1883
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""

#define FIRMWARE_VERSION "0.7.0-battery-power-gyro-fall"
#define RESET_PAIRING_ON_BOOT false

const unsigned long WIFI_RETRY_INTERVAL_MS = 10000;
const unsigned long WIFI_CONNECT_TIMEOUT_MS = 20000;
const unsigned long MQTT_RETRY_INTERVAL_MS = 5000;
const unsigned long PAIRING_RETRY_INTERVAL_MS = 5000;
const unsigned long STATUS_CHECK_RETRY_INTERVAL_MS = 15000;
const unsigned long PAIRING_REFRESH_SKEW_MS = 3000;
const unsigned long SERVER_MESSAGE_DISPLAY_MS = 5000;
const unsigned long DEVICE_TASK_MANUAL_FOCUS_MS = 15000;
const int MAX_ACTIVE_TASK_SESSIONS = 3;
const unsigned long TOUCH_LONG_PRESS_MS = 5000;
const unsigned long IMU_READ_INTERVAL_MS = 100;
const unsigned long FALL_CONFIRM_MS = 700;
const unsigned long UPRIGHT_CONFIRM_MS = 1200;
const float FALLEN_ANGLE_DEGREES = 65.0f;
const float UPRIGHT_ANGLE_DEGREES = 35.0f;

const uint8_t MPU6050_ADDR_PRIMARY = 0x68;
const uint8_t MPU6050_ADDR_FALLBACK = 0x69;
const uint8_t MPU6050_PWR_MGMT_1 = 0x6B;
const uint8_t MPU6050_ACCEL_CONFIG = 0x1C;
const uint8_t MPU6050_ACCEL_XOUT_H = 0x3B;
const float MPU6050_ACCEL_SCALE = 16384.0f;
const byte DNS_PORT = 53;

Adafruit_SH1106G display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
U8G2_FOR_ADAFRUIT_GFX u8g2Fonts;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
Preferences preferences;
WebServer setupServer(80);
DNSServer dnsServer;
IPAddress setupApIp(192, 168, 4, 1);
IPAddress setupApGateway(192, 168, 4, 1);
IPAddress setupApSubnet(255, 255, 255, 0);
uint8_t oledAddress = OLED_ADDRESS_PRIMARY;
uint8_t mpuAddress = MPU6050_ADDR_PRIMARY;
int activeSdaPin = SDA_PIN;
int activeSclPin = SCL_PIN;

String deviceId;
String displayTopic;
String currentPairCode;
String wifiSsid;
String wifiPassword;
String setupApSsid;

bool paired = false;
bool wifiStarted = false;
bool wifiWasConnected = false;
bool pairingStatusSynced = false;
bool wifiSetupMode = false;
bool wifiSetupServerStarted = false;
bool wifiSetupRoutesConfigured = false;
bool wifiReconnectPending = false;

unsigned long nextWifiAttemptAt = 0;
unsigned long wifiAttemptStartedAt = 0;
unsigned long wifiReconnectAt = 0;
unsigned long nextMqttAttemptAt = 0;
unsigned long nextPairingAttemptAt = 0;
unsigned long nextStatusCheckAt = 0;
unsigned long pairCodeExpiresAt = 0;
unsigned long nextPairCodeRedrawAt = 0;
unsigned long messageUntil = 0;

#define INTRO_BITMAP_WIDTH 128
#define INTRO_BYTES_PER_ROW (INTRO_BITMAP_WIDTH / 8)

#define HELLO_BITMAP_HEIGHT (sizeof(bmp_hello_kr) / INTRO_BYTES_PER_ROW)
#define NAME_BITMAP_HEIGHT  (sizeof(bmp_name_kr) / INTRO_BYTES_PER_ROW)

const unsigned char bmp_hello_kr[] PROGMEM = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x00, 0x00, 0xC0, 0x18, 0x06, 0x00, 0x00, 0xCE, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x07, 0xC0, 0xE0, 0x60, 0x00, 0xC0, 0x1C, 0x06, 0x00, 0x00, 0xCE, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x0F, 0xF0, 0xE0, 0x70, 0x00, 0xC0, 0x1C, 0x06, 0x00, 0xC0, 0xCE, 0x01, 0xFC, 0x00, 0x00,
  0x00, 0x1C, 0x38, 0xE0, 0x70, 0x3F, 0xC3, 0xFF, 0xE6, 0x00, 0xE0, 0xCE, 0x07, 0xFF, 0x00, 0x00,
  0x00, 0x18, 0x38, 0xE0, 0x70, 0x3F, 0xC3, 0xFF, 0xE6, 0x00, 0xE0, 0xCE, 0x0F, 0x03, 0x80, 0x00,
  0x00, 0x38, 0x18, 0xE0, 0x70, 0x00, 0xC0, 0x00, 0x06, 0x00, 0xE0, 0xCE, 0x0E, 0x01, 0xC0, 0x00,
  0x00, 0x38, 0x18, 0xFC, 0x70, 0x00, 0xC0, 0x00, 0x06, 0x00, 0xE0, 0xCE, 0x0C, 0x00, 0xC0, 0x00,
  0x00, 0x38, 0x18, 0xFC, 0x70, 0x3F, 0xC0, 0x3E, 0x06, 0x00, 0xE7, 0xCE, 0x0C, 0x00, 0xC0, 0x00,
  0x00, 0x38, 0x18, 0xE0, 0x70, 0x3F, 0xC0, 0xFF, 0x07, 0xC0, 0xE7, 0xCE, 0x0C, 0x00, 0xC0, 0x00,
  0x00, 0x18, 0x38, 0xE0, 0x70, 0x00, 0xC0, 0xC3, 0x87, 0xC1, 0xE0, 0xCE, 0x0E, 0x01, 0xC0, 0x00,
  0x00, 0x1C, 0x30, 0xE0, 0x7F, 0xF8, 0xC1, 0xC1, 0x86, 0x03, 0xF0, 0xCE, 0x0F, 0x03, 0x80, 0x00,
  0x00, 0x0F, 0xF0, 0xE0, 0x7F, 0xF8, 0xC1, 0x81, 0xC6, 0x03, 0xB8, 0xCE, 0x07, 0xFF, 0x00, 0x00,
  0x00, 0x07, 0xC0, 0xE0, 0x00, 0x00, 0xC1, 0xC1, 0x86, 0x07, 0x1C, 0xCE, 0x01, 0xFC, 0x00, 0x00,
  0x00, 0x00, 0x00, 0xE0, 0x00, 0x00, 0xC0, 0xE3, 0x86, 0x0E, 0x1E, 0xCE, 0x03, 0x03, 0x00, 0x00,
  0x00, 0x00, 0x00, 0xE0, 0x01, 0xFE, 0x00, 0xFF, 0x06, 0x0C, 0x0C, 0xCE, 0x03, 0x07, 0x00, 0x00,
  0x00, 0x06, 0x00, 0xE0, 0x07, 0xFF, 0x80, 0x3E, 0x06, 0x00, 0x00, 0xCE, 0x03, 0x07, 0x00, 0x00,
  0x00, 0x07, 0x00, 0x60, 0x07, 0x03, 0xC0, 0x00, 0x06, 0x00, 0x00, 0xCE, 0x03, 0x07, 0x00, 0x00,
  0x00, 0x07, 0x00, 0x00, 0x0E, 0x00, 0xC0, 0x00, 0x06, 0x00, 0x00, 0xCE, 0x7F, 0xFF, 0xF8, 0x00,
  0x00, 0x07, 0x00, 0x00, 0x0E, 0x00, 0xC0, 0x00, 0x06, 0x00, 0x00, 0xCE, 0x7F, 0xFF, 0xF8, 0x00,
  0x00, 0x07, 0x00, 0x00, 0x0E, 0x00, 0xC0, 0x00, 0x06, 0x00, 0x00, 0xCE, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x07, 0xFF, 0xE0, 0x07, 0xFF, 0x80, 0x00, 0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x07, 0xFF, 0xE0, 0x01, 0xFE, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

const unsigned char bmp_name_kr[] PROGMEM = {
  0x00, 0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x30, 0x00, 0x00, 0x60, 0x00, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x03, 0xFF, 0x06, 0x00, 0xE0, 0x70, 0x3F, 0xFC, 0x60, 0xE0, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x03, 0xFF, 0x06, 0x00, 0xE0, 0x70, 0x3F, 0xFC, 0x60, 0xE0, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x03, 0x06, 0x00, 0xE0, 0x70, 0x01, 0x80, 0x60, 0xE0, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x03, 0x06, 0x00, 0xE0, 0x7E, 0x01, 0x80, 0x60, 0xE0, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x07, 0x06, 0x01, 0xF0, 0x70, 0x01, 0x80, 0x60, 0xE0, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x0E, 0x06, 0x07, 0xB8, 0x70, 0x03, 0xC0, 0x60, 0xE0, 0x11, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x3C, 0x06, 0x0F, 0x1C, 0x70, 0x03, 0xC0, 0x60, 0xFF, 0xF9, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0xF8, 0x06, 0x1E, 0x0E, 0x70, 0x07, 0xE0, 0x60, 0x7F, 0xF1, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x03, 0xE0, 0x06, 0x18, 0x06, 0x70, 0x0E, 0x70, 0x60, 0x00, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x03, 0x00, 0x06, 0x00, 0x00, 0x30, 0x3C, 0x38, 0x60, 0x00, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x7F, 0xFE, 0x00, 0x7F, 0x80, 0x30, 0x0C, 0x60, 0x1F, 0xFF, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x7F, 0xFE, 0x00, 0xFF, 0xE0, 0x00, 0x00, 0x60, 0x1F, 0xFF, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x06, 0x01, 0xC0, 0xF0, 0x00, 0x00, 0x60, 0x18, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x06, 0x03, 0x80, 0x70, 0x00, 0x00, 0x60, 0x18, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x06, 0x03, 0x80, 0x30, 0x00, 0x00, 0x60, 0x18, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x06, 0x03, 0x80, 0x70, 0x00, 0x00, 0x60, 0x18, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x60, 0x06, 0x01, 0xC0, 0xF0, 0x00, 0x00, 0x60, 0x18, 0x01, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x7F, 0xFE, 0x00, 0xFF, 0xE0, 0x00, 0x00, 0x00, 0x1F, 0xFF, 0x80, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x7F, 0xFE, 0x00, 0x7F, 0x80, 0x00, 0x00, 0x00, 0x1F, 0xFF, 0x80, 0x00, 0x00
};

enum Mood {
  NORMAL,
  HAPPY,
  SLEEPY,
  ANGRY,
  SAD,
  LOVE,
  THINKING
};

Mood currentMood = NORMAL;
Mood fallenMood = SLEEPY;

bool lastTouchState = false;
unsigned long lastTouchTime = 0;
unsigned long touchPressedAt = 0;
bool longPressHandled = false;
const unsigned long debounceMs = 250;

struct DeviceTaskView {
  bool active;
  String taskRunId;
  String sessionId;
  String stepRunId;
  String type;
  String icon;
  String text;
  String textKey;
  String renderMode;
  int priority;
  unsigned long ttlMs;
  unsigned long updatedAt;
};

DeviceTaskView taskViews[MAX_ACTIVE_TASK_SESSIONS];
int focusedTaskViewIndex = -1;
unsigned long manualFocusUntil = 0;

unsigned long lastBlinkTime = 0;
bool blinking = false;
unsigned long blinkStart = 0;

bool imuReady = false;
bool imuBaselineReady = false;
bool robotFallen = false;
float uprightAccelX = 0.0f;
float uprightAccelY = 0.0f;
float uprightAccelZ = 1.0f;
unsigned long nextImuReadAt = 0;
unsigned long fallCandidateSince = 0;
unsigned long uprightCandidateSince = 0;

// =========================
// I2C / OLED
// =========================

void setOledContrast(uint8_t value);

void printHexAddress(uint8_t address) {
  Serial.print("0x");
  if (address < 16) {
    Serial.print("0");
  }
  Serial.print(address, HEX);
}

bool isI2cDevicePresent(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

int scanI2cBus() {
  Serial.print("I2C scan on SDA ");
  Serial.print(activeSdaPin);
  Serial.print(" SCL ");
  Serial.println(activeSclPin);

  int found = 0;
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("I2C device found at ");
      printHexAddress(address);
      Serial.println();
      found++;
    } else if (error == 4) {
      Serial.print("I2C unknown error at ");
      printHexAddress(address);
      Serial.println();
    }
  }

  if (found == 0) {
    Serial.println("No I2C devices found. Check OLED VCC/GND/SDA/SCL wiring.");
  }

  return found;
}

bool selectI2cPins() {
  const int candidates[][2] = {
    {SDA_PIN, SCL_PIN},
    {SCL_PIN, SDA_PIN},
    {8, 9},
    {9, 8},
    {6, 7},
    {7, 6}
  };

  for (size_t i = 0; i < sizeof(candidates) / sizeof(candidates[0]); i++) {
    activeSdaPin = candidates[i][0];
    activeSclPin = candidates[i][1];
    Wire.begin(activeSdaPin, activeSclPin);
    Wire.setClock(100000);
    delay(20);

    int found = scanI2cBus();
    if (found > 0) {
      Serial.print("Using I2C pins SDA ");
      Serial.print(activeSdaPin);
      Serial.print(" SCL ");
      Serial.println(activeSclPin);
      return true;
    }
  }

  activeSdaPin = SDA_PIN;
  activeSclPin = SCL_PIN;
  Wire.begin(activeSdaPin, activeSclPin);
  Wire.setClock(100000);
  return false;
}

bool initOledDisplay() {
  selectI2cPins();

  if (isI2cDevicePresent(OLED_ADDRESS_PRIMARY)) {
    oledAddress = OLED_ADDRESS_PRIMARY;
  } else if (isI2cDevicePresent(OLED_ADDRESS_FALLBACK)) {
    oledAddress = OLED_ADDRESS_FALLBACK;
  } else {
    Serial.print("OLED not found at ");
    printHexAddress(OLED_ADDRESS_PRIMARY);
    Serial.print(" or ");
    printHexAddress(OLED_ADDRESS_FALLBACK);
    Serial.println(". If MPU6050 appears at 0x68 only, the OLED wiring/address is the issue.");
    return false;
  }

  Serial.print("OLED init address ");
  printHexAddress(oledAddress);
  Serial.println();

  if (!display.begin(oledAddress, true)) {
    Serial.println("SH1106 OLED init failed. Check display type, address, and power.");
    return false;
  }

  display.clearDisplay();
  display.display();
  setOledContrast(255);
  u8g2Fonts.begin(display);
  u8g2Fonts.setFont(u8g2_font_unifont_t_korean1);
  u8g2Fonts.setFontMode(1);
  u8g2Fonts.setFontDirection(0);
  u8g2Fonts.setForegroundColor(SSD1306_WHITE);
  u8g2Fonts.setBackgroundColor(SSD1306_BLACK);
  return true;
}

// =========================
// Passive Piezo Buzzer
// =========================

void beepPassive(int freq, int durationMs) {
  int halfPeriodUs = 1000000 / freq / 2;
  unsigned long start = millis();

  while (millis() - start < (unsigned long)durationMs) {
    digitalWrite(BUZZER_PIN, HIGH);
    delayMicroseconds(halfPeriodUs);
    digitalWrite(BUZZER_PIN, LOW);
    delayMicroseconds(halfPeriodUs);
  }

  digitalWrite(BUZZER_PIN, LOW);
}

void rest(int ms) {
  digitalWrite(BUZZER_PIN, LOW);
  delay(ms);
}

void playMoodSound(Mood mood) {
  switch (mood) {
    case NORMAL:
      // 짧고 기본적인 확인음
      beepPassive(700, 70);
      break;

    case HAPPY:
      // 신나는 짧은 상승음
      beepPassive(900, 60);
      rest(25);
      beepPassive(1200, 60);
      rest(25);
      beepPassive(1600, 80);
      break;

    case SLEEPY:
      // 낮아지는 졸린 소리
      beepPassive(500, 120);
      rest(40);
      beepPassive(350, 160);
      break;

    case ANGRY:
      // 낮고 짧게 반복되는 경고음
      beepPassive(220, 60);
      rest(25);
      beepPassive(180, 60);
      rest(25);
      beepPassive(220, 80);
      break;

    case SAD:
      // 내려가는 슬픈 소리
      beepPassive(600, 100);
      rest(40);
      beepPassive(420, 140);
      rest(40);
      beepPassive(300, 180);
      break;

    case LOVE:
      // 밝고 귀여운 높은 소리
      beepPassive(1000, 50);
      rest(25);
      beepPassive(1400, 50);
      rest(25);
      beepPassive(1800, 70);
      rest(25);
      beepPassive(1400, 70);
      break;

    case THINKING:
      // 생각하는 느낌의 톡톡 소리
      beepPassive(650, 50);
      rest(70);
      beepPassive(850, 50);
      rest(70);
      beepPassive(650, 50);
      break;
  }
}

void setOledContrast(uint8_t value) {
  display.oled_command(OLED_CMD_SET_CONTRAST);
  display.oled_command(value);
}

void drawIntroBitmap(const unsigned char* bitmap, int bitmapHeight, uint8_t contrast) {
  setOledContrast(contrast);

  display.clearDisplay();

  int y = (SCREEN_HEIGHT - bitmapHeight) / 2;

  display.drawBitmap(
    0,
    y,
    bitmap,
    INTRO_BITMAP_WIDTH,
    bitmapHeight,
    SSD1306_WHITE
  );

  display.display();
}

void fadeIntroBitmap(const unsigned char* bitmap, int bitmapHeight) {
  for (int c = 0; c <= 255; c += 15) {
    drawIntroBitmap(bitmap, bitmapHeight, c);
    delay(35);
  }

  delay(500);

  for (int c = 255; c >= 0; c -= 15) {
    drawIntroBitmap(bitmap, bitmapHeight, c);
    delay(35);
  }

  display.clearDisplay();
  display.display();
  delay(250);
}

void playIntro() {
  display.clearDisplay();
  display.display();
  delay(100);

  beepPassive(900, 70);
  fadeIntroBitmap(bmp_hello_kr, HELLO_BITMAP_HEIGHT);

  display.clearDisplay();
  display.display();
  delay(100);

  beepPassive(1200, 70);
  fadeIntroBitmap(bmp_name_kr, NAME_BITMAP_HEIGHT);

  display.clearDisplay();
  display.display();
  delay(100);

  setOledContrast(255);
}

// =========================
// Text / Status Screens
// =========================

bool isDue(unsigned long deadline) {
  return deadline == 0 || (long)(millis() - deadline) >= 0;
}

void printClipped(int16_t x, int16_t y, const String& text, int maxChars) {
  String value = text;
  if (value.length() > maxChars) {
    value = value.substring(0, maxChars);
  }

  display.setCursor(x, y);
  display.print(value);
}

String deviceTextForKey(String textKey, const String& fallback) {
  textKey.trim();
  textKey.toUpperCase();

  if (textKey == "CHECKING_REQUEST") return "요청 확인중";
  if (textKey == "SEARCHING") return "검색 중";
  if (textKey == "HTTP_CALL") return "HTTP 호출 중";
  if (textKey == "WRITING_REPLY") return "답변 생성중";
  if (textKey == "REVIEWING") return "검토 중";
  if (textKey == "DELEGATING") return "작업 위임중";
  if (textKey == "TOOL_RUNNING") return "도구 실행중";
  if (textKey == "WAITING_INPUT") return "입력 대기";
  if (textKey == "DONE_SUCCESS") return "성공";
  if (textKey == "FAILED") return "실패";
  if (textKey == "CANCELED") return "취소됨";
  if (textKey == "STEP_DONE") return "단계 완료";
  if (textKey == "WORKING") return "작업중";

  return fallback;
}

void printUnicodeLine(int16_t x, int16_t baseline, const String& text) {
  u8g2Fonts.setForegroundColor(SSD1306_WHITE);
  u8g2Fonts.setBackgroundColor(SSD1306_BLACK);
  u8g2Fonts.setCursor(x, baseline);
  u8g2Fonts.print(text);
}

void setMessageDeadline(unsigned long ttlMs) {
  unsigned long effectiveTtl = ttlMs == 0 ? SERVER_MESSAGE_DISPLAY_MS : ttlMs;
  messageUntil = millis() + effectiveTtl;
}

long secondsUntil(unsigned long deadline) {
  if (deadline == 0) {
    return 0;
  }

  long remainingMs = (long)(deadline - millis());
  if (remainingMs <= 0) {
    return 0;
  }

  return (remainingMs + 999) / 1000;
}

void showStatus(const String& line1, const String& line2 = "", const String& line3 = "") {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  printClipped(0, 0, line1, 21);
  printClipped(0, 20, line2, 21);
  printClipped(0, 40, line3, 21);
  display.display();

  Serial.print("[status] ");
  Serial.print(line1);
  Serial.print(" ");
  Serial.print(line2);
  Serial.print(" ");
  Serial.println(line3);
}

void showPairCode() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  printClipped(0, 0, "PAIR CODE", 21);
  printClipped(0, 12, deviceId, 21);

  display.setTextSize(2);
  display.setCursor(28, 28);
  display.print(currentPairCode.length() > 0 ? currentPairCode : "------");

  display.setTextSize(1);
  printClipped(0, 54, String("expires ") + secondsUntil(pairCodeExpiresAt) + "s", 21);
  display.display();
}

void showServerMessage(const String& title, const String& text, unsigned long ttlMs) {
  showStatus(title, text, paired ? "service ready" : deviceId);
  setMessageDeadline(ttlMs);
}

bool isTerminalTaskType(String type) {
  type.toLowerCase();
  return type == "done" || type == "failed" || type == "canceled";
}

bool isWaitingTaskType(String type) {
  type.toLowerCase();
  return type == "waiting";
}

void clearTaskView(int index) {
  if (index < 0 || index >= MAX_ACTIVE_TASK_SESSIONS) {
    return;
  }
  taskViews[index] = DeviceTaskView();
  if (focusedTaskViewIndex == index) {
    focusedTaskViewIndex = -1;
  }
}

int findTaskViewIndex(const String& taskRunId) {
  if (taskRunId.length() == 0) {
    return -1;
  }
  for (int i = 0; i < MAX_ACTIVE_TASK_SESSIONS; i++) {
    if (taskViews[i].active && taskViews[i].taskRunId == taskRunId) {
      return i;
    }
  }
  return -1;
}

int firstActiveTaskViewIndex() {
  for (int i = 0; i < MAX_ACTIVE_TASK_SESSIONS; i++) {
    if (taskViews[i].active) {
      return i;
    }
  }
  return -1;
}

int firstEmptyTaskViewIndex() {
  for (int i = 0; i < MAX_ACTIVE_TASK_SESSIONS; i++) {
    if (!taskViews[i].active) {
      return i;
    }
  }
  return -1;
}

int activeTaskViewCount() {
  int count = 0;
  for (int i = 0; i < MAX_ACTIVE_TASK_SESSIONS; i++) {
    if (taskViews[i].active) {
      count++;
    }
  }
  return count;
}

String compactTaskRunId(const String& taskRunId) {
  if (taskRunId.length() <= 8) {
    return taskRunId;
  }
  return taskRunId.substring(taskRunId.length() - 8);
}

void showTaskViewMessage(const DeviceTaskView& view, unsigned long ttlMs) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  String title = String("Task ") + compactTaskRunId(view.taskRunId);
  printClipped(0, 0, title, 21);

  String statusText = deviceTextForKey(view.textKey, view.text.length() > 0 ? view.text : view.type);
  printUnicodeLine(0, 32, statusText);

  String footer = "slot ";
  footer += String(focusedTaskViewIndex + 1);
  footer += "/";
  footer += String(activeTaskViewCount());
  if (isWaitingTaskType(view.type)) {
    footer += " waiting";
  }
  printClipped(0, 54, footer, 21);

  display.display();
  setMessageDeadline(ttlMs);
}

void showFocusedTaskView(unsigned long ttlMs = SERVER_MESSAGE_DISPLAY_MS) {
  if (focusedTaskViewIndex < 0 || focusedTaskViewIndex >= MAX_ACTIVE_TASK_SESSIONS || !taskViews[focusedTaskViewIndex].active) {
    focusedTaskViewIndex = firstActiveTaskViewIndex();
  }
  if (focusedTaskViewIndex < 0) {
    return;
  }
  showTaskViewMessage(taskViews[focusedTaskViewIndex], ttlMs);
}

void focusTaskView(int index, bool manual) {
  if (index < 0 || index >= MAX_ACTIVE_TASK_SESSIONS || !taskViews[index].active) {
    focusedTaskViewIndex = firstActiveTaskViewIndex();
    return;
  }
  focusedTaskViewIndex = index;
  if (manual) {
    manualFocusUntil = millis() + DEVICE_TASK_MANUAL_FOCUS_MS;
  }
}

int nextActiveTaskViewIndex(int currentIndex) {
  for (int offset = 1; offset <= MAX_ACTIVE_TASK_SESSIONS; offset++) {
    int index = (currentIndex + offset + MAX_ACTIVE_TASK_SESSIONS) % MAX_ACTIVE_TASK_SESSIONS;
    if (taskViews[index].active) {
      return index;
    }
  }
  return -1;
}

void cycleTaskViewByTouch() {
  int count = activeTaskViewCount();
  if (count == 0) {
    nextMood();
    return;
  }

  int baseIndex = focusedTaskViewIndex >= 0 ? focusedTaskViewIndex : firstActiveTaskViewIndex();
  int nextIndex = count == 1 ? baseIndex : nextActiveTaskViewIndex(baseIndex);
  focusTaskView(nextIndex, true);
  showFocusedTaskView(SERVER_MESSAGE_DISPLAY_MS);
}

void upsertTaskView(
  const String& taskRunId,
  const String& sessionId,
  const String& stepRunId,
  const String& type,
  const String& icon,
  const String& text,
  const String& textKey,
  const String& renderMode,
  int priority,
  unsigned long ttlMs,
  bool focus
) {
  if (taskRunId.length() == 0) {
    return;
  }

  int index = findTaskViewIndex(taskRunId);
  if (isTerminalTaskType(type)) {
    if (index >= 0) {
      clearTaskView(index);
    }
    return;
  }

  if (index < 0) {
    index = firstEmptyTaskViewIndex();
  }
  if (index < 0) {
    // 최대 3개 활성 세션만 유지한다. 꽉 찬 상태의 새 세션은 기존 실시간 표시를 보존한다.
    return;
  }

  taskViews[index].active = true;
  taskViews[index].taskRunId = taskRunId;
  taskViews[index].sessionId = sessionId;
  taskViews[index].stepRunId = stepRunId;
  taskViews[index].type = type;
  taskViews[index].icon = icon;
  taskViews[index].text = text;
  taskViews[index].textKey = textKey;
  taskViews[index].renderMode = renderMode;
  taskViews[index].priority = priority;
  taskViews[index].ttlMs = ttlMs;
  taskViews[index].updatedAt = millis();

  bool manualFocusActive = manualFocusUntil > 0 && !isDue(manualFocusUntil);
  if (isWaitingTaskType(type) || focus || !manualFocusActive || focusedTaskViewIndex < 0) {
    focusTaskView(index, false);
  }
}

// =========================
// Device Identity
// =========================

String macSuffix() {
  uint64_t mac = ESP.getEfuseMac();
  char suffix[7];
  snprintf(suffix, sizeof(suffix), "%06x", (uint32_t)(mac & 0xFFFFFF));
  return String(suffix);
}

String buildDeviceId() {
  return "deskmate-c3-" + macSuffix();
}

String buildNonce() {
  return String(macSuffix()) + "-" + String((uint32_t)millis(), HEX) + "-" + String(random(100000, 999999));
}

void beginWifiAttempt();

// =========================
// Wi-Fi Provisioning
// =========================

String buildSetupApSsid() {
  return "DeskMate-" + macSuffix();
}

bool hasWifiCredentials() {
  return wifiSsid.length() > 0;
}

void loadWifiCredentials() {
  wifiSsid = preferences.getString("wifiSsid", "");
  wifiPassword = preferences.getString("wifiPassword", "");

  if (wifiSsid.length() == 0 && strlen(DEFAULT_WIFI_SSID) > 0) {
    wifiSsid = DEFAULT_WIFI_SSID;
    wifiPassword = DEFAULT_WIFI_PASSWORD;
  }

  Serial.print("wifi ssid saved: ");
  Serial.println(wifiSsid.length() > 0 ? wifiSsid : "(none)");
}

String htmlEscape(const String& value) {
  String escaped = value;
  escaped.replace("&", "&amp;");
  escaped.replace("<", "&lt;");
  escaped.replace(">", "&gt;");
  escaped.replace("\"", "&quot;");
  escaped.replace("'", "&#39;");
  return escaped;
}

String wifiSetupPage(const String& title, const String& message) {
  String page;
  page.reserve(2800);
  page += "<!doctype html><html><head><meta charset=\"utf-8\">";
  page += "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">";
  page += "<title>DeskMate WiFi Setup</title>";
  page += "<style>";
  page += "body{font-family:Arial,sans-serif;margin:0;background:#f4f6f8;color:#111827}";
  page += "main{max-width:420px;margin:0 auto;padding:28px 18px}";
  page += "section{background:white;border:1px solid #d8dee8;border-radius:8px;padding:20px}";
  page += "h1{font-size:22px;margin:0 0 8px}";
  page += "p{font-size:14px;line-height:1.45;color:#4b5563}";
  page += "label{display:block;font-size:13px;font-weight:700;margin:16px 0 6px}";
  page += "input{box-sizing:border-box;width:100%;font-size:16px;padding:11px;border:1px solid #b8c0cc;border-radius:6px}";
  page += "button{width:100%;margin-top:18px;padding:12px;border:0;border-radius:6px;background:#2563eb;color:white;font-size:16px;font-weight:700}";
  page += ".hint{font-size:12px;color:#6b7280}.msg{padding:10px;border-radius:6px;background:#eef2ff;color:#3730a3}";
  page += "</style></head><body><main><section>";
  page += "<h1>";
  page += htmlEscape(title);
  page += "</h1>";
  if (message.length() > 0) {
    page += "<p class=\"msg\">";
    page += htmlEscape(message);
    page += "</p>";
  }
  page += "<p>Connect DeskMate to your WiFi network. The device will save this setting and reconnect automatically.</p>";
  page += "<form method=\"post\" action=\"/save\">";
  page += "<label for=\"ssid\">WiFi name</label>";
  page += "<input id=\"ssid\" name=\"ssid\" maxlength=\"32\" value=\"";
  page += htmlEscape(wifiSsid);
  page += "\" required autocomplete=\"off\">";
  page += "<label for=\"password\">WiFi password</label>";
  page += "<input id=\"password\" name=\"password\" maxlength=\"64\" type=\"password\" autocomplete=\"current-password\">";
  page += "<button type=\"submit\">Save and connect</button>";
  page += "</form>";
  page += "<p class=\"hint\">Setup AP: ";
  page += htmlEscape(setupApSsid);
  page += "<br>Fallback URL: http://";
  page += setupApIp.toString();
  page += "</p></section></main></body></html>";
  return page;
}

void sendWifiSetupPage(const String& title, const String& message = "") {
  setupServer.sendHeader("Cache-Control", "no-store");
  setupServer.send(200, "text/html", wifiSetupPage(title, message));
}

void redirectToWifiSetupPage() {
  setupServer.sendHeader("Location", String("http://") + setupApIp.toString() + "/", true);
  setupServer.send(302, "text/plain", "");
}

void handleWifiSetupSave() {
  String ssid = setupServer.arg("ssid");
  String password = setupServer.arg("password");
  ssid.trim();

  if (ssid.length() == 0) {
    sendWifiSetupPage("DeskMate WiFi Setup", "WiFi name is required.");
    return;
  }

  wifiSsid = ssid;
  wifiPassword = password;
  preferences.putString("wifiSsid", wifiSsid);
  preferences.putString("wifiPassword", wifiPassword);

  wifiReconnectPending = true;
  wifiReconnectAt = millis() + 1200;

  Serial.print("Saved WiFi SSID: ");
  Serial.println(wifiSsid);
  sendWifiSetupPage("WiFi saved", "DeskMate is connecting to the saved network now.");
  showStatus("WiFi saved", wifiSsid, "connecting soon");
}

void setupWifiSetupServerRoutes() {
  setupServer.on("/", HTTP_GET, []() {
    sendWifiSetupPage("DeskMate WiFi Setup");
  });
  setupServer.on("/save", HTTP_POST, handleWifiSetupSave);
  setupServer.on("/generate_204", HTTP_GET, redirectToWifiSetupPage);
  setupServer.on("/gen_204", HTTP_GET, redirectToWifiSetupPage);
  setupServer.on("/hotspot-detect.html", HTTP_GET, []() {
    sendWifiSetupPage("DeskMate WiFi Setup");
  });
  setupServer.on("/connecttest.txt", HTTP_GET, redirectToWifiSetupPage);
  setupServer.on("/ncsi.txt", HTTP_GET, redirectToWifiSetupPage);
  setupServer.onNotFound(redirectToWifiSetupPage);
}

void startWifiSetupMode(const String& reason) {
  if (wifiSetupMode) {
    return;
  }

  mqtt.disconnect();
  WiFi.disconnect();
  delay(100);
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(setupApIp, setupApGateway, setupApSubnet);
  WiFi.softAP(setupApSsid.c_str());

  dnsServer.start(DNS_PORT, "*", setupApIp);

  if (!wifiSetupRoutesConfigured) {
    setupWifiSetupServerRoutes();
    wifiSetupRoutesConfigured = true;
  }

  if (!wifiSetupServerStarted) {
    setupServer.begin();
    wifiSetupServerStarted = true;
  }

  wifiSetupMode = true;
  wifiStarted = false;
  wifiWasConnected = false;
  pairingStatusSynced = false;
  showStatus("WiFi setup", setupApSsid, setupApIp.toString());

  Serial.print("WiFi setup AP started: ");
  Serial.print(setupApSsid);
  Serial.print(" reason=");
  Serial.println(reason);
}

void stopWifiSetupMode() {
  if (!wifiSetupMode) {
    return;
  }

  dnsServer.stop();
  setupServer.stop();
  WiFi.softAPdisconnect(true);
  delay(100);

  wifiSetupMode = false;
  wifiSetupServerStarted = false;
  wifiStarted = false;
  wifiWasConnected = false;
  pairingStatusSynced = false;
  nextWifiAttemptAt = 0;
  wifiAttemptStartedAt = 0;

  Serial.println("WiFi setup AP stopped.");
}

void maintainWifiSetupMode() {
  if (!wifiSetupMode) {
    return;
  }

  dnsServer.processNextRequest();
  setupServer.handleClient();

  if (wifiReconnectPending && isDue(wifiReconnectAt)) {
    wifiReconnectPending = false;
    stopWifiSetupMode();
    beginWifiAttempt();
  }
}

// =========================
// Wi-Fi / Pairing / MQTT
// =========================

String pairingStartUrl() {
  return String(BACKEND_BASE_URL) + "/api/v1/iot/pairing/start";
}

String pairingStatusUrl() {
  return String(BACKEND_BASE_URL) + "/api/v1/iot/pairing/devices/" + deviceId + "/status";
}

bool hasMqttAuth() {
  return strlen(MQTT_USERNAME) > 0;
}

const char* wifiStatusLabel(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS:
      return "idle";
    case WL_NO_SSID_AVAIL:
      return "ssid not found";
    case WL_SCAN_COMPLETED:
      return "scan done";
    case WL_CONNECTED:
      return "connected";
    case WL_CONNECT_FAILED:
      return "connect failed";
    case WL_CONNECTION_LOST:
      return "connection lost";
    case WL_DISCONNECTED:
      return "disconnected";
    default:
      return "unknown";
  }
}

void beginWifiAttempt() {
  if (!hasWifiCredentials()) {
    startWifiSetupMode("missing credentials");
    return;
  }

  wifiStarted = true;
  nextWifiAttemptAt = millis() + WIFI_RETRY_INTERVAL_MS;
  wifiAttemptStartedAt = millis();
  WiFi.disconnect(true, true);
  delay(150);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
  showStatus("WiFi connecting", wifiSsid, deviceId);
  Serial.print("WiFi attempt started. ssid=");
  Serial.println(wifiSsid);
}

void maintainWifi() {
  if (wifiSetupMode) {
    maintainWifiSetupMode();
    return;
  }

  if (!hasWifiCredentials()) {
    startWifiSetupMode("missing credentials");
    return;
  }

  bool connected = WiFi.status() == WL_CONNECTED;

  if (connected && !wifiWasConnected) {
    wifiWasConnected = true;
    wifiAttemptStartedAt = 0;
    pairingStatusSynced = false;
    showStatus("WiFi connected", WiFi.localIP().toString(), deviceId);
    nextStatusCheckAt = 0;
    nextPairingAttemptAt = 0;
    delay(500);
  }

  if (connected) {
    return;
  }

  if (wifiStarted && wifiAttemptStartedAt > 0 && millis() - wifiAttemptStartedAt >= WIFI_CONNECT_TIMEOUT_MS) {
    wl_status_t status = WiFi.status();
    String reason = wifiStatusLabel(status);
    showStatus("WiFi failed", reason, setupApSsid);
    Serial.print("WiFi connect timeout. status=");
    Serial.print((int)status);
    Serial.print(" ");
    Serial.println(reason);
    startWifiSetupMode("connect timeout");
    return;
  }

  if (wifiStarted && wifiAttemptStartedAt > 0) {
    return;
  }

  if (wifiWasConnected) {
    wifiWasConnected = false;
    wifiAttemptStartedAt = 0;
    mqtt.disconnect();
    showStatus("WiFi lost", "reconnecting", deviceId);
  }

  if (!wifiStarted || isDue(nextWifiAttemptAt)) {
    beginWifiAttempt();
  }
}

bool parsePairingResponse(const String& payload, String& pairCode, long& expiresInSeconds) {
  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    Serial.print("Pairing JSON parse failed: ");
    Serial.println(error.c_str());
    return false;
  }

  const char* parsedCode = "";
  long parsedExpires = 300;

  if (!doc["data"].isNull()) {
    parsedCode = doc["data"]["pairCode"] | "";
    parsedExpires = doc["data"]["expiresInSeconds"] | 300;
  } else {
    parsedCode = doc["pairCode"] | "";
    parsedExpires = doc["expiresInSeconds"] | 300;
  }

  if (strlen(parsedCode) != 6) {
    Serial.print("Pairing response missing pairCode: ");
    Serial.println(payload);
    return false;
  }

  pairCode = String(parsedCode);
  expiresInSeconds = parsedExpires > 0 ? parsedExpires : 300;
  return true;
}

bool parsePairingStatusResponse(const String& payload, bool& serverPaired, String& serverStatus) {
  StaticJsonDocument<768> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    Serial.print("Pairing status JSON parse failed: ");
    Serial.println(error.c_str());
    return false;
  }

  JsonVariant source;
  if (doc["data"].isNull()) {
    source = doc.as<JsonVariant>();
  } else {
    source = doc["data"].as<JsonVariant>();
  }
  if (source["paired"].isNull()) {
    Serial.print("Pairing status missing paired: ");
    Serial.println(payload);
    return false;
  }

  serverPaired = source["paired"] | false;
  serverStatus = String((const char*)(source["status"] | ""));
  return true;
}

bool isAlreadyPairedResponse(int status, const String& payload) {
  if (status != 409) {
    return false;
  }

  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (!error) {
    String code = doc["code"] | "";
    if (code == "DEVICE_ALREADY_PAIRED") {
      return true;
    }
  }

  return payload.indexOf("DEVICE_ALREADY_PAIRED") >= 0
    || payload.indexOf("이미 등록") >= 0;
}

void markAlreadyPaired() {
  paired = true;
  currentPairCode = "";
  pairCodeExpiresAt = 0;
  preferences.putBool("paired", true);
  currentMood = NORMAL;
  showServerMessage("DeskMate", "service ready", SERVER_MESSAGE_DISPLAY_MS);
}

void resetLocalPairingState(const String& reason) {
  paired = false;
  currentPairCode = "";
  pairCodeExpiresAt = 0;
  nextPairingAttemptAt = 0;
  nextPairCodeRedrawAt = 0;
  preferences.putBool("paired", false);
  currentMood = THINKING;
  playMoodSound(THINKING);
  showStatus("Pairing reset", reason, deviceId);
}

bool syncPairingStatusWithServer() {
  if (WiFi.status() != WL_CONNECTED || !isDue(nextStatusCheckAt)) {
    return false;
  }

  nextStatusCheckAt = millis() + STATUS_CHECK_RETRY_INTERVAL_MS;

  HTTPClient http;
  String url = pairingStatusUrl();
  http.begin(url);
  http.setTimeout(5000);

  int status = http.GET();
  String payload = http.getString();
  http.end();

  Serial.print("Pairing status HTTP status: ");
  Serial.println(status);
  Serial.print("Pairing status response: ");
  Serial.println(payload);

  if (status < 200 || status >= 300) {
    showStatus("Status check failed", String("HTTP ") + status, deviceId);
    return false;
  }

  bool serverPaired = false;
  String serverStatus;
  if (!parsePairingStatusResponse(payload, serverPaired, serverStatus)) {
    showStatus("Status check failed", "bad response", deviceId);
    return false;
  }

  pairingStatusSynced = true;

  if (!serverPaired && paired) {
    resetLocalPairingState("server unpaired");
    requestPairCode();
    return true;
  }

  if (serverPaired && !paired) {
    Serial.println("Server says paired. Restoring local paired state.");
    markAlreadyPaired();
    return true;
  }

  return true;
}

bool requestPairCode() {
  if (paired || WiFi.status() != WL_CONNECTED) {
    return false;
  }

  nextPairingAttemptAt = millis() + PAIRING_RETRY_INTERVAL_MS;

  HTTPClient http;
  String url = pairingStartUrl();
  http.begin(url);
  http.setTimeout(5000);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> request;
  request["deviceId"] = deviceId;
  request["nonce"] = buildNonce();
  request["firmwareVersion"] = FIRMWARE_VERSION;

  String body;
  serializeJson(request, body);

  showStatus("Pairing start", "requesting code", deviceId);
  int status = http.POST(body);
  String payload = http.getString();
  http.end();

  Serial.print("Pairing HTTP status: ");
  Serial.println(status);
  Serial.print("Pairing response: ");
  Serial.println(payload);

  if (status < 200 || status >= 300) {
    if (isAlreadyPairedResponse(status, payload)) {
      Serial.println("Device already paired. Entering idle display mode.");
      markAlreadyPaired();
      return true;
    }

    showStatus("Pairing failed", String("HTTP ") + status, deviceId);
    return false;
  }

  String pairCode;
  long expiresInSeconds = 300;
  if (!parsePairingResponse(payload, pairCode, expiresInSeconds)) {
    showStatus("Pairing failed", "bad response", deviceId);
    return false;
  }

  currentPairCode = pairCode;
  pairCodeExpiresAt = millis() + ((unsigned long)expiresInSeconds * 1000UL);
  nextPairingAttemptAt = pairCodeExpiresAt > PAIRING_REFRESH_SKEW_MS
    ? pairCodeExpiresAt - PAIRING_REFRESH_SKEW_MS
    : pairCodeExpiresAt;
  nextPairCodeRedrawAt = 0;

  currentMood = THINKING;
  playMoodSound(THINKING);
  showPairCode();
  return true;
}

void maintainPairing() {
  if (paired || WiFi.status() != WL_CONNECTED) {
    return;
  }

  bool missingCode = currentPairCode.length() == 0;
  bool expiredCode = pairCodeExpiresAt > 0 && isDue(pairCodeExpiresAt);

  if ((missingCode || expiredCode || isDue(nextPairingAttemptAt)) && isDue(nextPairingAttemptAt)) {
    currentPairCode = "";
    requestPairCode();
    return;
  }

  if (currentPairCode.length() > 0 && isDue(nextPairCodeRedrawAt)) {
    nextPairCodeRedrawAt = millis() + 1000;
    showPairCode();
  }
}

void updateMoodFromServerEvent(String type, String icon, String text) {
  type.toLowerCase();
  icon.toLowerCase();
  text.toLowerCase();

  if (type.indexOf("failed") >= 0 || type.indexOf("error") >= 0 || icon == "error") {
    currentMood = SAD;
  } else if (type.indexOf("done") >= 0 || icon == "success" || text.indexOf("done") >= 0 || text.indexOf("connected") >= 0) {
    currentMood = HAPPY;
  } else if (type.indexOf("waiting") >= 0 || icon == "wait" || icon == "question") {
    currentMood = THINKING;
  } else if (type.indexOf("started") >= 0 || type.indexOf("step") >= 0 || text.indexOf("working") >= 0) {
    currentMood = THINKING;
  } else {
    currentMood = NORMAL;
  }

  playMoodSound(currentMood);
}

bool isPairingConnectedPayload(String type, String sessionId, String stepRunId, String icon, String text) {
  type.toLowerCase();
  sessionId.toLowerCase();
  stepRunId.toLowerCase();
  icon.toLowerCase();
  text.toLowerCase();

  return type == "paired"
    || type == "pairing_claimed"
    || icon == "success"
    || text == "connected"
    || (sessionId == "pairing" && text.indexOf("connected") >= 0)
    || (stepRunId == "pairing" && text.indexOf("connected") >= 0);
}

bool isPairingResetPayload(String sessionId, String stepRunId, String text) {
  sessionId.toLowerCase();
  stepRunId.toLowerCase();
  text.toLowerCase();

  return sessionId == "pairing" && stepRunId == "reset" && text == "unpaired";
}

void markPaired(unsigned long ttlMs) {
  paired = true;
  currentPairCode = "";
  pairCodeExpiresAt = 0;
  preferences.putBool("paired", true);
  currentMood = HAPPY;
  playMoodSound(HAPPY);
  showServerMessage("Linked!", "connected", ttlMs);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<2048> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    Serial.print("MQTT JSON parse failed: ");
    Serial.println(error.c_str());
    showServerMessage("MQTT JSON error", error.c_str(), 3000);
    return;
  }

  String type = doc["type"] | "INFO";
  String sessionId = doc["sessionId"] | "";
  String taskRunId = doc["taskRunId"] | "";
  String stepRunId = doc["stepRunId"] | "";
  String icon = doc["icon"] | "info";
  String text = doc["text"] | "";
  String textKey = doc["textKey"] | "";
  String renderMode = doc["renderMode"] | "";
  int priority = doc["priority"] | 0;
  bool focus = doc["focus"] | false;
  unsigned long ttlMs = doc["ttlMs"] | SERVER_MESSAGE_DISPLAY_MS;

  Serial.print("MQTT message [");
  Serial.print(topic);
  Serial.print("]: ");
  serializeJson(doc, Serial);
  Serial.println();

  if (isPairingResetPayload(sessionId, stepRunId, text)) {
    resetLocalPairingState("server unpaired");
    requestPairCode();
    return;
  }

  if (isPairingConnectedPayload(type, sessionId, stepRunId, icon, text)) {
    markPaired(ttlMs);
    return;
  }

  if (text.length() == 0) {
    text = type.length() > 0 ? type : "event received";
  }

  if (taskRunId.length() == 0) {
    taskRunId = stepRunId;
  }

  bool terminalPayload = isTerminalTaskType(type);
  updateMoodFromServerEvent(type, icon, text);
  upsertTaskView(
    taskRunId,
    sessionId,
    stepRunId,
    type,
    icon,
    text,
    textKey,
    renderMode,
    priority,
    ttlMs,
    focus
  );

  if (terminalPayload) {
    showServerMessage(String("Task ") + compactTaskRunId(taskRunId), deviceTextForKey(textKey, text), ttlMs);
  } else if (taskRunId.length() > 0 && focusedTaskViewIndex >= 0) {
    showFocusedTaskView(ttlMs);
  } else {
    showServerMessage("DeskMate", deviceTextForKey(textKey, text), ttlMs);
  }
}

bool connectMqttOnce() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(2048);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(5);

  String clientId = deviceId + "-" + String(random(1000, 9999));
  bool ok = hasMqttAuth()
    ? mqtt.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)
    : mqtt.connect(clientId.c_str());

  if (!ok) {
    Serial.print("MQTT connect failed, state=");
    Serial.println(mqtt.state());
    return false;
  }

  displayTopic = String("devices/") + deviceId + "/display";
  mqtt.subscribe(displayTopic.c_str(), 1);

  Serial.print("MQTT subscribed: ");
  Serial.println(displayTopic);

  if (paired || currentPairCode.length() == 0) {
    showStatus("MQTT connected", MQTT_HOST, deviceId);
  }

  return true;
}

void maintainMqtt() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }

  if (isDue(nextMqttAttemptAt)) {
    nextMqttAttemptAt = millis() + MQTT_RETRY_INTERVAL_MS;
    connectMqttOnce();
  }
}

// =========================
// MPU6050 Fall Detection
// =========================

bool mpuWriteRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(mpuAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readMpuAccelRaw(int16_t& rawX, int16_t& rawY, int16_t& rawZ) {
  Wire.beginTransmission(mpuAddress);
  Wire.write(MPU6050_ACCEL_XOUT_H);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  uint8_t received = Wire.requestFrom(mpuAddress, (uint8_t)6);
  if (received != 6) {
    return false;
  }

  rawX = (int16_t)((Wire.read() << 8) | Wire.read());
  rawY = (int16_t)((Wire.read() << 8) | Wire.read());
  rawZ = (int16_t)((Wire.read() << 8) | Wire.read());
  return true;
}

bool readMpuAccelG(float& accelX, float& accelY, float& accelZ) {
  int16_t rawX;
  int16_t rawY;
  int16_t rawZ;
  if (!readMpuAccelRaw(rawX, rawY, rawZ)) {
    return false;
  }

  accelX = rawX / MPU6050_ACCEL_SCALE;
  accelY = rawY / MPU6050_ACCEL_SCALE;
  accelZ = rawZ / MPU6050_ACCEL_SCALE;
  return true;
}

float accelMagnitude(float x, float y, float z) {
  return sqrtf(x * x + y * y + z * z);
}

bool normalizeAccel(float& x, float& y, float& z) {
  float magnitude = accelMagnitude(x, y, z);
  if (magnitude < 0.15f) {
    return false;
  }

  x /= magnitude;
  y /= magnitude;
  z /= magnitude;
  return true;
}

float angleFromUpright(float accelX, float accelY, float accelZ) {
  if (!imuBaselineReady || !normalizeAccel(accelX, accelY, accelZ)) {
    return 0.0f;
  }

  float dot = accelX * uprightAccelX + accelY * uprightAccelY + accelZ * uprightAccelZ;
  dot = constrain(dot, -1.0f, 1.0f);
  return acosf(dot) * 180.0f / PI;
}

bool initMpu6050() {
  if (isI2cDevicePresent(MPU6050_ADDR_PRIMARY)) {
    mpuAddress = MPU6050_ADDR_PRIMARY;
  } else if (isI2cDevicePresent(MPU6050_ADDR_FALLBACK)) {
    mpuAddress = MPU6050_ADDR_FALLBACK;
  } else {
    Serial.print("MPU6050 not found at ");
    printHexAddress(MPU6050_ADDR_PRIMARY);
    Serial.print(" or ");
    printHexAddress(MPU6050_ADDR_FALLBACK);
    Serial.println(". Fall detection disabled.");
    return false;
  }

  Serial.print("MPU6050 init address ");
  printHexAddress(mpuAddress);
  Serial.println();

  if (!mpuWriteRegister(MPU6050_PWR_MGMT_1, 0x00)) {
    Serial.println("MPU6050 wake failed. Fall detection disabled.");
    return false;
  }

  delay(100);

  if (!mpuWriteRegister(MPU6050_ACCEL_CONFIG, 0x00)) {
    Serial.println("MPU6050 accel config failed. Fall detection disabled.");
    return false;
  }

  Serial.println("MPU6050 ready.");
  return true;
}

bool calibrateUprightPose() {
  if (!imuReady) {
    return false;
  }

  showStatus("Gyro calibrating", "keep robot upright", deviceId);

  float sumX = 0.0f;
  float sumY = 0.0f;
  float sumZ = 0.0f;
  int samples = 0;

  for (int i = 0; i < 30; i++) {
    float accelX;
    float accelY;
    float accelZ;
    if (readMpuAccelG(accelX, accelY, accelZ)) {
      sumX += accelX;
      sumY += accelY;
      sumZ += accelZ;
      samples++;
    }
    delay(20);
  }

  if (samples < 10) {
    Serial.println("MPU6050 calibration failed. Fall detection disabled.");
    showStatus("Gyro skipped", "calibration failed", deviceId);
    return false;
  }

  uprightAccelX = sumX / samples;
  uprightAccelY = sumY / samples;
  uprightAccelZ = sumZ / samples;
  imuBaselineReady = normalizeAccel(uprightAccelX, uprightAccelY, uprightAccelZ);

  Serial.print("Upright accel baseline: ");
  Serial.print(uprightAccelX, 3);
  Serial.print(", ");
  Serial.print(uprightAccelY, 3);
  Serial.print(", ");
  Serial.println(uprightAccelZ, 3);

  showStatus("Gyro ready", "fall detect on", deviceId);
  delay(500);
  return imuBaselineReady;
}

Mood chooseFallenMood(float accelX, float accelY) {
  if (fabsf(accelX) >= fabsf(accelY)) {
    return accelX >= 0.0f ? SLEEPY : SAD;
  }

  return accelY >= 0.0f ? SLEEPY : SAD;
}

void enterFallenState(Mood mood) {
  robotFallen = true;
  fallenMood = mood;
  playMoodSound(mood);
  Serial.println(mood == SLEEPY ? "Robot fallen: sleepy expression" : "Robot fallen: sad expression");
}

void leaveFallenState() {
  robotFallen = false;
  playMoodSound(currentMood);
  Serial.println("Robot upright: restored expression");
}

void updateFallDetection() {
  if (!imuReady || !imuBaselineReady || !isDue(nextImuReadAt)) {
    return;
  }

  unsigned long now = millis();
  nextImuReadAt = now + IMU_READ_INTERVAL_MS;

  float accelX;
  float accelY;
  float accelZ;
  if (!readMpuAccelG(accelX, accelY, accelZ)) {
    Serial.println("MPU6050 accel read failed.");
    return;
  }

  float tiltAngle = angleFromUpright(accelX, accelY, accelZ);

  if (!robotFallen) {
    if (tiltAngle >= FALLEN_ANGLE_DEGREES) {
      if (fallCandidateSince == 0) {
        fallCandidateSince = now;
      }
      if (now - fallCandidateSince >= FALL_CONFIRM_MS) {
        enterFallenState(chooseFallenMood(accelX, accelY));
        uprightCandidateSince = 0;
      }
    } else {
      fallCandidateSince = 0;
    }
    return;
  }

  if (tiltAngle <= UPRIGHT_ANGLE_DEGREES) {
    if (uprightCandidateSince == 0) {
      uprightCandidateSince = now;
    }
    if (now - uprightCandidateSince >= UPRIGHT_CONFIRM_MS) {
      leaveFallenState();
      fallCandidateSince = 0;
    }
  } else {
    uprightCandidateSince = 0;
  }
}

// =========================
// Mood Logic
// =========================

void nextMood() {
  currentMood = (Mood)((currentMood + 1) % 7);
  playMoodSound(currentMood);
}

// =========================
// Drawing
// =========================

void drawHeart(int x, int y) {
  display.fillCircle(x + 3, y + 3, 3, SSD1306_WHITE);
  display.fillCircle(x + 9, y + 3, 3, SSD1306_WHITE);
  display.fillTriangle(x, y + 4, x + 12, y + 4, x + 6, y + 13, SSD1306_WHITE);
}

void drawEyes(int eyeH, int pupilOffsetX, int pupilOffsetY) {
  int leftX = 18;
  int rightX = 74;
  int eyeY = 16;
  int eyeW = 36;

  display.fillRoundRect(leftX, eyeY, eyeW, eyeH, 8, SSD1306_WHITE);
  display.fillRoundRect(rightX, eyeY, eyeW, eyeH, 8, SSD1306_WHITE);

  if (eyeH > 8) {
    int pupilW = 14;
    int pupilH = max(4, eyeH / 2);

    display.fillRoundRect(
      leftX + 11 + pupilOffsetX,
      eyeY + eyeH / 2 - pupilH / 2 + pupilOffsetY,
      pupilW,
      pupilH,
      4,
      SSD1306_BLACK
    );

    display.fillRoundRect(
      rightX + 11 + pupilOffsetX,
      eyeY + eyeH / 2 - pupilH / 2 + pupilOffsetY,
      pupilW,
      pupilH,
      4,
      SSD1306_BLACK
    );
  }
}

void drawExpression() {
  display.clearDisplay();

  unsigned long now = millis();
  Mood moodToDraw = robotFallen ? fallenMood : currentMood;

  // 자동 깜빡임
  if (!blinking && now - lastBlinkTime > 3000) {
    blinking = true;
    blinkStart = now;
  }

  if (blinking && now - blinkStart > 120) {
    blinking = false;
    lastBlinkTime = now;
  }

  int eyeH = blinking ? 3 : 34;

  switch (moodToDraw) {
    case NORMAL:
      drawEyes(eyeH, 0, 0);
      break;

    case HAPPY:
      drawEyes(blinking ? 3 : 24, 0, 2);
      display.fillRect(18, 42, 92, 10, SSD1306_BLACK);
      break;

    case SLEEPY:
      drawEyes(blinking ? 2 : 12, 0, 0);
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(106, 4);
      display.print("Zz");
      break;

    case ANGRY:
      drawEyes(eyeH, 0, 0);
      display.drawLine(18, 14, 54, 24, SSD1306_BLACK);
      display.drawLine(74, 24, 110, 14, SSD1306_BLACK);
      display.drawLine(20, 10, 52, 20, SSD1306_WHITE);
      display.drawLine(76, 20, 108, 10, SSD1306_WHITE);
      break;

    case SAD:
      drawEyes(eyeH, 0, 2);
      display.drawLine(18, 18, 54, 10, SSD1306_BLACK);
      display.drawLine(74, 10, 110, 18, SSD1306_BLACK);
      display.fillCircle(105, 45, 2, SSD1306_WHITE);
      display.fillCircle(105, 51, 2, SSD1306_WHITE);
      break;

    case LOVE:
      drawEyes(eyeH, 0, 0);
      drawHeart(56, 2);
      break;

    case THINKING:
      drawEyes(eyeH, -5, 0);
      display.setTextSize(2);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(112, 4);
      display.print("?");
      break;
  }

  display.display();
}

// =========================
// Touch
// =========================

void handleTouch() {
  bool touchState = digitalRead(TOUCH_PIN);
  unsigned long now = millis();

  if (touchState && !lastTouchState) {
    touchPressedAt = now;
    longPressHandled = false;
  }

  if (touchState && !longPressHandled && touchPressedAt > 0 && now - touchPressedAt >= TOUCH_LONG_PRESS_MS) {
    longPressHandled = true;
    lastTouchTime = now;
    resetLocalPairingState("long press");
    if (WiFi.status() == WL_CONNECTED) {
      requestPairCode();
    }
  }

  if (!touchState && lastTouchState) {
    unsigned long pressedFor = touchPressedAt > 0 ? now - touchPressedAt : 0;
    if (!longPressHandled && pressedFor < TOUCH_LONG_PRESS_MS && now - lastTouchTime > debounceMs) {
      cycleTaskViewByTouch();
      lastTouchTime = now;
    }
    touchPressedAt = 0;
    longPressHandled = false;
  }

  if (touchState && !longPressHandled && touchPressedAt > 0 && now - touchPressedAt > 1500) {
    showStatus("Hold to reset", String((TOUCH_LONG_PRESS_MS - (now - touchPressedAt)) / 1000 + 1) + "s", deviceId);
  }

  lastTouchState = touchState;
}

// =========================
// Setup / Loop
// =========================

void setup() {
  Serial.begin(115200);
  delay(500);
  randomSeed((uint32_t)ESP.getEfuseMac() ^ micros());

  pinMode(TOUCH_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);

  if (!initOledDisplay()) {
    Serial.println("Boot halted because OLED is not ready.");
    while (true);
  }

  deviceId = buildDeviceId();
  displayTopic = String("devices/") + deviceId + "/display";
  setupApSsid = buildSetupApSsid();

  preferences.begin("heygent", false);
  if (RESET_PAIRING_ON_BOOT) {
    preferences.remove("paired");
  }
  paired = preferences.getBool("paired", false);
  loadWifiCredentials();

  Serial.println();
  Serial.print("deviceId: ");
  Serial.println(deviceId);
  Serial.print("paired: ");
  Serial.println(paired ? "true" : "false");
  Serial.print("wifi setup ap: ");
  Serial.println(setupApSsid);
  Serial.print("backend: ");
  Serial.println(BACKEND_BASE_URL);
  Serial.print("mqtt: ");
  Serial.print(MQTT_HOST);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  Serial.print("topic: ");
  Serial.println(displayTopic);

  showStatus("DeskMate", "power on", deviceId);
  delay(500);

  // 전원 인가 후 바로 한글 인트로 실행
  playIntro();

  imuReady = initMpu6050();
  if (imuReady) {
    imuReady = calibrateUprightPose();
  } else {
    showStatus("Gyro skipped", "MPU6050 not found", deviceId);
    delay(700);
  }

  if (paired) {
    showStatus("DeskMate", "service ready", deviceId);
    messageUntil = millis() + 1500;
  } else {
    showStatus("DeskMate", "pairing mode", deviceId);
    messageUntil = millis() + 1200;
  }

  beginWifiAttempt();
  lastBlinkTime = millis();
}

void loop() {
  maintainWifi();
  if (wifiSetupMode) {
    delay(10);
    return;
  }

  maintainMqtt();
  handleTouch();
  updateFallDetection();
  syncPairingStatusWithServer();

  if (!paired) {
    maintainPairing();
  }

  if (robotFallen) {
    messageUntil = 0;
  }

  if (messageUntil > 0 && !isDue(messageUntil)) {
    delay(30);
    return;
  }

  messageUntil = 0;

  if (!paired && currentPairCode.length() > 0) {
    maintainPairing();
    delay(30);
    return;
  }

  drawExpression();
  delay(30);
}
