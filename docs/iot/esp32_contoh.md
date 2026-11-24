# Contoh awal ESP32 (belum diuji pada perangkat keras)

**Peringatan:** kode berikut hanya contoh integrasi HTTP. Belum diuji pada
perangkat keras, sensor fisik, kalibrasi, atau instalasi jaringan. Nilai
konversi ADC adalah placeholder; sesuaikan dengan rangkaian dan kalibrasi sensor
yang benar. Jangan gunakan ambang contoh AquaTrace sebagai kalibrasi sensor.

Contoh membutuhkan pustaka Arduino `WiFi.h` dan `HTTPClient.h`. Isi kredensial
Wi-Fi dan API key secara lokal; jangan unggah rahasia ke repositori.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "GANTI_DI_LOKAL";
const char* WIFI_PASSWORD = "GANTI_DI_LOKAL";
const char* API_URL = "https://HOST_AQUATRACE/api/iot/ingest";
const char* API_KEY = "GANTI_DENGAN_KEY_PERANGKAT";
const char* DEVICE_CODE = "SENSOR-ESP32-01";

float readPhPlaceholder() {
  // TODO: baca modul pH terkalibrasi; ini hanya nilai simulasi awal.
  return 7.2f;
}

float readTurbidityPlaceholder() {
  // TODO: konversi ADC memakai kurva sensor dan kalibrasi lokal.
  return 1.8f;
}

float readTdsPlaceholder() {
  // TODO: kompensasi suhu dan kalibrasi probe TDS.
  return 145.0f;
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(API_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);

    String body = "{\"kode\":\"" + String(DEVICE_CODE) +
      "\",\"ph\":" + String(readPhPlaceholder(), 2) +
      ",\"kekeruhan_ntu\":" + String(readTurbidityPlaceholder(), 2) +
      ",\"tds_mgl\":" + String(readTdsPlaceholder(), 2) + "}";
    int status = http.POST(body);
    Serial.printf("AquaTrace HTTP status: %d\n", status);
    if (status > 0) {
      Serial.println(http.getString());
    }
    http.end();
  }
  delay(2000);
}
```

Perangkat nyata harus diuji dan dikalibrasi oleh kelompok sebelum dipakai.
