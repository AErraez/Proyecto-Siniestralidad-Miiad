const API_BASE = '/api';
const BOGOTA   = [4.6534, -74.0837];

// ── SVG ICON HELPERS ──────────────────────────────────────────────────────────
const _s = (paths, size = '12') =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;

const ICONS = {
  // Severity badge icons (16px)
  checkCircle: _s(`<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>`, '16'),
  alertTri:    _s(`<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`, '16'),
  xOctagon:    _s(`<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>`, '16'),
  // Action card icons (20px)
  shieldAlert: _s(`<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>`, '20'),
  ambulance:   _s(`<path d="M10 10H6"/><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>`, '20'),
  info:        _s(`<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>`, '20'),
  // Chips (12px)
  mapPin:      _s(`<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>`),
  skullX:      _s(`<circle cx="12" cy="11" r="8"/><path d="M8 18v3h8v-3"/><path d="M9 15h.01"/><path d="M15 15h.01"/>`),
  // Factor tag icons (12px)
  bike:        _s(`<circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M15 6h2l3.26 5.74"/><path d="m10 14-1.5-2.5L12 7l3 7-4.5-3.5H15"/><path d="M5.5 14H9"/>`),
  person:      _s(`<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>`),
  zap:         _s(`<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>`),
  wine:        _s(`<path d="M8 22h8"/><path d="M7 10h10"/><path d="M12 15v7"/><path d="M12 15a5 5 0 0 0 5-5V3H7v7a5 5 0 0 0 5 5z"/>`),
  truck:       _s(`<path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11v12H5"/><rect x="9" y="11" width="14" height="10" rx="2"/><circle cx="12" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>`),
  clock:       _s(`<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`),
  moon:        _s(`<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`),
  car:         _s(`<path d="M19 17H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2z"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>`),
};

// ── CLUSTER STATS ─────────────────────────────────────────────────────────────
let clusterStats = {};

async function loadClusterStats() {
  try {
    const r = await fetch(`${API_BASE}/stats/clusters`);
    if (r.ok) clusterStats = await r.json();
  } catch { /* silently fail — endpoint available after re-running train_model.py */ }
}
loadClusterStats();

// ── PICKER MAP ────────────────────────────────────────────────────────────────
const pickerMap = L.map('picker-map', { attributionControl: false }).setView(BOGOTA, 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(pickerMap);

const pickerIcon = L.divIcon({
  html: '<div style="width:14px;height:14px;background:#2563eb;border:2px solid #fff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,.25)"></div>',
  iconSize: [14, 14], iconAnchor: [7, 7], className: '',
});
let pickerMarker = L.marker([4.609, -74.082], { icon: pickerIcon, draggable: true }).addTo(pickerMap);

function setCoords(lat, lon) {
  document.getElementById('inp-lat').value        = lat.toFixed(5);
  document.getElementById('inp-lon').value        = lon.toFixed(5);
  document.getElementById('disp-lat').textContent = lat.toFixed(5);
  document.getElementById('disp-lon').textContent = lon.toFixed(5);
}
pickerMarker.on('dragend', e => { const p = e.target.getLatLng(); setCoords(p.lat, p.lng); });
pickerMap.on('click', e => { pickerMarker.setLatLng(e.latlng); setCoords(e.latlng.lat, e.latlng.lng); });

// ── INCIDENT MAP ──────────────────────────────────────────────────────────────
const renderer    = L.canvas({ padding: 0.5 });
const incidentMap = L.map('incident-map', { preferCanvas: true }).setView(BOGOTA, 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(incidentMap);

const incLayer = L.layerGroup().addTo(incidentMap);
const clsLayer = L.layerGroup();
let searchMarker = null;
const layerState = { incidents: true, clusters: false };

const SEV_COLOR   = ['#2563eb', '#d97706', '#dc2626'];
const CLS_PALETTE = [
  '#7c3aed','#0891b2','#059669','#b45309','#be123c',
  '#1d4ed8','#15803d','#a16207','#9f1239','#6d28d9',
  '#0369a1','#047857','#92400e','#831843','#4338ca',
];

function toggleLayer(which) {
  layerState[which] = !layerState[which];
  const layer = which === 'incidents' ? incLayer : clsLayer;
  const btnId  = which === 'incidents' ? 'btn-toggle-inc' : 'btn-toggle-cls';
  layerState[which] ? layer.addTo(incidentMap) : layer.remove();
  document.getElementById(btnId).classList.toggle('active', layerState[which]);
}

async function loadMapData() {
  try {
    const r = await fetch(`${API_BASE}/map/data`);
    if (!r.ok) return;
    const data = await r.json();
    data.incidents.forEach(p => {
      L.circleMarker([p.lat, p.lon], {
        renderer, radius: 3,
        color: SEV_COLOR[p.severity] ?? '#64748b',
        fillColor: SEV_COLOR[p.severity] ?? '#64748b',
        fillOpacity: 0.55, weight: 0,
      }).addTo(incLayer);
    });
    data.clusters.forEach(c => {
      const col = CLS_PALETTE[c.id % CLS_PALETTE.length];
      L.circle([c.lat, c.lon], {
        radius: 1500, color: col, fillColor: col,
        fillOpacity: 0.1, weight: 1.5, dashArray: '5,4',
      }).bindTooltip(`Zona de riesgo ${c.id}`, { direction: 'top' }).addTo(clsLayer);
    });
  } catch (e) {
    console.warn('Datos del mapa no disponibles:', e.message);
  }
}
loadMapData();

function updateSearchMarker(lat, lon) {
  const icon = L.divIcon({
    html: '<div style="width:18px;height:18px;background:#7c3aed;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 8px rgba(124,58,237,.45)"></div>',
    iconSize: [18, 18], iconAnchor: [9, 9], className: '',
  });
  if (searchMarker) {
    searchMarker.setLatLng([lat, lon]);
  } else {
    searchMarker = L.marker([lat, lon], { icon }).addTo(incidentMap);
    searchMarker.bindPopup('<b>Punto consultado</b>');
  }
  incidentMap.panTo([lat, lon]);
}

// ── HISTORICAL CHART ──────────────────────────────────────────────────────────
const STATIC_HIST = [
  { mes:'Ene', fatales:48,  heridos:610, danos:820 },
  { mes:'Feb', fatales:41,  heridos:570, danos:750 },
  { mes:'Mar', fatales:52,  heridos:640, danos:890 },
  { mes:'Abr', fatales:44,  heridos:590, danos:760 },
  { mes:'May', fatales:58,  heridos:680, danos:940 },
  { mes:'Jun', fatales:55,  heridos:660, danos:910 },
  { mes:'Jul', fatales:49,  heridos:620, danos:830 },
  { mes:'Ago', fatales:53,  heridos:650, danos:870 },
  { mes:'Sep', fatales:47,  heridos:600, danos:800 },
  { mes:'Oct', fatales:62,  heridos:700, danos:960 },
  { mes:'Nov', fatales:57,  heridos:675, danos:920 },
  { mes:'Dic', fatales:45,  heridos:580, danos:780 },
];

function renderChart(rows) {
  const maxVal = Math.max(...rows.map(r => r.fatales + r.heridos + r.danos));
  const el = document.getElementById('hist-chart');
  el.style.opacity = '1';
  el.innerHTML = rows.map(row => `
    <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px">
      <div style="width:100%;display:flex;flex-direction:column;align-items:stretch;gap:1px;height:72px;justify-content:flex-end">
        <div class="bar fatal"   style="height:${(row.fatales / maxVal * 68).toFixed(1)}px" title="Fatales: ${row.fatales}"></div>
        <div class="bar heridos" style="height:${(row.heridos / maxVal * 68).toFixed(1)}px" title="Heridos: ${row.heridos}"></div>
        <div class="bar danos"   style="height:${(row.danos   / maxVal * 68).toFixed(1)}px" title="Daños: ${row.danos}"></div>
      </div>
      <div class="bar-label">${(row.mes || '').slice(0, 3)}</div>
    </div>`).join('');
}

async function loadChart() {
  try {
    const r = await fetch(`${API_BASE}/stats/monthly`);
    if (!r.ok) throw new Error();
    renderChart((await r.json()).monthly);
  } catch {
    renderChart(STATIC_HIST);
  }
}
loadChart();

// ── GAUGE SVG ─────────────────────────────────────────────────────────────────
function buildGauge(pct, color) {
  const r = 70, cx = 90, cy = 85;
  const angle = Math.PI + Math.PI * (pct / 100);
  const tracks = [
    { from:0,  to:20,  c:'rgba(22,163,74,.18)'   },
    { from:20, to:50,  c:'rgba(253,186,116,.28)'  },
    { from:50, to:75,  c:'rgba(217,119,6,.22)'    },
    { from:75, to:100, c:'rgba(220,38,38,.22)'    },
  ];
  const paths = tracks.map(t => {
    const a1 = Math.PI + Math.PI*(t.from/100), a2 = Math.PI + Math.PI*(t.to/100);
    const x1=cx+r*Math.cos(a1), y1=cy+r*Math.sin(a1);
    const x2=cx+r*Math.cos(a2), y2=cy+r*Math.sin(a2);
    return `<path d="M${x1},${y1} A${r},${r} 0 ${(t.to-t.from)>50?1:0} 1 ${x2},${y2}" stroke="${t.c}" stroke-width="10" fill="none"/>`;
  }).join('');
  const nx = cx+(r-12)*Math.cos(angle), ny = cy+(r-12)*Math.sin(angle);
  return `<svg class="gauge-svg" viewBox="0 0 180 95">
    <path d="M${cx-r},${cy} A${r},${r} 0 0 1 ${cx+r},${cy}" stroke="rgba(0,0,0,.07)" stroke-width="10" fill="none"/>
    ${paths}
    <path d="M${cx},${cy} L${nx},${ny}" stroke="${color}" stroke-width="3" stroke-linecap="round"/>
    <circle cx="${cx}" cy="${cy}" r="5" fill="${color}"/>
    <text x="${cx}" y="${cy-14}" text-anchor="middle" fill="${color}" font-family="Rajdhani,sans-serif" font-size="22" font-weight="700">${pct.toFixed(1)}%</text>
    <text x="${cx}" y="${cy+2}" text-anchor="middle" fill="#94a3b8" font-family="IBM Plex Mono" font-size="8">PROBABILIDAD MUERTOS</text>
  </svg>`;
}

// ── PREDICTION ────────────────────────────────────────────────────────────────
async function runPrediction() {
  const btn      = document.getElementById('btn-predict');
  const resultEl = document.getElementById('result-content');

  const lat   = parseFloat(document.getElementById('inp-lat').value);
  const lon   = parseFloat(document.getElementById('inp-lon').value);
  const hora  = parseInt(document.getElementById('inp-hora').value);
  const veh   = parseInt(document.getElementById('inp-veh').value);
  const mes   = parseInt(document.getElementById('inp-mes').value);
  const dia   = document.getElementById('inp-dia').value;
  const clase = document.getElementById('inp-clase').value;

  const flags = {
    con_moto:          document.getElementById('chk-moto').checked    ? 1 : 0,
    con_peaton:        document.getElementById('chk-peaton').checked   ? 1 : 0,
    con_bicicleta:     document.getElementById('chk-bici').checked     ? 1 : 0,
    con_velocidad:     document.getElementById('chk-vel').checked      ? 1 : 0,
    con_embriaguez:    document.getElementById('chk-emb').checked      ? 1 : 0,
    con_carga:         document.getElementById('chk-carga').checked    ? 1 : 0,
    con_menores:       document.getElementById('chk-menores').checked  ? 1 : 0,
    con_persona_mayor: document.getElementById('chk-mayor').checked    ? 1 : 0,
  };

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Calculando...';
  resultEl.innerHTML = `<div class="result-idle">
    <div class="spinner-border text-primary" style="width:30px;height:30px" role="status"></div>
    <span>Consultando modelo...</span></div>`;

  const tags = [];
  if ((hora >= 7 && hora <= 9) || (hora >= 17 && hora <= 20)) tags.push({ icon: ICONS.clock, label: 'Hora Pico' });
  if (hora >= 22 || hora <= 5) tags.push({ icon: ICONS.moon, label: 'Hora Nocturna' });
  if (flags.con_moto)          tags.push({ icon: ICONS.bike,   label: 'Moto' });
  if (flags.con_peaton)        tags.push({ icon: ICONS.person, label: 'Peatón' });
  if (flags.con_bicicleta)     tags.push({ icon: ICONS.bike,   label: 'Bicicleta' });
  if (flags.con_velocidad)     tags.push({ icon: ICONS.zap,    label: 'Exc. Velocidad' });
  if (flags.con_embriaguez)    tags.push({ icon: ICONS.wine,   label: 'Embriaguez' });
  if (flags.con_carga)         tags.push({ icon: ICONS.truck,  label: 'Veh. Carga' });
  if (flags.con_menores)       tags.push({ icon: ICONS.person, label: 'Menores' });
  if (flags.con_persona_mayor) tags.push({ icon: ICONS.person, label: 'Adulto Mayor' });
  if (veh >= 4)                tags.push({ icon: ICONS.car,    label: `${veh} vehículos` });

  document.getElementById('factor-tags').innerHTML = tags.length
    ? tags.map(t => `<span class="factor-tag active">${t.icon} ${t.label}</span>`).join('')
    : '<span class="factor-tag">Sin factores adicionales detectados</span>';

  updateSearchMarker(lat, lon);

  try {
    const resp = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitud: lat, longitud: lon, hora_acc: hora,
        num_vehiculos: veh, dia_semana: dia, clase_acc: clase, mes_num: mes,
        ...flags,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    renderResult(await resp.json());
  } catch (e) {
    resultEl.innerHTML = `
      <div class="error-box">
        <strong>Error al conectar con la API</strong>
        ${e.message}<br><br>
        Verifique que el servidor esté activo en <code>${API_BASE}</code><br>
        ejecutando: <code>uvicorn api:app --host 0.0.0.0 --port 8000</code>
      </div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Calcular Riesgo';
  }
}

// ── RENDER RESULT ─────────────────────────────────────────────────────────────
function renderResult(data) {
  const pM = data.prob_con_muertos * 100;
  const pH = data.prob_con_heridos * 100;
  const pD = data.prob_solo_danos  * 100;

  const colorMap = { 0: 'var(--c-ok)', 1: 'var(--c-warn)', 2: 'var(--c-danger)' };
  const classMap = { 0: 'ok', 1: 'warn', 2: 'danger' };
  const iconMap  = { 0: ICONS.checkCircle, 1: ICONS.alertTri, 2: ICONS.xOctagon };
  const color = colorMap[data.clase_predicha];
  const cls   = classMap[data.clase_predicha];
  const icon  = iconMap[data.clase_predicha];

  // Cluster fatal stats chip (only shown if /stats/clusters endpoint is available)
  const cStats = clusterStats[String(data.zona_cluster)];
  const fatalChip = cStats
    ? `<div class="cluster-chip fatal-chip">${ICONS.skullX} ${cStats.fatales_6m} fatales · últ. 6 meses</div>`
    : '';

  // Action section — 3 steps for heridos, decisive single card for others
  let actionHtml;
  if (data.clase_predicha === 2 || pM >= 20) {
    actionHtml = `
      <div class="action-card critical">
        <div class="action-icon">${ICONS.shieldAlert}</div>
        <div class="action-text">
          <strong>Acción Recomendada</strong>
          ${data.accion_recomendada}
        </div>
      </div>`;
  } else if (data.clase_predicha === 1) {
    actionHtml = `
      <div class="action-card high">
        <div class="action-icon">${ICONS.ambulance}</div>
        <div class="action-text">
          <strong>Protocolo de Respuesta — Con Heridos</strong>
          <div class="action-steps">
            <div class="action-step"><span class="step-num">1</span><span>Despacho inmediato de Ambulancia de Soporte Vital Básico (SVB).</span></div>
            <div class="action-step"><span class="step-num">2</span><span>Pre-alerta a urgencias del centro hospitalario más cercano.</span></div>
            <div class="action-step"><span class="step-num">3</span><span>Despliegue de unidad de Tránsito para control del perímetro y vías de acceso.</span></div>
          </div>
        </div>
      </div>`;
  } else {
    actionHtml = `
      <div class="action-card">
        <div class="action-icon">${ICONS.info}</div>
        <div class="action-text">
          <strong>Acción Recomendada</strong>
          ${data.accion_recomendada}
        </div>
      </div>`;
  }

  document.getElementById('result-content').innerHTML = `
    <div class="d-flex align-items-center gap-4 flex-wrap anim-up">
      <div class="gauge-wrap">${buildGauge(pM, color)}</div>
      <div class="flex-grow-1 d-flex flex-column gap-3">
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <div class="severity-badge ${cls}">${icon} ${data.etiqueta}</div>
          <div class="cluster-chip">${ICONS.mapPin} Zona ${data.zona_cluster}</div>
          ${fatalChip}
        </div>
        <div class="prob-bars">
          <div class="prob-bar-row">
            <div class="prob-bar-label">Solo Daños</div>
            <div class="prob-bar-track"><div class="prob-bar-fill" style="width:${pD}%;background:var(--c-accent)"></div></div>
            <div class="prob-bar-val">${pD.toFixed(1)}%</div>
          </div>
          <div class="prob-bar-row">
            <div class="prob-bar-label">Con Heridos</div>
            <div class="prob-bar-track"><div class="prob-bar-fill" style="width:${pH}%;background:var(--c-warn)"></div></div>
            <div class="prob-bar-val">${pH.toFixed(1)}%</div>
          </div>
          <div class="prob-bar-row">
            <div class="prob-bar-label">Con Muertos</div>
            <div class="prob-bar-track"><div class="prob-bar-fill" style="width:${pM}%;background:var(--c-danger)"></div></div>
            <div class="prob-bar-val">${pM.toFixed(1)}%</div>
          </div>
        </div>
      </div>
    </div>
    ${actionHtml}`;
}
