# ต่อล้อ FireBot เข้า Bitstream Studio (VS Code)

เอาค่าล้อจาก `console.html` เข้าไปหมุนโมเดลใน Digital Twin ของ **extension ตัวจริง**
ไม่ได้จำลอง Bitstream ในหน้าเว็บ — เว็บเป็นแค่ผู้ส่ง (publisher), extension เป็นผู้รับ (subscriber)

```
console.html ──ws://127.0.0.1:8883──► MQTT Broker ของ Bitstream ──► โหนด MQTT Subscriber
 (เบราว์เซอร์)                          (เปิดโดย extension)              └─► Part Spin ×2
                                                                        └─► Part Transform
```

Broker เป็นตัวเดียวกันทั้งสองพอร์ต — ต่างกันแค่วิธีขนส่ง:

| พอร์ต | โปรโตคอล | ใครใช้ |
|---|---|---|
| `1883` | MQTT บน TCP | Python, ESP32, สคริปต์ใน `tools/` |
| `8883` | MQTT over WebSocket | `console.html` (JS ในเบราว์เซอร์เปิด TCP ดิบไม่ได้) |

---

## Topic ที่ส่งออก

**`firebot/tesa-demo/robot/R1/twin`** ← ใช้อันนี้กับ Twin (แบน ไม่มี array)

```json
{ "rpmL":126.9, "rpmR":124.3,
  "radL":10.863, "radR":10.712,
  "x":3.42, "y":-1.08,
  "thetaDeg":58.3, "thetaRad":1.0176 }
```

| ฟิลด์ | หน่วย | ใช้กับ |
|---|---|---|
| `rpmL` / `rpmR` | rpm | Part Spin — ถ้าโหนดรับ **ความเร็ว** |
| `radL` / `radR` | rad สะสม (ไม่ wrap) | Part Spin — ถ้าโหนดรับ **มุมสัมบูรณ์** |
| `x` / `y` | m | Part Transform → position |
| `thetaDeg` / `thetaRad` | ° / rad | Part Transform → rotation (แกน Y) |

ส่งทั้ง rpm และ rad เพราะยังไม่รู้ว่าโหนด Part Spin รับแบบไหน — ต่อแบบที่ใช้ได้ อีกอันปล่อยว่างไว้

**`firebot/tesa-demo/robot/R1/drive`** ← payload เต็ม (มี `currentA`, `tempC`, `slip`, `stalled`)
เอาไว้ต่อเกจ/HMI ไม่ใช่สำหรับ Twin

---

## ขั้นตอน

### 1. ตรวจว่า broker เปิดอยู่

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep -E '1883|8883'
```

ต้องเห็น `Code Helper` ฟังทั้ง `*:1883` และ `*:8883` ถ้าไม่เห็น → เปิด Bitstream Studio ใน VS Code
(สั่ง **Start MQTT Broker** จากเมนู ☰ ถ้ายังไม่ขึ้น)

### 2. ทดสอบโหนดก่อน โดยยังไม่ต้องเปิดเบราว์เซอร์

เปิด 2 เทอร์มินัล:

```bash
python3 tools/mqtt_watch.py 'firebot/#'      # ดูว่ามีอะไรวิ่ง
python3 tools/mqtt_fake_wheels.py --hz 5     # ส่งค่าล้อปลอม (หุ่นวิ่งเป็นวงกลม)
```

**ทำขั้นนี้ก่อนเสมอ** เพราะมันแยกปัญหาให้:

| อาการ | แปลว่า |
|---|---|
| `mqtt_watch` เห็นข้อความ + โหนดขึ้น `Received` | ✅ ตั้งค่าโหนดถูก ไปข้อ 3 |
| `mqtt_watch` เห็น แต่โหนดไม่ขึ้น | ตั้งค่าโหนดผิด (URL / topic / ยังไม่กด connect) |
| `mqtt_watch` ไม่เห็นอะไรเลย | broker ไม่ทำงาน หรือ Bitstream ปิดอยู่ |

### 3. ตั้งค่าโหนด MQTT Subscriber

ในเวิร์กสเปซ **Sensor Studio** คลิกโหนดที่วางไว้ แล้วกรอกในแผง properties:

| ช่อง | ค่า |
|---|---|
| Broker / URL | `ws://127.0.0.1:8883` |
| Topic | `firebot/tesa-demo/robot/R1/twin` |
| QoS | `0` |

> ถ้าช่อง URL ไม่รับ `ws://` ให้ลอง `mqtt://127.0.0.1:1883` — โหนดอาจรันในฝั่ง extension host
> (Node.js) ซึ่งต่อ TCP ได้ ลองทีละอันจนเอาต์พุต **Connected** เปลี่ยนเป็น `true`

เอาต์พุตของโหนด:

- **Connected** — `true` เมื่อต่อ broker ติด (ยังไม่ต้องมีข้อความ)
- **Message** — ตัวข้อความ (สตริง JSON)
- **Topic** — ชื่อ topic ที่มา
- **Received** — กระตุกทุกครั้งที่มีข้อความเข้า ใช้ดูว่ามีข้อมูลไหลจริง

### 4. แกะ JSON แล้วต่อเข้าโมเดล

```
MQTT Subscriber ──Message──► [แกะ JSON] ──rpmL──► Part Spin  (ล้อซ้าย)
                                        ──rpmR──► Part Spin  (ล้อขวา)
                                        ──x,y────► Part Transform (position)
                                        ──thetaRad─► Part Transform (rotation Y)
```

- ถ้ามีโหนดแกะ JSON ให้ใช้เลย ถ้าไม่มีให้ใช้ **JSON Creator** / **Multiplexer** ในหมวด utility
- โมเดล: ใช้โหนด **Model Source** เลือก **Two-Wheels Bot** จากคลัง
  (ถ้ายังไม่มีในเครื่อง สั่ง **Download Free Assets from GitHub**)
- **Part Spin** / **Part Transform** ต้องระบุ *ชื่อ part* ในไฟล์ GLB — เปิดโมเดลใน
  **Model Viewer** เพื่อดูชื่อ part ของล้อก่อน แล้วเอาชื่อนั้นไปกรอก
- ถ้า `thetaRad` หมุนผิดแกน ให้ลองสลับไปแกนอื่น หรือใส่ **Degrees ⇄ Radians** คั่น

### 5. ต่อจาก console.html ตัวจริง

เปิด `http://localhost:8080/console.html` → แผง **เชื่อมต่อ Bitstream** → กด **🔗 ต่อ broker**

- ป้ายบนแถบหัวต้องเปลี่ยนเป็น **MQTT: ต่อแล้ว** (สีเขียว)
- ตัวเลข "ส่งไปแล้ว" ต้องเดินขึ้น
- ขับหุ่นด้วย W/A/S/D → ล้อในโมเดล Bitstream ต้องหมุนตาม

อัตราส่งปรับได้ 5/10/20/30 Hz (ค่าเริ่มต้น 20 Hz) — ถ้าโฟลว์กระตุกให้ลดลงเหลือ 10 Hz

---

## ข้อจำกัดที่ต้องรู้

1. **Bitstream โหลด GLB ไม่ใช่ STL** — `Firefighter-robot.stl` เอาเข้า Twin ตรง ๆ ไม่ได้
   โมเดล **Two-Wheels Bot** ในคลังเป็นหุ่นสองล้อทั่วไป ไม่ใช่หุ่นดับเพลิงของเรา
   ถ้าอยากเห็นหุ่นตัวจริงหมุนล้อ ให้ดูที่ `console.html` (หรือแปลง STL → GLB ทีหลัง)
2. **broker มีชีวิตเท่าที่ VS Code + Bitstream เปิดอยู่** ปิด VS Code = ระบบตาย
   ถ้าจะให้รันเองตลอด ค่อยรัน `mosquitto` เพิ่มแล้ว relay — topic เหมือนกันหมด ไม่ต้องแก้โค้ด
3. **Bitstream สั่งขับล้อกลับไม่ได้** — คำสั่งที่ extension มีคือ `sensor.cfg.*` / `bmi270.mode.*`
   ไม่มีคำสั่งมอเตอร์ ทิศทางข้อมูลเป็นทางเดียว: console → Bitstream
4. **แผง Sensor Telemetry จะไม่แสดงค่าล้อ** เพราะแค็ตตาล็อกล็อกไว้ 4 เซนเซอร์
   (โปรไฟล์ `minimal-sensor`) ค่าล้ออยู่ในโฟลว์กับ Twin เท่านั้น — เป็นเรื่องปกติ ไม่ใช่ bug
