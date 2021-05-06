#include <Arduino.h>
#include <nbUdp.h>
#include <coap-simple.h>

nbUDP U;
Coap coap(U);

void callback_response(CoapPacket &packet, IPAddress ip, int port) {
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  Serial.print(p);
}

//void send_cmd(char *CMD) {
//  s32 ret = 1;
//  ret = Ql_RIL_SendATCmd(CMD, strlen(CMD), callback, NULL, DEFAULT_AT_TIMEOUT);
//}
//
//s32 callback(char* line, u32 len, void* userdata)
//{
//  Serial.println(line);
//}

void setup()
{
  Dev.noSleep();
  Serial.begin(9600);
  Dev.waitSimReady();
  Serial.println("SIM ready");
  Dev.waitCereg();
  Serial.println("Net ready");
  delay(200);
  coap.response(callback_response);
  coap.start();
  Serial.println("ready");
}

void loop() {
  if (Serial.available()) {
    String msg = Serial.readString();
    coap.put(IPAddress(85, 246, 38, 211), 5683, "lys", msg.c_str());
    delay(2000);
  }
  coap.loop();
}
