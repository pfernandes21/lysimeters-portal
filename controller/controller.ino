#include <ArduinoJson.h>
#include <avr/sleep.h>
#include <DS3232RTC.h>
#include <SoftwareSerial.h>

SoftwareSerial bc66(12, 13);

#define ID 1

#define pressureSensorPin A0
#define humidityPin20 A1
#define humidityPin40 A2
#define humidityPin60 A3
#define valvePin20 8
#define valvePin40 7
#define valvePin60 5
#define motorPin 6
#define levelSensorPin20 3
#define levelSensorPin40 4
#define levelSensorPin60 9
#define sleepInterruptPin 2

#define numberOfSamples 25
#define airLevel20 760
#define waterLevel20 480
#define airLevel40 760
#define waterLevel40 480
#define airLevel60 760
#define waterLevel60 480
#define pressureUpperThreshold 45
#define pressureLowerThreshold 40
#define PRESSURIZE_TIMEOUT 10000
#define MSG_TIMEOUT 10000

int init_ack = false;
int msg_id = 0;
int humidityThreshold20 = 60;
int humidityThreshold40 = 60;
int humidityThreshold60 = 60;

char humidity20_msg[15];
char humidity40_msg[15];
char humidity60_msg[15];
char pressure_msg[15];
char msg[103];
bool pickupMsgSent = false;

enum lysState
{
  Normal = 0,
  Collecting = 1,
  Collected = 2,
  Broken = 3
};
enum lysState lysimeters[3] = {Normal, Normal, Normal};
enum lysState nextLysimeters[3] = {Normal, Normal, Normal};

long readVcc()
{
  // Read 1.1V reference against AVcc
  // set the reference to Vcc and the measurement to the internal 1.1V reference
#if defined(__AVR_ATmega32U4__) || defined(__AVR_ATmega1280__) || defined(__AVR_ATmega2560__)
  ADMUX = _BV(REFS0) | _BV(MUX4) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#elif defined(__AVR_ATtiny24__) || defined(__AVR_ATtiny44__) || defined(__AVR_ATtiny84__)
  ADMUX = _BV(MUX5) | _BV(MUX0);
#else
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#endif

  delay(2);            // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Start conversion
  while (bit_is_set(ADCSRA, ADSC))
    ; // measuring

  uint8_t low = ADCL;  // must read ADCL first - it then locks ADCH
  uint8_t high = ADCH; // unlocks both

  int result = (high << 8) | low;

  result = 11253L / result; // Calculate Vcc (in dV); 1125300 = 1.1*1023*10
  return result;            // Vcc in decivolts
}

void hibernate(time_t wake_time)
{
  Serial.println("Sleep until Day: " + String(day(wake_time)) + ", Time: " + String(hour(wake_time)) + ":" + String(minute(wake_time)) + ":" + String(second(wake_time)));
  RTC.setAlarm(ALM1_MATCH_DATE, second(wake_time), minute(wake_time), hour(wake_time), day(wake_time));
  RTC.alarm(ALARM_1);
  sleep_enable();
  attachInterrupt(digitalPinToInterrupt(sleepInterruptPin), wakeUp, LOW);
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);

  time_t t;
  t = RTC.get();
  Serial.println("Sleep  Time: " + String(hour(t)) + ":" + String(minute(t)) + ":" + String(second(t)));
  delay(1000);
  sleep_cpu();
  t = RTC.get();
  Serial.println("WakeUp Time: " + String(hour(t)) + ":" + String(minute(t)) + ":" + String(second(t)));
}

void wakeUp()
{
  sleep_disable();
  detachInterrupt(digitalPinToInterrupt(sleepInterruptPin));
}

float getHumidity(int pin)
{
  float humidity = 0.0;

  for (int i = 0; i < numberOfSamples; i++)
  {
    humidity += analogRead(pin);
  }

  if (humidityPin20 == pin) {
    return map(humidity / numberOfSamples, airLevel20, waterLevel20, 0, 100);
  }
  else if (humidityPin40 == pin) {
    return map(humidity / numberOfSamples, airLevel40, waterLevel40, 0, 100);
  }
  else if (humidityPin60 == pin) {
    return map(humidity / numberOfSamples, airLevel60, waterLevel60, 0, 100);
  }

  return map(humidity / numberOfSamples, airLevel20, waterLevel20, 0, 100);
}

void getLysimeters()
{
  if (lysimeters[0] == Normal && getHumidity(humidityPin20) > humidityThreshold20)
  {
    Serial.println("20cm collecting");
    nextLysimeters[0] = Collecting;
    if (!pressurizeValve(valvePin20)) {
      nextLysimeters[0] = Broken;
    }
  }
  else if (lysimeters[1] == Normal && getHumidity(humidityPin40) > humidityThreshold40)
  {
    Serial.println("40cm collecting");
    nextLysimeters[1] = Collecting;
    if (!pressurizeValve(valvePin40)) {
      nextLysimeters[1] = Broken;
    }
  }
  else if (lysimeters[2] == Normal && getHumidity(humidityPin60) > humidityThreshold60)
  {
    Serial.println("60cm collecting");
    nextLysimeters[2] = Collecting;
    if (!pressurizeValve(valvePin60)) {
      nextLysimeters[2] = Broken;
    }
  }
  else if (lysimeters[0] == Collecting && !digitalRead(levelSensorPin20))
  {
    Serial.println("20cm collected");
    nextLysimeters[0] = Collected;
  }
  else if (lysimeters[1] == Collecting && !digitalRead(levelSensorPin40))
  {
    Serial.println("40cm collected");
    nextLysimeters[1] = Collected;
  }
  else if (lysimeters[2] == Collecting && !digitalRead(levelSensorPin60))
  {
    Serial.println("60cm collected");
    nextLysimeters[2] = Collected;
  }
}

float getPressure()
{
  return (analogRead(pressureSensorPin) - 25.658) / 3.4799;
}

bool pressurize()
{
  int t = millis();
  int w = t;
  digitalWrite(motorPin, HIGH);
  while (getPressure() < pressureUpperThreshold && w < (t + PRESSURIZE_TIMEOUT))
  {
    w = millis();
  }
  digitalWrite(motorPin, LOW);

  if (w >= (t + PRESSURIZE_TIMEOUT))
  {
    Serial.println("Error pressurizing");
    return false;
  }
  else
  {
    return true;
  }
}

bool pressurizeValve(int valvePin)
{
  Serial.print("Pressurizing valve ");
  Serial.println(valvePin);

  digitalWrite(valvePin, HIGH);
  bool result = pressurize();
  digitalWrite(valvePin, LOW);

  return result;
}

void unpressurizeValve(int valvePin) {
  Serial.print("Unpressurizing valve ");
  Serial.println(valvePin);
  digitalWrite(valvePin, HIGH);
  delay(2000);
  digitalWrite(valvePin, LOW);
}

void recv_msg(char const *warning, int attempt, char * msg) {
  Serial.print("Receiving: ");
  Serial.println(msg);
  StaticJsonDocument<200> resp;
  DeserializationError error = deserializeJson(resp, msg);
  if (error)
    return;

  const char *status = resp["status"];
  if (!strcmp(status, "ok"))
  {
    init_ack = true;
    time_t wake_time = resp["wake"];
    if (wake_time > (RTC.get() + 3600) && wake_time < (RTC.get() + 259200) && lysimeters[0] == Normal && lysimeters[1] == Normal && lysimeters[2] == Normal)
    {
      hibernate(wake_time);
    }
    else if (wake_time > (RTC.get() + 259200) && lysimeters[0] == Normal && lysimeters[1] == Normal && lysimeters[2] == Normal)
    {
      hibernate(RTC.get() + 259200);
    }
  }
  else if (!strcmp(status, "pickup"))
  {
    pickupMsgSent = true;
  }
  else if (!strcmp(status, "config20"))
  {
    int level = resp["level"];
    humidityThreshold20 = level;
    send_msg(",\"config20\":\"ok\"", 0);
  }
  else if (!strcmp(status, "config40"))
  {
    int level = resp["level"];
    humidityThreshold40 = level;
    send_msg(",\"config40\":\"ok\"", 0);
  }
  else if (!strcmp(status, "config60"))
  {
    int level = resp["level"];
    humidityThreshold60 = level;
    send_msg(",\"config60\":\"ok\"", 0);
  }
  else if (!strcmp(status, "error"))
  {
    send_msg(warning, attempt + 1);
  }
}

bool send_msg(char const *warning, int attempt)
{
  char * pch;
  const char * r_msg_c;
  String r_msg;

  if (attempt < 3)
  {
    dtostrf(getHumidity(humidityPin20), 4, 3, humidity20_msg);
    dtostrf(getHumidity(humidityPin40), 4, 3, humidity40_msg);
    dtostrf(getHumidity(humidityPin60), 4, 3, humidity60_msg);
    dtostrf(getPressure(), 4, 3, pressure_msg);
    sprintf(msg, "{\"id\":%d,\"msg\":%d,\"h20\":%s,\"h40\":%s,\"h60\":%s,\"p\":%s%s}", ID, msg_id, humidity20_msg, humidity40_msg, humidity60_msg, pressure_msg, warning);
    bc66.println(msg);
    msg_id++;
    Serial.print("Sending: ");
    Serial.println(msg);
  }
  else
  {
    return true;
  }

  long t = millis();
  while (!bc66.available() && millis() < (t + MSG_TIMEOUT))
  {
  }
  if (bc66.available() > 0)
  {
    r_msg = bc66.readString();
    r_msg_c = r_msg.c_str();
    pch = strtok (r_msg_c, "\n");
    while (pch != NULL)
    {
      recv_msg(warning, attempt, pch);
      pch = strtok (NULL, "\n");
    }
    return true;
  }
  return false;
}

void setup()
{
  Serial.begin(9600);
  bc66.begin(9600);

  pinMode(motorPin, OUTPUT);
  pinMode(valvePin20, OUTPUT);
  pinMode(valvePin40, OUTPUT);
  pinMode(valvePin60, OUTPUT);
  pinMode(levelSensorPin20, INPUT_PULLUP);
  pinMode(levelSensorPin40, INPUT_PULLUP);
  pinMode(levelSensorPin60, INPUT_PULLUP);
  pinMode(sleepInterruptPin, INPUT_PULLUP);

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

  bc66.flush();
  //  while (!init_ack) {
  //    if (!send_msg(",\"init\":\"true\"", 0)) {
  //      while (!bc66.available())
  //      {}
  //      if (bc66.available() > 0)
  //      {
  //        String r_msg = bc66.readString();
  //        const char * m = r_msg.c_str();
  //        char * pch = strtok (m, "\n");
  //        while (pch != NULL)
  //        {
  //          recv_msg("", 0, pch);
  //          pch = strtok (NULL, "\n");
  //        }
  //      }
  //    }
  //  }
}

void loop()
{
  getLysimeters();

  //waiting for pickup
  if ((lysimeters[0] == Collected || lysimeters[0] == Broken) && (lysimeters[1] == Collected || lysimeters[1] == Broken) && (lysimeters[2] == Collected || lysimeters[2] == Broken))
  {
    //if pickup not confirmed send warning
    if (!pickupMsgSent)
    {
      if (lysimeters[0] == Collected) {
        send_msg(",\"l20\":\"end\"", 0);
      }
      else {
        send_msg(",\"l20\":\"error\"", 0);
      }
      delay(10000);

      if (lysimeters[1] == Collected) {
        send_msg(",\"l40\":\"end\"", 0);
      }
      else {
        send_msg(",\"l40\":\"error\"", 0);
      }
      delay(10000);

      if (lysimeters[2] == Collected) {
        send_msg(",\"l60\":\"end\"", 0);
      }
      else {
        send_msg(",\"l60\":\"error\"", 0);
      }
      delay(10000);

      hibernate(RTC.get() + 5 * 60);
    }
    //sleep indefinitely
    else
    {
      Serial.println("Hibernating indefinatly");
      hibernate(RTC.get() + 7 * 24 * 60 * 60);
    }
  }
  //lysimeter 0 (20cm) changed
  else if (nextLysimeters[0] != lysimeters[0])
  {
    //if start collecting send warning + data
    if (lysimeters[0] == Normal && nextLysimeters[0] == Collecting)
    {
      send_msg(",\"l20\":\"start\"", 0);
    }
    //else if end collecting send warning + data, unpressurize
    else if (lysimeters[0] == Collecting && nextLysimeters[0] == Collected)
    {
      send_msg(",\"l20\":\"end\"", 0);
      unpressurizeValve(valvePin20);
    }
    //if pipe broken send warning
    else if (nextLysimeters[0] == Broken)
    {
      send_msg(",\"l20\":\"error\"", 0);
    }

    lysimeters[0] = nextLysimeters[0];
  }
  //lysimeter 1 (40cm) changed
  else if (nextLysimeters[1] != lysimeters[1])
  {
    //if start collecting send warning + data
    if (lysimeters[1] == Normal && nextLysimeters[1] == Collecting)
    {
      send_msg(",\"l40\":\"start\"", 0);
    }
    //else if end collecting send warning + data, unpressurize
    else if (lysimeters[1] == Collecting && nextLysimeters[1] == Collected)
    {
      send_msg(",\"l40\":\"end\"", 0);
      unpressurizeValve(valvePin40);
    }
    //if pipe broken send warning
    else if (nextLysimeters[1] == Broken)
    {
      send_msg(",\"l40\":\"error\"", 0);
    }

    lysimeters[1] = nextLysimeters[1];
  }
  //lysimeter 2 (60cm) changed
  else if (nextLysimeters[2] != lysimeters[2])
  {
    //if start collecting send warning + data
    if (lysimeters[2] == Normal && nextLysimeters[2] == Collecting)
    {
      send_msg(",\"l60\":\"start\"", 0);
    }
    //else if end collecting send warning + data, unpressurize
    else if (lysimeters[2] == Collecting && nextLysimeters[2] == Collected)
    {
      send_msg(",\"l60\":\"end\"", 0);
      unpressurizeValve(valvePin60);
    }
    //if pipe broken send warning
    else if (nextLysimeters[2] == Broken)
    {
      send_msg(",\"l60\":\"error\"", 0);
    }

    lysimeters[2] = nextLysimeters[2];
  }
  else
  {
    //if all normal send data
    if (lysimeters[0] == Normal || lysimeters[1] == Normal || lysimeters[2] == Normal)
    {
      send_msg("", 0);
    }
  }

  //if one or more collecting pressurize
  if (lysimeters[0] == Collecting)
  {
    pressurizeValve(valvePin20);
  }
  if (lysimeters[1] == Collecting)
  {
    pressurizeValve(valvePin40);
  }
  if (lysimeters[2] == Collecting)
  {
    pressurizeValve(valvePin60);
  }

  //if battery low
  //  if (!pickupMsgSent && readVcc() < 50)
  //  {
  //    send_msg(",\"b\":\"low\"", 0);
  //  }

  delay(5000);
}