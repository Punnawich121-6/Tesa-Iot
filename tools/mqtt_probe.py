#!/usr/bin/env python3
"""ยิงข้อความไปหลาย topic พร้อมกัน โดยใส่ชื่อ topic ไว้ในตัว payload เอง

ใช้หาว่าโหนด MQTT Subscriber subscribe topic อะไรอยู่จริง —
อ่านค่าที่โผล่ใน Message Viewer แล้วดูฟิลด์ FROM_TOPIC จะรู้ทันที
ถ้าไม่มีอันไหนโผล่เลย = โหนดไม่ได้รับข้อมูล ไม่เกี่ยวกับชื่อ topic
"""
import json, time
import paho.mqtt.client as mqtt

# topic มาตรฐานของระบบ Bitstream — ได้จาก repo TESAIoT_Hackathon/web-app/shared/ex-mqtt.js
#   devkitTwinTopic(id) = device/<id>/devkit-twin/telemetry   (default id = devkit-twin-01)
DEVICE = 'devkit-twin-01'
TOPICS = [
    'sensor-studio/connectivity/telemetry',     # ★★ ค่าเริ่มต้นจริงของโหนด MQTT Subscriber
    f'device/{DEVICE}/devkit-twin/telemetry',   # ของ DevKit Twin (ตัวอย่างใน hackathon repo)
    'firebot/tesa-demo/robot/R1/twin',
    'firebot/tesa-demo/robot/R1/drive',
    'sensors/lab/temp',                         # topic ที่ ex10_mqtt_publisher ใช้เป็นค่าเริ่มต้น
    'bitstream2/evt/sensor',
    'bitstream2/hmi',
    'test',
]

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.connect('127.0.0.1', 1883, 30)
c.loop_start()
print('ยิงไป %d topic ทุก 1 วินาที — ดูใน Message Viewer ว่าโผล่อันไหน\n' % len(TOPICS))
for t in TOPICS: print('  ', t)
print('\nCtrl+C เพื่อหยุด')

n = 0
try:
    while True:
        n += 1
        for t in TOPICS:
            # ใส่ทั้งรูปแบบ channels (มาตรฐาน DevKit Twin) และ FROM_TOPIC เพื่อระบุที่มา
            c.publish(t, json.dumps({
                'FROM_TOPIC': t, 'n': n,
                'deviceId': DEVICE, 'ts': int(time.time()*1000),
                'channels': {
                    'wheel.rpmL': 42.0, 'wheel.rpmR': 58.0,
                    'wheel.radL': round(n*0.7,3), 'wheel.radR': round(n*0.9,3),
                    'odom.x': 1.25, 'odom.y': -0.4, 'odom.thetaDeg': 33.0,
                },
            }))
        if n % 10 == 0: print('  ยิงรอบที่', n)
        time.sleep(1)
except KeyboardInterrupt:
    c.loop_stop(); print('\nหยุดแล้ว (%d รอบ)' % n)
