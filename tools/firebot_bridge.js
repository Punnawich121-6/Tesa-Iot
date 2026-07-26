/* ═══════════════════════════════════════════════════════════════════════
   FireBot live bridge — เชื่อม console.html เข้ากับ Pancabo Fire Control
   console.html publish ค่าจริงขึ้น broker ของ Bitstream Studio
   หน้านี้ subscribe แล้วเอาไปแทนค่าที่เดิมสุ่มด้วย Math.random()
   ถ้าไม่มีข้อมูลเข้า (console.html ปิด) จะกลับไปใช้ sim เดิมเองอัตโนมัติ
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  const BROKER = 'ws://127.0.0.1:8883/mqtt';
  const T_TWIN = 'sensor-studio/connectivity/telemetry';
  const T_SCAN = 'firebot/tesa-demo/robot/R1/scan';
  const STALE  = 2500;                     // ms — เกินนี้ถือว่าข้อมูลเก่า

  const LIVE = { ts: 0, msgs: 0 };
  window.__FIREBOT_LIVE = null;
  const fresh = () => window.__FIREBOT_LIVE && (Date.now() - LIVE.ts < STALE);

  /* ---------- ป้ายบอกสถานะ LIVE / SIM ---------- */
  const chip = document.createElement('div');
  chip.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:99999;white-space:pre;'
    + 'font:600 11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;padding:8px 12px;'
    + 'border-radius:9px;background:rgba(13,17,23,.94);border:1px solid #30363d;'
    + 'color:#8b949e;pointer-events:none;box-shadow:0 4px 18px rgba(0,0,0,.35)';
  function paintChip() {
    const L = window.__FIREBOT_LIVE;
    const ok = fresh();
    chip.style.borderColor = ok ? '#238636' : '#6e7681';
    chip.style.color = ok ? '#3fb950' : '#8b949e';
    chip.textContent = ok
      ? '● LIVE · console.html\n'
        + LIVE.msgs + ' msg  ·  ' + (L.tempC == null ? '—' : L.tempC.toFixed(1) + '°C')
        + '  ·  ' + (L.validPts == null ? '—' : L.validPts + ' LiDAR pts')
      : '○ SIM · ไม่พบ console.html\n' + BROKER;
  }
  function mountChip() { document.body.appendChild(chip); paintChip(); setInterval(paintChip, 700); }
  if (document.body) mountChip(); else addEventListener('DOMContentLoaded', mountChip);

  /* ---------- MQTT ---------- */
  if (typeof mqtt === 'undefined') { console.warn('[firebot] ไม่พบไลบรารี mqtt.js'); return; }
  const client = mqtt.connect(BROKER, {
    clientId: 'pancabo-' + Math.random().toString(16).slice(2, 8),
    reconnectPeriod: 3000, connectTimeout: 5000, clean: true,
  });
  client.on('connect', () => {
    client.subscribe([T_TWIN, T_SCAN], { qos: 0 });
    console.log('[firebot] ต่อ broker แล้ว · subscribe', T_TWIN, T_SCAN);
  });
  client.on('error', e => console.warn('[firebot] mqtt error', e && e.message));
  client.on('message', (topic, buf) => {
    let p; try { p = JSON.parse(buf.toString()); } catch (e) { return; }
    const L = window.__FIREBOT_LIVE || (window.__FIREBOT_LIVE = {});
    LIVE.ts = Date.now(); LIVE.msgs++;
    if (topic === T_SCAN) { L.ranges = p.ranges; L.rev = p.rev; return; }
    const ch = p.channels || {};
    const pick = (k, prev) => (ch[k] != null ? ch[k] : prev);
    L.tempC      = pick('fire.tempC', L.tempC);
    L.smokePpm   = pick('fire.smokePpm', L.smokePpm);
    L.flame      = pick('fire.flame', L.flame);
    L.nearestM   = pick('fire.nearestM', L.nearestM);
    L.batteryPct = pick('power.batteryPct', L.batteryPct);
    L.tankPct    = pick('water.tankPct', L.tankPct);
    L.validPts   = pick('lidar.validPts', L.validPts);
    L.odomX      = pick('odom.x', L.odomX);
    L.odomY      = pick('odom.y', L.odomY);
    L.headingDeg = pick('imu.headingDeg', L.headingDeg);
    L.rpmL       = pick('wheel.rpmL', L.rpmL);
    L.rpmR       = pick('wheel.rpmR', L.rpmR);
  });

  /* ---------- ต่อเข้า React: ทับค่าที่ tick() สุ่มไว้ ด้วยค่าจริง ---------- */
  window.__firebotAttach = function (app) {
    // แพตช์ที่ instance ไม่ใช่ prototype — setInterval ของแอปเรียก this.tick()
    // ซึ่งจะเจอ property ของ instance ก่อน จึงพอ และไม่กระทบ class เดิม
    const origTick = app.tick.bind(app);
    app.tick = function () {
      origTick();
      if (!fresh()) return;                          // ไม่มีข้อมูลจริง → ปล่อย sim เดิมทำงาน
      const L = window.__FIREBOT_LIVE;
      app.setState(s => {
        const out = {};
        const ids = Object.keys(s.sensors || {});
        if (ids.length && L.tempC != null) {
          const id = ids[0];                         // โซนแรก = โซนที่หุ่นตัวจริงอยู่
          const cur = s.sensors[id] || {};
          const sensors = Object.assign({}, s.sensors);
          sensors[id] = Object.assign({}, cur, {
            temp:  L.tempC,
            smoke: L.smokePpm != null ? L.smokePpm : cur.smoke,
            flame: L.flame != null ? L.flame : cur.flame,
            co:    8 + (L.smokePpm || 0) / 60,       // ประมาณ CO จากความหนาแน่นควัน
            hist:  (cur.hist || []).concat(L.tempC).slice(-24),
          });
          out.sensors = sensors;
        }
        if (Array.isArray(s.robots) && L.odomX != null) {
          // odom (เมตร) → ร้อยละบนผังอาคาร 10 × 8 m ที่จำลองใน console.html
          const px = Math.max(2, Math.min(98, (L.odomX * 1000 + 5000) / 10000 * 100));
          const py = Math.max(2, Math.min(98, (L.odomY * 1000 + 4000) /  8000 * 100));
          out.robots = s.robots.map(r => r.id !== 'R1' ? r : Object.assign({}, r, {
            x: px, y: py, tx: px, ty: py,
            bat: L.batteryPct != null ? Math.round(L.batteryPct) : r.bat,
          }));
        }
        return out;
      });
    };
    console.log('[firebot] ต่อเข้า dashboard สำเร็จ — tick() ใช้ค่าจริงแล้ว');
  };

  /* ---------- LiDAR: แทน polygon ปลอม 40 จุด ด้วยสแกนจริง 360 จุด ---------- */
  window.__firebotRad = function (i, n) {
    const L = window.__FIREBOT_LIVE;
    if (!fresh() || !L.ranges) return null;          // null → แอปใช้ค่าปลอมเดิม
    // i=0 ของแอปชี้ไปทางขวาจอ หมุน 90° เพื่อให้หน้าหุ่นชี้ขึ้น
    const base = Math.round((i / n * 360 + 90) % 360);
    const span = Math.max(1, Math.round(360 / n));
    let best = null;
    for (let d = 0; d < span; d++) {                 // เอาค่าที่ใกล้สุดในช่วงมุมนั้น
      const r = L.ranges[(base + d) % 360];
      if (r == null) continue;
      if (best === null || r < best) best = r;
    }
    return best === null ? 54 : 6 + Math.min(1, best / 12) * 48;   // ranges เป็นเมตร (สูงสุด 12)
  };
})();
