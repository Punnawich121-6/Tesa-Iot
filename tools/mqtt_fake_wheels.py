#!/usr/bin/env python3
"""ส่งค่าล้อปลอมขึ้น broker ของ Bitstream Studio

ใช้ทดสอบโหนด MQTT Subscriber ใน Sensor Studio โดยไม่ต้องเปิดเบราว์เซอร์ —
ถ้าสคริปต์นี้ทำให้โหนดขึ้น Received แต่ console.html ไม่ขึ้น = ปัญหาอยู่ฝั่งเว็บ
ถ้าสคริปต์นี้ก็ไม่ขึ้น = ปัญหาอยู่ที่การตั้งค่าโหนด/broker

    python3 tools/mqtt_fake_wheels.py            # 20 Hz, หุ่นวิ่งเป็นวงกลม
    python3 tools/mqtt_fake_wheels.py --hz 5
"""
import argparse, json, math, time
import paho.mqtt.client as mqtt

HOST, PORT = '127.0.0.1', 1883
# ค่าเริ่มต้นของโหนด MQTT Subscriber ใน Sensor Studio (จาก defaultConfig.subscribeTopic)
TOPIC_TWIN  = 'sensor-studio/connectivity/telemetry'
TOPIC_DRIVE = 'firebot/tesa-demo/robot/R1/drive'

R, L = 0.04515, 0.3335        # วัดจาก Firefighter-robot.stl

ap = argparse.ArgumentParser()
ap.add_argument('--hz', type=float, default=20)
a = ap.parse_args()

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.connect(HOST, PORT, 30)
c.loop_start()
print(f'ส่งขึ้น {HOST}:{PORT} ที่ {a.hz} Hz\n  {TOPIC_TWIN}\n  {TOPIC_DRIVE}\nCtrl+C เพื่อหยุด\n')

dt = 1.0 / a.hz
v, w = 0.45, 0.55                      # วิ่งเป็นวงกลม
posL = posR = 0.0
x = y = th = 0.0
seq = 0
try:
    while True:
        vl, vr = v - w*L/2, v + w*L/2
        wl, wr = vl/R, vr/R
        posL += wl*dt; posR += wr*dt
        th += w*dt
        x  += v*math.sin(th)*dt
        y  += v*math.cos(th)*dt
        seq += 1
        r2 = lambda n, d=2: round(n, d)
        # normalize มุมหุ่นให้อยู่ในช่วง (-180, 180] เหมือนที่ console.html ทำ
        # thetaDeg กับ thetaRad ต้องเป็นมุมเดียวกัน ไม่งั้นต่อโหนดคนละฟิลด์ได้ผลไม่ตรงกัน
        th_n = (th + math.pi) % (2*math.pi) - math.pi
        twin = {'rpmL': r2(wl*60/(2*math.pi),1), 'rpmR': r2(wr*60/(2*math.pi),1),
                'radL': r2(posL,3), 'radR': r2(posR,3),
                'x': r2(x), 'y': r2(y),
                'thetaDeg': r2(math.degrees(th_n),1),
                'thetaRad': r2(th_n,4)}
        drive = {'ts': int(time.time()*1000), 'seq': seq,
                 'wheels': [{'id':'L','posRad':twin['radL'],'rpm':twin['rpmL'],'currentA':1.1,'tempC':38.0},
                            {'id':'R','posRad':twin['radR'],'rpm':twin['rpmR'],'currentA':1.2,'tempC':38.4}],
                 'odom': {'x':twin['x'],'y':twin['y'],'thetaDeg':twin['thetaDeg'],'distM':r2(v*seq*dt,1)},
                 'vel': {'linear':v,'angular':w},
                 'health': {'slip':0.05,'stalled':False,'tiltDeg':2.1,'whPerM':0.8}}
        c.publish(TOPIC_TWIN,  json.dumps(twin))
        c.publish(TOPIC_DRIVE, json.dumps(drive))
        if seq % int(max(1,a.hz)) == 0:
            print(f'  seq={seq}  rpmL={twin["rpmL"]}  rpmR={twin["rpmR"]}  x={twin["x"]}  y={twin["y"]}  θ={twin["thetaDeg"]}°')
        time.sleep(dt)
except KeyboardInterrupt:
    c.loop_stop(); print(f'\nส่งไปทั้งหมด {seq} ข้อความ')
