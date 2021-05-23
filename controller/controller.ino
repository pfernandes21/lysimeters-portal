#include <ArduinoJson.h>
#include <avr/sleep.h>
#include <DS3232RTC.h>
#include <SoftwareSerial.h>

SoftwareSerial mySerial(13, 12);

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
#define airLevel 750
#define waterLevel 500
#define pressureUpperThreshold 45
#define pressureLowerThreshold 40

int humidityThreshold = 60;

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
  RTC.setAlarm(ALM1_MATCH_DATE, second(wake_time), minute(wake_time), hour(wake_time), day(wake_time));
  RTC.alarm(ALARM_1);
  sleep_enable();
  attachInterrupt(digitalPinToInterrupt(sleepInterruptPin), wakeUp, LOW);
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  delay(1000);
  sleep_cpu();
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

  return map(humidity / numberOfSamples, airLevel, waterLevel, 0, 100);
}

void getLysimeters()
{
  if (lysimeters[0] == Normal && getHumidity(humidityPin20) > humidityThreshold)
  {
    nextLysimeters[0] = Collecting;
    pressurizeValve(valvePin20);
  }
  else if (lysimeters[1] == Normal && getHumidity(humidityPin40) > humidityThreshold)
  {
    nextLysimeters[1] = Collecting;
    pressurizeValve(valvePin40);
  }
  else if (lysimeters[2] == Normal && getHumidity(humidityPin60) > humidityThreshold)
  {
    nextLysimeters[2] = Collecting;
    pressurizeValve(valvePin60);
  }
  else if (lysimeters[0] == Collecting && digitalRead(levelSensorPin20))
  {
    nextLysimeters[0] = Collected;
  }
  else if (lysimeters[1] == Collecting && digitalRead(levelSensorPin40))
  {
    nextLysimeters[1] = Collected;
  }
  else if (lysimeters[2] == Collecting && digitalRead(levelSensorPin60))
  {
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
  digitalWrite(motorPin, HIGH);
  while (getPressure() < pressureUpperThreshold && millis() < (t + 10000))
  {
  }
  digitalWrite(motorPin, LOW);

  if (millis() > (t + 10000))
  {
    return false;
  }
  else
  {
    return true;
  }
}

void pressurizeValve(int valvePin)
{
  int lysimeterIndex = getLysimeterIndexFromValvePin(valvePin);
  if (lysimeters[lysimeterIndex] == Broken)
  {
    return;
  }

  digitalWrite(valvePin, HIGH);
  if (!pressurize())
  {
    lysimeters[lysimeterIndex] = Broken;
    digitalWrite(valvePin, LOW);
    if(lysimeterIndex == 0) {
     send_msg(",\"l20\":\"error\"", 0); 
    }
    else if(lysimeterIndex == 0) {
     send_msg(",\"l40\":\"error\"", 0); 
    }
    else if(lysimeterIndex == 0) {
     send_msg(",\"l60\":\"error\"", 0); 
    }
  }
  else {
    digitalWrite(valvePin, LOW);
  }
}

void unpressurizeValve(int valvePin) {
  digitalWrite(valvePin, HIGH);
  delay(2000);
  digitalWrite(valvePin, LOW);
}

int getLysimeterIndexFromValvePin(int valvePin)
{
  switch (valvePin)
  {
    case valvePin20:
      return 0;
    case valvePin40:
      return 1;
    case valvePin60:
      return 2;
    default:
      return 0;
  }
}

void send_msg(char const *warning, int attempt)
{
  if (attempt < 3)
  {
    dtostrf(getHumidity(humidityPin20), 4, 3, humidity20_msg);
    dtostrf(getHumidity(humidityPin40), 4, 3, humidity40_msg);
    dtostrf(getHumidity(humidityPin60), 4, 3, humidity60_msg);
    dtostrf(getPressure(), 4, 3, pressure_msg);
    sprintf(msg, "{\"id\":%d,\"h20\":%s,\"h40\":%s,\"h60\":%s,\"p\":%s%s}", ID, humidity20_msg, humidity40_msg, humidity60_msg, pressure_msg, warning);
    mySerial.flush();
    mySerial.println(msg);
  }
  else
  {
    return;
  }

  long t = millis();
  while (!Serial.available() && millis() < (t + 10*1000))
  {
  }
  if (Serial.available())
  {
    StaticJsonDocument<200> resp;
    DeserializationError error = deserializeJson(resp, Serial.readString().c_str());
    if (error)
      return;

    const char *status = resp["status"];
    if (!strcmp(status, "ok"))
    {
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
    else if (!strcmp(status, "config"))
    {
      int level = resp["level"];
      humidityThreshold = level;
      send_msg(", \"config\":\"ok\"", 0);
    }
    else if (!strcmp(status, "error"))
    {
      send_msg(warning, attempt + 1);
    }
  }
  else
  {
    send_msg(warning, attempt + 1);
  }
}

void setup()
{
  Serial.begin(9600);

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

  send_msg(",\"init\":\"true\"", 0);
}

void loop()
{
  getLysimeters();

  //waiting for pickup
  if (lysimeters[0] == Collected && lysimeters[1] == Collected && lysimeters[2] == Collected)
  {
    //if pickup not confirmed send warning
    if (!pickupMsgSent)
    {
      send_msg(",\"l20\":\"end\"", 0);
      send_msg(",\"l40\":\"end\"", 0);
      send_msg(",\"l60\":\"end\"", 0);
      delay(10000);
    }
    //sleep indefinitely
    else
    {
      hibernate(RTC.get() + 7 * 24 * 60 * 60);
    }
  }
  else if (lysimeters[0] == Broken && lysimeters[1] == Broken && lysimeters[2] == Broken)
  {
    //if pickup not confirmed send warning
    if (!pickupMsgSent)
    {
      send_msg(",\"l20\":\"error\"", 0);
      send_msg(",\"l40\":\"error\"", 0);
      send_msg(",\"l60\":\"error\"", 0);
      delay(10000);
    }
    //sleep indefinitely
    else
    {
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
  if (!pickupMsgSent && readVcc() < 50)
  {
    send_msg(",\"b\":\"low\"", 0);
  }

  delay(5000);
}