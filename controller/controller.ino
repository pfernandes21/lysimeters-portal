#include <ArduinoJson.h>
#include <avr/sleep.h>
#include <DS3232RTC.h>

#define ID 1
#define pressureSensorPin A0
#define humidityPin20 A1
#define humidityPin40 A2
#define humidityPin60 A3
#define valvePin20 9
#define valvePin40 8
#define valvePin60 7
#define motorPin 6
#define levelSensorPin20 5
#define levelSensorPin40 4
#define levelSensorPin60 3
#define sleepInterruptPin 2
#define numberOfSamples 25
#define humidityThreshold 60
#define airLevel 760
#define waterLevel 450
#define pressureUpperThreshold 45
#define pressureLowerThreshold 40

char humidity20_msg[15];
char humidity40_msg[15];
char humidity60_msg[15];
char pressure_msg[15];
char msg[103];
bool pickupMsgSent = false;
enum lysState {Normal = 0, Collecting = 1, Collected = 2};
enum lysState lysimeters[3] = {Normal, Normal, Normal};
enum lysState nextLysimeters[3] = {Normal, Normal, Normal};

char hex[256];
uint8_t data[256];
int start = 0;
uint8_t hash[32];
String pin;
#define SHA256_BLOCK_SIZE 32

typedef struct {
  uint8_t data[64];
  uint32_t datalen;
  unsigned long long bitlen;
  uint32_t state[8];
} SHA256_CTX;

void sha256_init(SHA256_CTX *ctx);
void sha256_update(SHA256_CTX *ctx, const uint8_t data[], size_t len);
void sha256_final(SHA256_CTX *ctx, uint8_t hash[]);

#define ROTLEFT(a,b) (((a) << (b)) | ((a) >> (32-(b))))
#define ROTRIGHT(a,b) (((a) >> (b)) | ((a) << (32-(b))))

#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTRIGHT(x,2) ^ ROTRIGHT(x,13) ^ ROTRIGHT(x,22))
#define EP1(x) (ROTRIGHT(x,6) ^ ROTRIGHT(x,11) ^ ROTRIGHT(x,25))
#define SIG0(x) (ROTRIGHT(x,7) ^ ROTRIGHT(x,18) ^ ((x) >> 3))
#define SIG1(x) (ROTRIGHT(x,17) ^ ROTRIGHT(x,19) ^ ((x) >> 10))

static const uint32_t k[64] = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

void sha256_transform(SHA256_CTX *ctx, const uint8_t data[]) {
  uint32_t a, b, c, d, e, f, g, h, i, j, t1, t2, m[64];

  for (i = 0, j = 0; i < 16; ++i, j += 4)
    m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j + 1] << 16) | ((uint32_t)data[j + 2] << 8) | ((uint32_t)data[j + 3]);
  for ( ; i < 64; ++i)
    m[i] = SIG1(m[i - 2]) + m[i - 7] + SIG0(m[i - 15]) + m[i - 16];

  a = ctx->state[0];
  b = ctx->state[1];
  c = ctx->state[2];
  d = ctx->state[3];
  e = ctx->state[4];
  f = ctx->state[5];
  g = ctx->state[6];
  h = ctx->state[7];

  for (i = 0; i < 64; ++i) {
    t1 = h + EP1(e) + CH(e, f, g) + k[i] + m[i];
    t2 = EP0(a) + MAJ(a, b, c);
    h = g;
    g = f;
    f = e;
    e = d + t1;
    d = c;
    c = b;
    b = a;
    a = t1 + t2;
  }

  ctx->state[0] += a;
  ctx->state[1] += b;
  ctx->state[2] += c;
  ctx->state[3] += d;
  ctx->state[4] += e;
  ctx->state[5] += f;
  ctx->state[6] += g;
  ctx->state[7] += h;
}

void sha256_init(SHA256_CTX *ctx)
{
  ctx->datalen = 0;
  ctx->bitlen = 0;
  ctx->state[0] = 0x6a09e667;
  ctx->state[1] = 0xbb67ae85;
  ctx->state[2] = 0x3c6ef372;
  ctx->state[3] = 0xa54ff53a;
  ctx->state[4] = 0x510e527f;
  ctx->state[5] = 0x9b05688c;
  ctx->state[6] = 0x1f83d9ab;
  ctx->state[7] = 0x5be0cd19;
}

void sha256_update(SHA256_CTX *ctx, const uint8_t data[], size_t len) {
  uint32_t i;

  for (i = 0; i < len; ++i) {
    ctx->data[ctx->datalen] = data[i];
    ctx->datalen++;
    if (ctx->datalen == 64) {
      sha256_transform(ctx, ctx->data);
      ctx->bitlen += 512;
      ctx->datalen = 0;
    }
  }
}

void sha256_final(SHA256_CTX *ctx, uint8_t hash[]) {
  uint32_t i;

  i = ctx->datalen;

  // Pad whatever data is left in the buffer.
  if (ctx->datalen < 56) {
    ctx->data[i++] = 0x80;
    while (i < 56)
      ctx->data[i++] = 0x00;
  }
  else {
    ctx->data[i++] = 0x80;
    while (i < 64)
      ctx->data[i++] = 0x00;
    sha256_transform(ctx, ctx->data);
    memset(ctx->data, 0, 56);
  }

  // Append to the padding the total message's length in bits and transform.
  ctx->bitlen += ctx->datalen * 8;
  ctx->data[63] = ctx->bitlen;
  ctx->data[62] = ctx->bitlen >> 8;
  ctx->data[61] = ctx->bitlen >> 16;
  ctx->data[60] = ctx->bitlen >> 24;
  ctx->data[59] = ctx->bitlen >> 32;
  ctx->data[58] = ctx->bitlen >> 40;
  ctx->data[57] = ctx->bitlen >> 48;
  ctx->data[56] = ctx->bitlen >> 56;
  sha256_transform(ctx, ctx->data);

  // Since this implementation uses little endian byte ordering and SHA uses big endian,
  // reverse all the bytes when copying the final state to the output hash.
  for (i = 0; i < 4; ++i) {
    hash[i]      = (ctx->state[0] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 4]  = (ctx->state[1] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 8]  = (ctx->state[2] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 12] = (ctx->state[3] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 16] = (ctx->state[4] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 20] = (ctx->state[5] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 24] = (ctx->state[6] >> (24 - i * 8)) & 0x000000ff;
    hash[i + 28] = (ctx->state[7] >> (24 - i * 8)) & 0x000000ff;
  }
}

char *btoh(char *dest, uint8_t *src, int len) {
  char *d = dest;
  while ( len-- ) sprintf(d, "%02x", (unsigned char)*src++), d += 2;
  return dest;
}

String SHA256(String data)
{
  uint8_t data_buffer[data.length()];

  for (int i = 0; i < data.length(); i++)
  {
    data_buffer[i] = (uint8_t)data.charAt(i);
  }

  SHA256_CTX ctx;
  ctx.datalen = 0;
  ctx.bitlen = 512;

  sha256_init(&ctx);
  sha256_update(&ctx, data_buffer, data.length());
  sha256_final(&ctx, hash);
  return (btoh(hex, hash, 32));
}

long readVcc() {
  // Read 1.1V reference against AVcc
  // set the reference to Vcc and the measurement to the internal 1.1V reference
#if defined(__AVR_ATmega32U4__) || defined(__AVR_ATmega1280__) || defined(__AVR_ATmega2560__)
  ADMUX = _BV(REFS0) | _BV(MUX4) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#elif defined (__AVR_ATtiny24__) || defined(__AVR_ATtiny44__) || defined(__AVR_ATtiny84__)
  ADMUX = _BV(MUX5) | _BV(MUX0) ;
#else
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#endif

  delay(2); // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Start conversion
  while (bit_is_set(ADCSRA, ADSC)); // measuring

  uint8_t low  = ADCL; // must read ADCL first - it then locks ADCH
  uint8_t high = ADCH; // unlocks both

  int result = (high << 8) | low;

  result = 11253L / result; // Calculate Vcc (in dV); 1125300 = 1.1*1023*10
  return result; // Vcc in decivolts
}

void hibernate(time_t wake_time) {
  RTC.setAlarm(ALM1_MATCH_DATE , second(wake_time), minute(wake_time), hour(wake_time), day(wake_time));
  RTC.alarm(ALARM_1);
  sleep_enable();
  attachInterrupt(digitalPinToInterrupt(sleepInterruptPin), wakeUp, LOW);
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  delay(1000);
  sleep_cpu();
}

void wakeUp() {
  sleep_disable();
  detachInterrupt(digitalPinToInterrupt(sleepInterruptPin));
}

float getHumidity(int pin) {
  float humidity = 0.0;

  for (int i = 0; i < numberOfSamples; i++)
  {
    humidity += analogRead(pin);
  }

  return map(humidity / numberOfSamples, airLevel, waterLevel, 0, 100);
}

void getLysimeters() {
  if (lysimeters[0] == Normal && getHumidity(humidityPin20) > humidityThreshold) {
    nextLysimeters[0] = Collecting;
    pressurizeValve(valvePin20);
  }
  else if (lysimeters[1] == Normal && getHumidity(humidityPin40) > humidityThreshold) {
    nextLysimeters[1] = Collecting;
    pressurizeValve(valvePin40);
  }
  else if (lysimeters[2] == Normal && getHumidity(humidityPin60) > humidityThreshold) {
    nextLysimeters[2] = Collecting;
    pressurizeValve(valvePin60);
  }
  else if (lysimeters[0] == Collecting && digitalRead(levelSensorPin20)) {
    nextLysimeters[0] = Collected;
  }
  else if (lysimeters[1] == Collecting && digitalRead(levelSensorPin40)) {
    nextLysimeters[1] = Collected;
  }
  else if (lysimeters[2] == Collecting && digitalRead(levelSensorPin60)) {
    nextLysimeters[2] = Collected;
  }
}

float getPressure()
{
  return (analogRead(pressureSensorPin) - 25.658) / 3.4799;
}

void pressurize()
{
  digitalWrite(motorPin, HIGH);
  while (getPressure() < pressureUpperThreshold)
  {
  }
  digitalWrite(motorPin, LOW);
}

void pressurizeValve(int valvePin) {
  digitalWrite(valvePin, HIGH);
  pressurize();
  digitalWrite(valvePin, LOW);
}

void send_msg(char const *warning, int attempt) {
  dtostrf(getHumidity(humidityPin20), 4, 3, humidity20_msg);
  dtostrf(getHumidity(humidityPin40), 4, 3, humidity40_msg);
  dtostrf(getHumidity(humidityPin60), 4, 3, humidity60_msg);
  dtostrf(getPressure(), 4, 3, pressure_msg);
  sprintf(msg, "{\"id\":%d,\"h20\":%s,\"h40\":%s,\"h60\":%s,\"p\":%s,\"t\":%s%s}", ID, humidity20_msg, humidity40_msg, humidity60_msg, pressure_msg, SHA256(String(RTC.get()) + "lisimetros").c_str(), warning);
  Serial.println(msg);

  time_t t = RTC.get();
  while (!Serial.available() && RTC.get() > (t + 10)) {}
  if (Serial.available()) {
    StaticJsonDocument<200> resp;
    DeserializationError error = deserializeJson(resp, Serial.readString().c_str());
    if (error) return;

    const char* status = resp["status"];
    if (!strcmp(status, "ok")) {
      time_t wake_time = resp["wake"];
      if (wake_time > (RTC.get() + 3600) && wake_time < (RTC.get() + 10800)) {
        hibernate(wake_time);
      }
    }
    else if (!strcmp(status, "pickup")) {
      pickupMsgSent = true;
    }
    else if (!strcmp(status, "error") && attempt < 3) {
      send_msg(warning, attempt + 1);
    }
  }
}

void setup() {
  pinMode(motorPin, OUTPUT);
  pinMode(valvePin20, OUTPUT);
  pinMode(valvePin40, OUTPUT);
  pinMode(valvePin60, OUTPUT);
  pinMode(levelSensorPin20, INPUT);
  pinMode(levelSensorPin40, INPUT);
  pinMode(levelSensorPin60, INPUT);

  RTC.setAlarm(ALM1_MATCH_DATE, 0, 0, 0, 1);
  RTC.setAlarm(ALM2_MATCH_DATE, 0, 0, 0, 1);
  RTC.alarm(ALARM_1);
  RTC.alarm(ALARM_2);
  RTC.alarmInterrupt(ALARM_1, false);
  RTC.alarmInterrupt(ALARM_2, false);
  RTC.squareWave(SQWAVE_NONE);
  RTC.alarm(ALARM_1);
  RTC.squareWave(SQWAVE_NONE);
  RTC.alarmInterrupt(ALARM_1, true);

  Serial.begin(115200);
  send_msg(", \"init\":\"true\"", 0);
}

void loop() {
  getLysimeters();

  //waiting for collection
  if (lysimeters[0] == Collected && lysimeters[1] == Collected && lysimeters[2] == Collected) {
    if (!pickupMsgSent) {
      //send pickup msg
      delay(10000);
    }
    else {
      while (true) {};
    }
  }
  else if (nextLysimeters[0] != lysimeters[0]) {
    //if start collecting send warning + data, pressurize, open valve
    if (lysimeters[0] == Normal && nextLysimeters[0] == Collecting) {
      send_msg(", \"l20\":\"start\"", 0);
    }
    //else if end collecting send warning + data
    else if (lysimeters[0] == Collecting && nextLysimeters[0] == Collected) {
      send_msg(", \"l20\":\"end\"", 0);
    }

    lysimeters[0] = nextLysimeters[0];
  }
  else if (nextLysimeters[1] != lysimeters[1]) {
    //if start collecting send warning + data, pressurize, open valve
    if (lysimeters[1] == Normal && nextLysimeters[1] == Collecting) {
      send_msg(", \"l40\":\"start\"", 0);
    }
    //else if end collecting send warning + data, close valve
    else if (lysimeters[1] == Collecting && nextLysimeters[1] == Collected) {
      send_msg(", \"l40\":\"end\"", 0);
    }

    lysimeters[1] = nextLysimeters[1];
  }
  else if (nextLysimeters[2] != lysimeters[2]) {
    //if start collecting send warning + data, pressurize, open valve
    if (lysimeters[2] == Normal && nextLysimeters[2] == Collecting) {
      send_msg(", \"l60\":\"start\"", 0);
    }
    //else if end collecting send warning + data, close valve
    else if (lysimeters[2] == Collecting && nextLysimeters[2] == Collected) {
      send_msg(", \"l60\":\"end\"", 0);
    }

    lysimeters[2] = nextLysimeters[2];
  }
  else {
    //if all normal send data
    if (lysimeters[0] == Normal || lysimeters[1] == Normal || lysimeters[2] == Normal) {
      send_msg("", 0);
    }
  }

  //  //if one or more collecting pressurize
  //  if (lysimeters[0] == Collecting) {
  //    pressurizeValve(valvePin20);
  //  }
  //  if (lysimeters[1] == Collecting) {
  //    pressurizeValve(valvePin40);
  //  }
  //  if (lysimeters[2] == Collecting) {
  //    pressurizeValve(valvePin60);
  //  }

  //if battery low
  if (readVcc() < 50) {
    send_msg(", \"b\":\"low\"", 0);
  }

  delay(5000);
}
