#include <Arduino.h>
#include <nbUdp.h>
#include <coap-simple.h>

nbUDP U;
Coap coap(U);
String msg = "";
bool msg_sent = false;

void callback_response(CoapPacket &packet, IPAddress ip, int port) {
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  if(!msg_sent && strcmp(p,"{\"status\": \"ack\"}") != 0) {
   Serial.print(p);
   msg_sent = true;
  }
  msg = "";
}

void setup()
{
  int t = millis();
  String imei, mcc_mnc, sim_imsi, sim_iccid, uid;
  Dev.noSleep();

  Serial.begin(9600);

  Serial.printf("Arduino      %s\n", Dev.getVersion());
  Dev.getImei(imei);
  Serial.printf("IMEI         %s\n", imei.c_str());
  Dev.getUid(uid);
  Serial.printf("UID          %s\n", uid.c_str());

  Dev.waitSimReady();

  Dev.getMccMnc(mcc_mnc);
  Serial.printf("MCCMNC       %s\n", mcc_mnc.c_str());
  Dev.getImsi(sim_imsi);
  Serial.printf("IMSI         %s\n", sim_imsi.c_str());
  Dev.getIccid(sim_iccid);
  Serial.printf("ICCID        %s\n", sim_iccid.c_str());

  Dev.waitCereg();
  delay(200);

  Serial.printf("Rx level     %d dbm\n", Dev.getReceiveLevel());
  Serial.printf("Rx quality   %d\n", Dev.getQuality());
  Serial.printf("Rx access    %d\n", Dev.getAccess());
  Serial.printf("Cell cid     %d\n", Dev.getCid());
  Serial.printf("Cell tac     %d\n", Dev.getTac());
  char mlts[322];
  Dev.getMlts(mlts, 322);
  Serial.printf("Cell mlts    %s\n", mlts);
  Serial.printf("Elapsed: %d mili seconds\n", millis() - t);

  delay(200);
  coap.response(callback_response);
  coap.start();
  Serial.println("Coap ready");
  delay(200);
}

void loop()
{
  if (Serial.available() > 0) {
    msg = Serial.readString();
    int nindex = msg.lastIndexOf('\n', msg.length() - 2);
    msg = msg.substring(nindex > -1 ? nindex : 0);
    msg.trim();
    if (msg.length() > 0) {
      coap.put(IPAddress(85, 246, 38, 211), 5683, "lys", msg.c_str());
      msg_sent = false;
    }
  }

  if (msg.length() > 0) {
    //coap.put(IPAddress(146, 193, 41, 162), 5683, "lys", msg.c_str());
    coap.put(IPAddress(85, 246, 169, 148), 5683, "lys", msg.c_str());
  }

  delay(1000);
  coap.loop();
}