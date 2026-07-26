#!/usr/bin/env python3
"""แพตช์ 'Pancabo Fire Control.html' ให้รับค่าจริงจาก console.html ผ่าน MQTT

dashboard เป็นบันเดิล React ที่จำลองข้อมูลด้วย Math.random() ทั้งหมด และไม่มี
MQTT client จริง สคริปต์นี้แทรกสะพานเชื่อม (tools/firebot_bridge.js) + mqtt.js
เข้าไปในบันเดิล แล้วแก้ 2 จุดในโค้ดแอป:

  1. componentDidMount → เรียก window.__firebotAttach(this) เพื่อส่ง instance ให้สะพาน
  2. การคำนวณรัศมี LiDAR → ใช้ window.__firebotRad() ถ้ามีสแกนจริง

ใช้เมื่อ export dashboard ใหม่จากเครื่องมือออกแบบแล้วไฟล์ถูกทับ:

    python3 tools/patch_pancabo.py                       # แพตช์ในที่เดิม (สำรอง .orig ให้)
    python3 tools/patch_pancabo.py --check               # ดูว่าแพตช์แล้วหรือยัง
    python3 tools/patch_pancabo.py --restore             # คืนไฟล์เดิมจาก .orig
"""
import argparse, json, os, re, shutil, sys

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, 'Pancabo Fire Control.html')
BACKUP = TARGET + '.orig'
BRIDGE = os.path.join(ROOT, 'tools', 'firebot_bridge.js')
MQTTJS = os.path.join(ROOT, 'vendor', 'mqtt.min.js')

A1 = 'this.tick();'
A2 = 'const rad = 44 + wob;'
MARK = 'FireBot live bridge'


def template_of(s):
    m = re.search(r'(<script type="__bundler/template"[^>]*>)([\s\S]*?)(</script>)', s)
    if not m:
        sys.exit('ไม่พบ <script type="__bundler/template"> — ไฟล์นี้ไม่ใช่บันเดิลที่รองรับ')
    return m


def patch(src):
    m = template_of(src)
    html = json.loads(m.group(2).strip())
    if MARK in html:
        return None, 'แพตช์ไว้แล้ว'

    for a in (A1, A2):
        n = html.count(a)
        if n != 1:
            return None, 'หา anchor %r ไม่เจอหรือเจอซ้ำ (%d ครั้ง) — โค้ดแอปเปลี่ยนไป' % (a, n)

    html = html.replace(A1, A1 + '\n    if (window.__firebotAttach) window.__firebotAttach(this);', 1)
    html = html.replace(A2, 'const rad = (window.__firebotRad ? window.__firebotRad(i,40) : null) || (44 + wob);', 1)

    mqttjs = open(MQTTJS, encoding='utf-8').read()
    bridge = open(BRIDGE, encoding='utf-8').read()
    for name, code in (('mqtt.min.js', mqttjs), ('firebot_bridge.js', bridge)):
        if '</script' in code:
            return None, '%s มี </script> — แทรกตรง ๆ ไม่ได้' % name

    inject = ('<script>/* mqtt.js v5 (vendored) */\n' + mqttjs + '\n</script>\n'
              '<script>\n' + bridge + '\n</script>\n')
    mm = re.search(r'<script(?![^>]*\ssrc=)[^>]*>', html)
    if not mm:
        return None, 'ไม่พบ inline script ของแอป'
    html = html[:mm.start()] + inject + html[mm.start():]

    # เทมเพลตเก็บเป็น JSON string; escape '<' กัน </script> ปิดแท็กก่อนเวลา
    raw = json.dumps(html, ensure_ascii=False).replace('<', '\\u003C')
    if json.loads(raw) != html:
        return None, 'round-trip ของ JSON ไม่ตรง'
    return src[:m.start(2)] + '\n' + raw + src[m.end(2):], None


ap = argparse.ArgumentParser()
ap.add_argument('--check', action='store_true')
ap.add_argument('--restore', action='store_true')
a = ap.parse_args()

if not os.path.exists(TARGET):
    sys.exit('ไม่พบ %s' % TARGET)

if a.restore:
    if not os.path.exists(BACKUP):
        sys.exit('ไม่มีไฟล์สำรอง %s' % BACKUP)
    shutil.copy(BACKUP, TARGET)
    sys.exit('คืนไฟล์เดิมแล้ว')

src = open(TARGET, encoding='utf-8').read()
html = json.loads(template_of(src).group(2).strip())

if a.check:
    ok = MARK in html
    print('สถานะ: %s' % ('แพตช์แล้ว ✓' if ok else 'ยังไม่แพตช์'))
    if ok:
        for n, p in (('__firebotAttach', 'window.__firebotAttach(this)'),
                     ('__firebotRad', 'window.__firebotRad(i,40)'),
                     ('mqtt.js', 'var mqtt=')):
            print('  %s %s' % ('✓' if p in html else '✗', n))
    sys.exit(0)

out, err = patch(src)
if err:
    sys.exit('ไม่ได้แพตช์: %s' % err)
if not os.path.exists(BACKUP):
    shutil.copy(TARGET, BACKUP)
    print('สำรองต้นฉบับไว้ที่ %s' % os.path.basename(BACKUP))
open(TARGET, 'w', encoding='utf-8').write(out)
print('แพตช์สำเร็จ — %.1f KB' % (len(out) / 1024))
