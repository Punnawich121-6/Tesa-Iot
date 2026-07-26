#!/usr/bin/env python3
"""ดูว่ามีอะไรวิ่งอยู่บน broker ของ Bitstream Studio จริงไหม

    python3 tools/mqtt_watch.py                  # ดู topic ของ FireBot
    python3 tools/mqtt_watch.py '#'              # ดูทุก topic (รวม bitstream2/*)
    python3 tools/mqtt_watch.py 'bitstream2/#'   # ดูแค่ฝั่ง Bitstream
"""
import json, sys, time
import paho.mqtt.client as mqtt

HOST, PORT = '127.0.0.1', 1883          # ฝั่ง TCP ของ broker เดียวกับ ws:8883
TOPIC = sys.argv[1] if len(sys.argv) > 1 else 'firebot/#'
n = 0

def on_connect(c, u, f, rc, props=None):
    if rc != 0:
        print(f'ต่อ broker ไม่ได้ (rc={rc}) — Bitstream Studio เปิดอยู่ไหม?'); return
    print(f'ต่อแล้ว {HOST}:{PORT}  ·  subscribe "{TOPIC}"\n')
    c.subscribe(TOPIC)

def on_message(c, u, msg):
    global n; n += 1
    body = msg.payload.decode('utf-8', 'replace')
    try:
        body = json.dumps(json.loads(body), ensure_ascii=False, separators=(',', ':'))
    except Exception:
        pass
    if len(body) > 220: body = body[:220] + '…'
    print(f'[{n:5d}] {time.strftime("%H:%M:%S")}  {msg.topic}\n        {body}')

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_connect, c.on_message = on_connect, on_message
c.connect(HOST, PORT, 30)
try:
    c.loop_forever()
except KeyboardInterrupt:
    print(f'\nรับได้ทั้งหมด {n} ข้อความ')
