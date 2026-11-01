/*
  Property explorer: tower -> floor plan -> room.
  All content comes from data/property.js; this file shouldn't need editing.
*/
(() => {
  "use strict";

  const P = window.PROPERTY;
  const $ = (sel, el = document) => el.querySelector(sel);
  const SVGNS = "http://www.w3.org/2000/svg";

  const viewport = $("#viewport");
  const ui = $("#ui");
  const card = $("#floorCard");
  const hint = $("#hint");
  const loadingBar = $("#loadingBar");
  const topbar = $(".topbar");

  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const noHover = matchMedia("(hover: none)");
  const calibrate = new URLSearchParams(location.search).has("calibrate");

  const STATUS = { available: "Available", reserved: "Reserved", sold: "Sold", ...P.statusLabels };
  const DEPTH = { tower: 0, plan: 1, room: 2 };

  // ------------------------------------------------------------------ helpers

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const num = n => Number(n).toLocaleString("en-US");
  const esc = s => String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const currency = P.currency &&
    new Intl.NumberFormat(P.locale || "en-US", { style: "currency", currency: P.currency, maximumFractionDigits: 0 });

  function money(v) {
    if (v == null || v === "") return "";
    if (typeof v === "string") return v;
    if (currency) return currency.format(v);
    const trim = n => n.toFixed(2).replace(/\.?0+$/, "");
    if (v >= 1e6) return `$${trim(v / 1e6)}M`;
    if (v >= 1e3) return `$${Math.round(v / 1e3)}K`;
    return `$${v}`;
  }

  // ------------------------------------------------------------------ data

  // A floor holds one residence type (with room renders), a plate of individual
  // apartments (P.apartments), or neither: then it only shows its status.
  const residences = P.residences || {};
  const plates = P.plates || {};

  const floorInfo = new Map();
  for (const entry of P.floors) {
    const [lo, hi] = entry.floors || [entry.floor, entry.floor];
    for (let f = lo; f <= hi; f++) {
      const merged = { ...floorInfo.get(f), ...entry };
      delete merged.floors;
      delete merged.floor;
      floorInfo.set(f, merged);
    }
  }
  for (const [f, info] of floorInfo) {
    const missing = info.plate ? !plates[info.plate] && `plate "${info.plate}"`
      : info.residence && !residences[info.residence] && `residence "${info.residence}"`;
    if (missing) {
      console.warn(`Floor ${f}: unknown ${missing} in the property data`);
      floorInfo.delete(f);
    }
  }

  const aptsByFloor = new Map();
  for (const apt of P.apartments || []) {
    apt.id = apt.unit.toLowerCase().replace(/[^a-z0-9]+/g, "");
    apt.name = apt.name || `Apartment ${apt.unit}`;
    apt.status = apt.status || "available";
    if (!aptsByFloor.has(apt.floor)) aptsByFloor.set(apt.floor, []);
    aptsByFloor.get(apt.floor).push(apt);
  }

  const lowest = apts => (apts.length ? Math.min(...apts.map(a => a.price)) : null);

  function unitAt(floor) {
    const info = floorInfo.get(floor);
    if (!info) return null;
    const res = residences[info.residence];
    const plate = plates[info.plate];
    const apts = plate ? aptsByFloor.get(floor) || [] : null;
    const open = apts ? apts.filter(a => a.status === "available") : [];
    const status = info.status || (apts && !open.length ? "sold" : "available");
    return {
      floor,
      res,
      plate,
      apts,
      open,
      note: info.note,
      status,
      statusKey: statusKey(status),
      priceFrom: info.priceFrom ?? (apts ? lowest(open) : res && res.priceFrom),
      towerClip: info.towerClip ?? (plate || res || {}).towerClip,
    };
  }

  const canEnter = unit => !!unit && (unit.apts ? unit.apts.length > 0 : !!unit.res);
  const planOf = unit => unit.plate || unit.res.plan;
  const roomOf = (unit, id) => (unit.apts || unit.res.rooms).find(r => r.id === id);
  const placeName = unit => (unit.apts ? `Floor ${unit.floor}` : unit.res.name);
  const statusKey = status => (STATUS[status] ? status : "other");
  const statusLabel = item => STATUS[item.status] || item.status;
  const showsPrice = unit => unit.status !== "sold" && unit.priceFrom != null && unit.priceFrom !== "";
  const area = m2 => `${num(m2)} m²`;

  function layoutRange(apts) {
    const layouts = [...new Set(apts.map(a => a.layout).filter(Boolean))].sort();
    return layouts.length > 1 ? `${layouts[0]} – ${layouts[layouts.length - 1]}` : layouts[0] || "";
  }

  function unitName(unit) {
    if (unit.apts) return `${unit.apts.length} apartments`;
    return unit.res ? unit.res.name : statusLabel(unit);
  }

  function unitMeta(unit) {
    if (unit.apts) return `${layoutRange(unit.apts)} · ${unit.open.length} available`;
    if (!unit.res) return unit.note || "";
    const res = unit.res;
    return `${res.beds} Bed · ${res.baths} Bath · ${num(res.sqft)} SF`;
  }

  function priceLine(unit) {
    return showsPrice(unit) ? `${statusLabel(unit)} · From ${money(unit.priceFrom)}` : statusLabel(unit);
  }

  // ------------------------------------------------------------------ routing

  function parseHash() {
    const m = location.hash.match(/^#\/floor\/(\d+)(?:\/([\w-]+))?/);
    const unit = m && unitAt(Number(m[1]));
    if (!canEnter(unit)) return { view: "tower" };
    if (m[2] && roomOf(unit, m[2])) return { view: "room", floor: unit.floor, room: m[2] };
    return { view: "plan", floor: unit.floor };
  }

  function href(s) {
    if (s.view === "tower") return "#/";
    if (s.view === "plan") return `#/floor/${s.floor}`;
    return `#/floor/${s.floor}/${s.room}`;
  }

  function titleFor(s) {
    const base = `${P.name} — ${P.location}`;
    if (s.view === "tower") return base;
    const unit = unitAt(s.floor);
    if (s.view === "plan") return `${unit.apts ? "" : `${unit.res.name}, `}Floor ${s.floor} — ${P.name}`;
    return `${roomOf(unit, s.room).name} · ${placeName(unit)} — ${P.name}`;
  }

  // ------------------------------------------------------------------ scenes & layout

  function sceneFor(s) {
    if (s.view === "tower") {
      return { image: P.tower.image, size: P.tower.size, focus: P.tower.focus, alt: `${P.name} tower` };
    }
    const unit = unitAt(s.floor);
    const plan = planOf(unit);
    // Apartment floors keep the plan on screen; picking an apartment only changes the panel.
    if (s.view === "plan" || unit.apts) {
      return { image: plan.image, size: plan.size, frame: plan.frame, focus: plan.focus, plan: true,
               alt: `${placeName(unit)} floor plan` };
    }
    const room = roomOf(unit, s.room);
    return { image: room.image, size: room.size, focus: room.focus, alt: `${room.name}, ${unit.res.name}` };
  }

  const isNarrow = () => viewport.clientWidth < 900 || viewport.clientWidth < viewport.clientHeight;

  // Screen area a scene should frame its subject in (plan views leave room for the panel).
  function sceneArea(scene) {
    const vw = viewport.clientWidth, vh = viewport.clientHeight;
    if (!scene.plan) return { x: 0, y: 0, w: vw, h: vh };
    const top = topbar.offsetHeight;
    if (isNarrow()) return { x: 0, y: top, w: vw, h: vh * 0.56 - top };
    const panel = clamp(vw * 0.26, 300, 380) + 64;
    return { x: 24, y: top, w: vw - panel - 48, h: vh - top - 56 };
  }

  // Cover the viewport, shrinking only if the scene's frame wouldn't fit its area.
  function layout(scene) {
    const [W, H] = scene.size || P.mediaSize;
    const vw = viewport.clientWidth, vh = viewport.clientHeight;
    const area = sceneArea(scene);
    let s = Math.max(vw / W, vh / H);
    let cx, cy;
    if (scene.frame) {
      const [x0, y0, x1, y1] = scene.frame;
      s = Math.min(s, area.w / ((x1 - x0) * W), area.h / ((y1 - y0) * H));
      cx = (x0 + x1) / 2;
      cy = (y0 + y1) / 2;
    } else {
      [cx, cy] = scene.focus || [0.5, 0.5];
    }
    const w = W * s, h = H * s;
    let x = area.x + area.w / 2 - cx * w;
    let y = area.y + area.h / 2 - cy * h;
    if (w >= vw) x = clamp(x, vw - w, 0);
    if (h >= vh) y = clamp(y, vh - h, 0);
    return { x, y, w, h, covers: w >= vw - 1 && h >= vh - 1 };
  }

  function place(el, r) {
    Object.assign(el.style, { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` });
    el.classList.toggle("is-inset", !r.covers);
  }

  function makeLayer(state) {
    const scene = sceneFor(state);
    const el = document.createElement("div");
    el.className = `layer layer--${state.view}`;
    const img = new Image();
    img.className = "layer-img";
    img.alt = scene.alt;
    img.draggable = false;
    img.src = scene.image;
    el.append(img);
    el._scene = scene;
    el._state = state;
    const unit = state.view === "tower" ? null : unitAt(state.floor);
    if (!unit) buildFloors(el, scene);
    else if (unit.apts) buildApartments(el, unit, scene);
    else if (state.view === "plan") buildHotspots(el, unit);
    place(el, layout(scene));
    return el;
  }

  // ------------------------------------------------------------------ tower floors

  function floorQuad(f) {
    const { outline: o, floors: [bottom, top] } = P.tower;
    const n = top - bottom + 1;
    const t0 = (top - f) / n, t1 = (top - f + 1) / n;
    return [lerp(o.topLeft, o.bottomLeft, t0), lerp(o.topRight, o.bottomRight, t0),
            lerp(o.topRight, o.bottomRight, t1), lerp(o.topLeft, o.bottomLeft, t1)];
  }

  const centroid = pts => [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];

  function buildFloors(layer, scene) {
    const [W, H] = scene.size || P.mediaSize;
    const [bottom, top] = P.tower.floors;
    const svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("class", "floors");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");
    for (const f of [...floorInfo.keys()].sort((a, b) => b - a)) {
      if (f < bottom || f > top) continue;
      const unit = unitAt(f);
      const q = floorQuad(f);
      const poly = document.createElementNS(SVGNS, "polygon");
      poly.setAttribute("points", q.map(([x, y]) => `${x * W},${y * H}`).join(" "));
      poly.setAttribute("class", `floor is-${unit.statusKey}${canEnter(unit) ? "" : " is-closed"}`);
      poly.setAttribute("tabindex", "0");
      poly.setAttribute("role", "button");
      poly.setAttribute("aria-label", `Floor ${f}, ${unitName(unit)}, ${priceLine(unit)}`);
      poly.dataset.floor = f;
      svg.append(poly);
      if (calibrate) {
        const t = document.createElementNS(SVGNS, "text");
        t.setAttribute("class", "floor-num");
        t.setAttribute("x", q[1][0] * W + 8);
        t.setAttribute("y", centroid(q)[1] * H + 4);
        t.textContent = f;
        svg.append(t);
      }
    }
    layer.append(svg);
    wireTower(svg);
  }

  let hovered = null;  // floor shown in the card
  let pinned = false;  // touch: first tap pins the card, second tap enters
  let lastPointer = "mouse";
  addEventListener("pointerdown", e => { lastPointer = e.pointerType; }, true);

  function wireTower(svg) {
    const floorOf = e => {
      const el = e.target.closest && e.target.closest("[data-floor]");
      return el ? Number(el.dataset.floor) : null;
    };
    svg.addEventListener("pointerover", e => {
      const f = floorOf(e);
      if (e.pointerType === "mouse" && f) showFloor(f);
    });
    svg.addEventListener("pointerout", e => {
      if (e.pointerType !== "mouse" || pinned) return;
      const to = e.relatedTarget;
      if (!(to && to.closest && to.closest("[data-floor]"))) hideFloor();
    });
    svg.addEventListener("click", e => {
      const f = floorOf(e);
      if (!f) return hideFloor();
      if (lastPointer === "mouse" || (pinned && hovered === f)) return enter(f);
      pinned = true;
      showFloor(f);
    });
    svg.addEventListener("keydown", e => {
      const f = floorOf(e);
      if (!f) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        enter(f);
      } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        const next = svg.querySelector(`[data-floor="${f + (e.key === "ArrowUp" ? 1 : -1)}"]`);
        if (next) next.focus();
      }
    });
    svg.addEventListener("focusin", e => {
      const f = floorOf(e);
      if (f && lastPointer === "mouse") showFloor(f);
    });
    svg.addEventListener("focusout", e => {
      if (!pinned && !svg.contains(e.relatedTarget)) hideFloor();
    });
  }

  function showFloor(f) {
    if (!currentLayer || currentLayer._state.view !== "tower") return;
    const poly = currentLayer.querySelector(`[data-floor="${f}"]`);
    if (!poly) return;
    currentLayer.querySelectorAll(".floor.is-active").forEach(p => p.classList.remove("is-active"));
    poly.classList.add("is-active");
    hovered = f;
    const unit = unitAt(f);
    card.innerHTML = `
      <div class="fc-floor"><span>Floor</span><b>${f}</b></div>
      <div class="fc-body">
        <p class="fc-name">${esc(unitName(unit))}</p>
        <p class="fc-meta">${esc(unitMeta(unit))}</p>
        ${canEnter(unit) ? `
        <p class="fc-status is-${unit.statusKey}">${esc(priceLine(unit))}</p>
        <button class="btn btn-solid fc-go" type="button">Explore ${unit.apts ? "floor" : "residence"} <span aria-hidden="true">→</span></button>` : ""}
      </div>`;
    card.classList.toggle("is-pinned", pinned);
    const entering = card.hidden;
    card.hidden = false;
    card.classList.toggle("no-anim", entering);
    positionCard(poly);
    if (entering) {
      void card.offsetWidth;
      card.classList.remove("no-anim");
    }
    prefetchUnit(unit);
  }

  function positionCard(poly) {
    const r = poly.getBoundingClientRect();
    const vw = innerWidth, vh = innerHeight;
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const gap = 48, m = 16, minY = topbar.offsetHeight + 8;
    const mid = r.top + r.height / 2;
    let side = "right";
    let x = r.right + gap;
    let y = mid - ch / 2;
    if (x + cw > vw - m) {
      side = "left";
      x = r.left - gap - cw;
    }
    if (x < m) {  // no room beside the tower: stack above or below the floor
      side = r.top - ch - 16 > minY ? "above" : "below";
      x = clamp(r.left + r.width / 2 - cw / 2, m, vw - cw - m);
      y = side === "above" ? r.top - ch - 16 : r.bottom + 16;
    }
    y = clamp(y, minY, vh - ch - m);
    card.dataset.side = side;
    card.style.setProperty("--gap", `${gap}px`);
    card.style.setProperty("--ly", `${clamp(mid - y, 12, ch - 12)}px`);
    card.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
  }

  function hideFloor() {
    hovered = null;
    pinned = false;
    card.hidden = true;
    if (currentLayer) currentLayer.querySelectorAll(".floor.is-active").forEach(p => p.classList.remove("is-active"));
  }

  function enter(f) {
    if (canEnter(unitAt(f))) go({ view: "plan", floor: f });
  }

  card.addEventListener("click", e => {
    if (e.target.closest(".fc-go") && hovered != null) enter(hovered);
  });

  // ------------------------------------------------------------------ plan hotspots

  function buildHotspots(layer, unit) {
    const wrap = document.createElement("div");
    wrap.className = "hotspots";
    for (const room of unit.res.rooms) {
      const a = document.createElement("a");
      a.className = "hotspot";
      a.href = href({ view: "room", floor: unit.floor, room: room.id });
      a.dataset.room = room.id;
      a.style.left = `${room.hotspot[0] * 100}%`;
      a.style.top = `${room.hotspot[1] * 100}%`;
      a.innerHTML = `<span class="hotspot-dot" aria-hidden="true"></span><span class="hotspot-label">${esc(room.name)}</span>`;
      a.addEventListener("pointerenter", () => prefetchRoom(room));
      wrap.append(a);
    }
    layer.append(wrap);
  }

  // ------------------------------------------------------------------ plan apartments

  const aptKey = apt => statusKey(apt.status);

  function buildApartments(layer, unit, scene) {
    const [W, H] = scene.size || P.mediaSize;
    const svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("class", "apts");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");
    for (const apt of unit.apts) {
      const shape = unit.plate.slots[apt.slot];
      if (!shape) {
        console.warn(`${apt.unit}: no slot "${apt.slot}" on the floor plate`);
        continue;
      }
      const pts = shape.map(([x, y]) => [x * W, y * H]);
      const [cx, cy] = centroid(pts);
      const a = document.createElementNS(SVGNS, "a");
      a.setAttribute("href", href({ view: "room", floor: unit.floor, room: apt.id }));
      a.setAttribute("class", `apt is-${aptKey(apt)}`);
      a.setAttribute("aria-label", `${apt.name}, ${apt.layout ? `${apt.layout}, ${area(apt.area)}, ` : ""}${statusLabel(apt)}`);
      a.dataset.room = apt.id;
      a.innerHTML = `<polygon points="${pts.map(p => p.join(",")).join(" ")}"/>`
        + `<text class="apt-num" x="${cx}" y="${apt.layout ? cy - 4 : cy + 8}">${esc(apt.unit)}</text>`
        + (apt.layout ? `<text class="apt-layout" x="${cx}" y="${cy + 22}">${esc(apt.layout)}</text>` : "");
      svg.append(a);
    }
    layer.append(svg);
  }

  function floorSummary(unit) {
    const sizes = unit.apts.filter(a => a.area).map(a => a.area);
    const aptHref = a => href({ view: "room", floor: unit.floor, room: a.id });
    return `
      <p class="eyebrow">Floor ${unit.floor} · <span class="status is-${unit.statusKey}">${unit.open.length} of ${unit.apts.length} available</span></p>
      <h1 class="panel-title">Floor ${unit.floor}</h1>
      <div class="stats">
        <div><b>${unit.apts.length}</b><span>Apartments</span></div>
        <div><b>${unit.open.length}</b><span>Available</span></div>
        <div><b>${sizes.length ? `${Math.round(Math.min(...sizes))}–${Math.round(Math.max(...sizes))}` : "–"}</b><span>m²</span></div>
      </div>
      ${showsPrice(unit) ? `<p class="price"><span>From</span>${esc(money(unit.priceFrom))}</p>` : ""}
      <ul class="apt-list">
        ${unit.apts.map(a => `
          <li><a href="${aptHref(a)}" data-room="${esc(a.id)}">
            <b>${esc(a.unit)}</b>
            <span class="apt-meta">${a.layout ? esc(a.layout) : ""}</span>
            <span class="apt-meta">${a.area ? esc(area(a.area)) : ""}</span>
            <span class="apt-end is-${aptKey(a)}">${esc(a.status === "available" && a.price ? money(a.price) : statusLabel(a))}</span>
          </a></li>`).join("")}
      </ul>`;
  }

  function aptDetail(unit, apt) {
    const open = apt.status === "available";
    const facts = [
      apt.facing && ["Facing", apt.facing],
      apt.outdoor > 0 && ["Balcony or terrace", area(apt.outdoor)],
      open && apt.price && apt.area && ["Price per m²", money(Math.round(apt.price / apt.area))],
    ].filter(Boolean);
    const note = apt.layout ? P.aptNote : P.soldNote;
    return `
      <p class="eyebrow">Floor ${unit.floor} · <span class="status is-${aptKey(apt)}">${esc(statusLabel(apt))}</span></p>
      <h1 class="panel-title">${esc(apt.name)}</h1>
      ${apt.layout ? `
      <div class="stats">
        <div><b>${esc(apt.layout)}</b><span>Layout</span></div>
        <div><b>${esc(num(apt.area))}</b><span>m² inside</span></div>
        <div><b>${apt.outdoor > 0 ? esc(num(apt.outdoor)) : "–"}</b><span>m² outside</span></div>
      </div>` : ""}
      ${open && apt.price ? `<p class="price"><span>Price</span>${esc(money(apt.price))}</p>` : ""}
      ${facts.length ? `<dl class="facts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>` : ""}
      ${note ? `<p class="desc">${esc(note)}</p>` : ""}`;
  }

  function renderApartments(state, unit) {
    const apt = state.view === "room" ? roomOf(unit, state.room) : null;
    currentLayer.querySelectorAll(".apt").forEach(el => el.classList.toggle("is-selected", !!apt && el.dataset.room === apt.id));
    const back = apt
      ? `<a class="btn btn-ghost" href="${href({ view: "plan", floor: unit.floor })}">Back to floor</a>`
      : `<a class="btn btn-ghost" href="#/">Back to tower</a>`;
    const link = apt && apt.status === "available" && P.aptLink
      ? { href: P.aptLink.href(apt), label: P.aptLink.label }
      : P.source;
    const more = link
      ? `<a class="btn btn-solid" href="${esc(link.href)}" target="_blank" rel="noopener">${esc(link.label)}</a>`
      : `<button class="btn btn-solid" type="button" data-lead="plan">Request details</button>`;
    ui.innerHTML = `
      <aside class="panel" aria-label="${esc(apt ? apt.name : `Floor ${unit.floor}`)}">
        ${apt ? aptDetail(unit, apt) : floorSummary(unit)}
        <div class="actions">${back}${more}</div>
        ${P.source && P.source.note ? `<p class="source">${esc(P.source.note)}</p>` : ""}
      </aside>`;
  }

  // ------------------------------------------------------------------ scene UI

  function renderUI(state) {
    document.body.dataset.view = state.view;
    hint.hidden = state.view !== "tower";
    if (state.view === "tower") {
      ui.innerHTML = "";
      return;
    }
    const unit = unitAt(state.floor);
    const roomHref = r => href({ view: "room", floor: unit.floor, room: r.id });

    if (unit.apts) {
      renderApartments(state, unit);
      return lightOnHover(unit);
    }

    if (state.view === "plan") {
      ui.innerHTML = `
        <aside class="panel" aria-label="${esc(unit.res.name)}">
          <p class="eyebrow">Floor ${unit.floor} · <span class="status is-${unit.statusKey}">${esc(statusLabel(unit))}</span></p>
          <h1 class="panel-title">${esc(unit.res.name)}</h1>
          <div class="stats">
            <div><b>${esc(unit.res.beds)}</b><span>Bedrooms</span></div>
            <div><b>${esc(unit.res.baths)}</b><span>Baths</span></div>
            <div><b>${esc(num(unit.res.sqft))}</b><span>Sq ft</span></div>
          </div>
          ${showsPrice(unit) ? `<p class="price"><span>From</span>${esc(money(unit.priceFrom))}</p>` : ""}
          ${unit.res.description ? `<p class="desc">${esc(unit.res.description)}</p>` : ""}
          <ul class="room-list">
            ${unit.res.rooms.map(r => `
              <li><a href="${roomHref(r)}" data-room="${esc(r.id)}">
                <span class="room-dot" aria-hidden="true"></span>${esc(r.name)}<span class="room-arrow" aria-hidden="true">→</span>
              </a></li>`).join("")}
          </ul>
          <div class="actions">
            <a class="btn btn-ghost" href="#/">Back to tower</a>
            <button class="btn btn-solid" type="button" data-lead="plan">Request floor plan</button>
          </div>
        </aside>`;
      return lightOnHover(unit);
    }

    const room = roomOf(unit, state.room);
    ui.innerHTML = `
      <div class="room-bar">
        <a class="btn btn-ghost room-back" href="${href({ view: "plan", floor: unit.floor })}">Back to floor plan</a>
        <div class="room-caption">
          <p class="eyebrow">Floor ${unit.floor} · ${esc(unit.res.name)}</p>
          <h1 class="room-title">${esc(room.name)}</h1>
        </div>
        <nav class="room-tabs" aria-label="Rooms">
          ${unit.res.rooms.map(r => `<a href="${roomHref(r)}"${r.id === room.id ? ' aria-current="page"' : ""}>${esc(r.name)}</a>`).join("")}
        </nav>
      </div>`;
  }

  // Hovering a list entry lights its marker on the plan.
  function lightOnHover(unit) {
    ui.querySelectorAll("a[data-room]").forEach(a => {
      const spot = () => currentLayer && currentLayer.querySelector(`[data-room="${a.dataset.room}"]`);
      const on = () => { const s = spot(); if (s) s.classList.add("is-lit"); prefetchRoom(roomOf(unit, a.dataset.room)); };
      const off = () => { const s = spot(); if (s) s.classList.remove("is-lit"); };
      a.addEventListener("pointerenter", on);
      a.addEventListener("pointerleave", off);
      a.addEventListener("focus", on);
      a.addEventListener("blur", off);
    });
  }

  // ------------------------------------------------------------------ preloading

  const imgCache = new Map();
  function preload(src) {
    if (!src) return Promise.resolve();
    if (!imgCache.has(src)) {
      const img = new Image();
      img.src = src;
      imgCache.set(src, img.decode().catch(() => {}));
    }
    return imgCache.get(src);
  }

  // Resolves to a playable URL: a blob once downloaded, the raw URL if fetch isn't
  // possible (e.g. opened from file://), or null if the clip doesn't exist.
  const clipCache = new Map();
  function clipSource(url) {
    if (!clipCache.has(url)) {
      clipCache.set(url, fetch(url)
        .then(r => (r.ok ? r.blob().then(b => URL.createObjectURL(b)) : null))
        .catch(() => url));
    }
    return clipCache.get(url);
  }

  function prefetchUnit(unit) {
    if (!canEnter(unit)) return;
    preload(planOf(unit).image);
    if (unit.towerClip && !reducedMotion.matches) clipSource(unit.towerClip);
  }

  function prefetchRoom(room) {
    if (!room) return;
    preload(room.image);
    if (room.clip && !reducedMotion.matches) clipSource(room.clip);
  }

  async function whenLoaded(src) {
    const t = setTimeout(() => loadingBar.classList.add("is-on"), 250);
    await Promise.race([preload(src), wait(8000)]);
    clearTimeout(t);
    loadingBar.classList.remove("is-on");
  }

  // ------------------------------------------------------------------ transitions

  let current = null;
  let currentLayer = null;
  let busy = false;
  let queued = null;

  function go(state) {
    const h = href(state);
    if (location.hash !== h) location.hash = h;
    else route();
  }

  function route() {
    const next = parseHash();
    if (location.hash && location.hash !== href(next)) history.replaceState(null, "", href(next));
    if (busy) {
      queued = next;
      return;
    }
    if (current && href(current) === href(next)) return;
    show(next);
  }

  // Moving between a floor and one of its apartments keeps the same scene.
  const sameScene = (a, b) => a.view !== "tower" && b.view !== "tower" && a.floor === b.floor && !!unitAt(a.floor).apts;

  function show(next) {
    if (!current || !sameScene(current, next)) return transition(next);
    current = next;
    document.title = titleFor(next);
    renderUI(next);
  }

  function kindOf(prev, next) {
    if (prev.view === "tower" || next.view === "tower" || prev.floor === next.floor) {
      if (DEPTH[next.view] > DEPTH[prev.view]) return "in";
      if (DEPTH[next.view] < DEPTH[prev.view]) return "out";
    }
    return "swap";
  }

  // Where the inner (deeper) scene sits inside the outer one, as image fractions.
  function anchor(outer, inner) {
    if (outer.view === "tower") return centroid(floorQuad(inner.floor));
    return roomOf(unitAt(inner.floor), inner.room).hotspot;
  }

  function clipFor(outer, inner, dir) {
    const unit = unitAt(inner.floor);
    if (outer.view === "tower" && inner.view === "plan") return dir === "in" ? unit.towerClip : (unit.plate || unit.res).towerBackClip;
    if (outer.view === "plan" && inner.view === "room") {
      const room = roomOf(unit, inner.room);
      return dir === "in" ? room.clip : room.backClip;
    }
    return null;
  }

  async function transition(next) {
    busy = true;
    const prev = current;
    const old = currentLayer;
    hideFloor();
    ui.classList.add("is-hidden");
    const layer = makeLayer(next);
    await whenLoaded(layer._scene.image);

    try {
      if (!prev) await fadeIn(layer, 700);
      else if (reducedMotion.matches) await crossfade(old, layer, 350, false);
      else {
        const kind = kindOf(prev, next);
        const [outer, inner] = kind === "out" ? [next, prev] : [prev, next];
        const clip = kind === "swap" ? null : clipFor(outer, inner, kind);
        const played = clip ? await playClip(clip, old, layer) : false;
        if (!played) {
          if (kind === "in") await zoomIn(old, layer, anchor(outer, inner));
          else if (kind === "out") await zoomOut(old, layer, anchor(outer, inner));
          else await crossfade(old, layer, 500, true);
        }
      }
    } catch (err) {
      console.error(err);
      if (!layer.isConnected) viewport.append(layer);
    }

    for (const el of [...viewport.children]) if (el !== layer) el.remove();
    current = next;
    currentLayer = layer;
    document.title = titleFor(next);
    renderUI(next);
    ui.classList.remove("is-hidden");
    afterEnter(next);
    busy = false;

    if (queued) {
      const q = queued;
      queued = null;
      if (href(q) !== href(current)) show(q);
    }
  }

  function afterEnter(state) {
    const idle = window.requestIdleCallback || (fn => setTimeout(fn, 400));
    idle(() => {
      if (state.view === "tower") [...Object.values(residences).map(r => r.plan), ...Object.values(plates)].forEach(p => preload(p.image));
      else if (!unitAt(state.floor).apts) unitAt(state.floor).res.rooms.forEach(r => preload(r.image));
    });
  }

  // Leaves the final state as plain styles so later animations start clean.
  function settle(el, anim) {
    el.style.opacity = "";
    el.style.transform = "";
    anim.cancel();
  }

  // Offset that brings an anchor point toward the middle of the screen.
  function towardCenter(layer, [ax, ay]) {
    const r = layer.getBoundingClientRect();
    return [viewport.clientWidth / 2 - (r.left + ax * r.width), viewport.clientHeight / 2 - (r.top + ay * r.height)];
  }

  async function fadeIn(layer, d) {
    layer.style.opacity = "0";
    viewport.append(layer);
    const a = layer.animate([{ opacity: 0, transform: "scale(1.04)" }, { opacity: 1, transform: "scale(1)" }],
      { duration: d, easing: "ease-out", fill: "forwards" });
    await a.finished;
    settle(layer, a);
  }

  async function crossfade(old, layer, d, throughBlack) {
    layer.style.opacity = "0";
    viewport.append(layer);
    if (throughBlack && old) {
      await old.animate([{ opacity: 1 }, { opacity: 0 }], { duration: d * 0.6, easing: "ease-in", fill: "forwards" }).finished;
    }
    const a = layer.animate([{ opacity: 0, transform: "scale(1.03)" }, { opacity: 1, transform: "scale(1)" }],
      { duration: d, easing: "ease-out", fill: "forwards" });
    await a.finished;
    settle(layer, a);
  }

  async function zoomIn(old, layer, [ax, ay]) {
    const [dx, dy] = towardCenter(old, [ax, ay]);
    old.style.transformOrigin = `${ax * 100}% ${ay * 100}%`;
    layer.style.opacity = "0";
    viewport.append(layer);
    const d = 1150;
    const a1 = old.animate([
      { transform: "none", opacity: 1 },
      { opacity: 1, offset: 0.55 },
      { transform: `translate(${dx}px, ${dy}px) scale(3.2)`, opacity: 0 },
    ], { duration: d, easing: "cubic-bezier(.55,0,.3,1)", fill: "forwards" });
    const a2 = layer.animate([
      { transform: "scale(1.14)", opacity: 0 },
      { opacity: 0, offset: 0.42 },
      { transform: "scale(1)", opacity: 1 },
    ], { duration: d, easing: "cubic-bezier(.3,0,.2,1)", fill: "forwards" });
    await Promise.all([a1.finished, a2.finished]);
    settle(layer, a2);
  }

  async function zoomOut(old, layer, [ax, ay]) {
    layer.style.opacity = "0";
    viewport.append(layer);
    const [dx, dy] = towardCenter(layer, [ax, ay]);
    layer.style.transformOrigin = `${ax * 100}% ${ay * 100}%`;
    const d = 1050;
    const a1 = old.animate([{ transform: "none", opacity: 1 }, { transform: "scale(.9)", opacity: 0 }],
      { duration: d * 0.55, easing: "ease-in", fill: "forwards" });
    const a2 = layer.animate([
      { transform: `translate(${dx}px, ${dy}px) scale(2.8)`, opacity: 0 },
      { opacity: 0.7, offset: 0.35 },
      { transform: "none", opacity: 1 },
    ], { duration: d, easing: "cubic-bezier(.2,.7,.2,1)", fill: "forwards" });
    await Promise.all([a1.finished, a2.finished]);
    settle(layer, a2);
    layer.style.transformOrigin = "";
  }

  // Plays a pre-rendered clip between two stills. Returns false if it can't play,
  // so the caller falls back to the zoom.
  async function playClip(url, old, layer) {
    const src = await clipSource(url);
    if (!src) return false;
    const video = document.createElement("video");
    video.className = "layer layer--clip";
    video.muted = true;
    video.playsInline = true;
    video.preload = "auto";
    video.setAttribute("muted", "");
    video.setAttribute("playsinline", "");
    const r0 = layout(old._scene), r1 = layout(layer._scene);
    place(video, r0);
    video.style.opacity = "0";
    video.src = src;
    viewport.append(video);

    const ready = await new Promise(res => {
      const t = setTimeout(() => res(false), 4000);
      video.addEventListener("canplay", () => { clearTimeout(t); res(true); }, { once: true });
      video.addEventListener("error", () => { clearTimeout(t); res(false); }, { once: true });
    });
    if (!ready) {
      video.remove();
      return false;
    }
    try {
      await video.play();
    } catch {
      video.remove();
      return false;
    }
    video.style.opacity = "1";
    old.style.opacity = "0";
    layer.style.opacity = "0";
    viewport.insertBefore(layer, video);

    // Drift from the source framing to the destination framing while the clip plays.
    const dur = (Number.isFinite(video.duration) ? video.duration : 4) * 1000;
    if (r0.x !== r1.x || r0.y !== r1.y || r0.w !== r1.w || r0.h !== r1.h) {
      video.style.transformOrigin = "0 0";
      video.animate([
        { transform: "none" },
        { transform: `translate(${r1.x - r0.x}px, ${r1.y - r0.y}px) scale(${r1.w / r0.w}, ${r1.h / r0.h})` },
      ], { duration: dur, easing: "ease-in-out", fill: "forwards" });
    }
    await new Promise(res => {
      const t = setTimeout(res, dur + 1500);
      video.addEventListener("ended", () => { clearTimeout(t); res(); }, { once: true });
      video.addEventListener("error", () => { clearTimeout(t); res(); }, { once: true });
    });
    layer.style.opacity = "";
    await video.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 240, fill: "forwards" }).finished;
    video.remove();
    return true;
  }

  // ------------------------------------------------------------------ lead form

  const lead = $("#lead");
  const leadForm = $("#leadForm");
  const leadStatus = $("#leadStatus");
  const leadSubmit = $(".lead-submit", leadForm);

  function say(text, tone) {
    leadStatus.textContent = text;
    leadStatus.className = `lead-status${tone ? ` is-${tone}` : ""}`;
  }

  function openLead(kind) {
    const unit = current && current.view !== "tower" ? unitAt(current.floor) : null;
    const forPlan = kind === "plan" && unit;
    const place = forPlan && (unit.apts ? `Floor ${unit.floor}` : `${unit.res.name}, Floor ${unit.floor}`);
    $("#leadEyebrow").textContent = forPlan ? place : P.name;
    $("#leadTitle").textContent = forPlan ? "Request the floor plan" : "Request a private tour";
    leadForm.elements.interest.value = forPlan ? `Floor plan: ${place}` : "Private tour";
    say("");
    leadSubmit.disabled = false;
    lead.showModal();
  }

  document.addEventListener("click", e => {
    const trigger = e.target.closest("[data-lead]");
    if (trigger) openLead(trigger.dataset.lead);
  });
  $("#leadClose").addEventListener("click", () => lead.close());
  lead.addEventListener("click", e => { if (e.target === lead) lead.close(); });

  leadForm.addEventListener("submit", async e => {
    e.preventDefault();
    const data = new FormData(leadForm);
    const { endpoint, email } = P.leads || {};
    if (endpoint) {
      leadSubmit.disabled = true;
      say("Sending…");
      try {
        const r = await fetch(endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        say("Thank you. We'll be in touch shortly.", "ok");
        leadForm.reset();
      } catch (err) {
        console.error(err);
        say("Sorry, that didn't go through. Please try again.", "error");
        leadSubmit.disabled = false;
      }
    } else if (email) {
      const body = [...data].filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join("\n");
      const subject = `${data.get("interest")} — ${P.name}`;
      location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      say("Your email app should open with the request filled in.", "ok");
    } else {
      say("This form isn't connected yet. Set leads.endpoint or leads.email in data/property.js.", "error");
    }
  });

  // ------------------------------------------------------------------ setup

  function setupChrome() {
    document.title = titleFor({ view: "tower" });
    const mark = $("#brandMark");
    if (P.logo) {
      const img = new Image();
      img.src = P.logo;
      img.alt = "";
      mark.append(img);
      mark.classList.add("has-logo");
    } else {
      mark.textContent = P.mark || P.name.charAt(0);
    }
    $("#brandName").textContent = P.name;
    $("#brandLoc").textContent = P.location;
    $("#legal").textContent = P.legal || "";
    $("#hintText").textContent = noHover.matches ? "Tap a floor to explore" : "Hover a floor to explore";
    const cta = P.cta || {};
    $("#nav").innerHTML = (P.nav || []).map(n => `<a class="nav-link" href="${esc(n.href)}">${esc(n.label)}</a>`).join("")
      + (cta.href
        ? `<a class="btn btn-solid nav-cta" href="${esc(cta.href)}" target="_blank" rel="noopener">${esc(cta.label || "Contact")}</a>`
        : `<button class="btn btn-solid nav-cta" type="button" data-lead="tour">${esc(cta.label || "Private Tour")}</button>`);

    const icon = document.createElement("link");
    icon.rel = "icon";
    icon.href = "data:image/svg+xml," + encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#0a0f1a"/>`
      + `<rect x="9" y="9" width="46" height="46" fill="none" stroke="#d9c59d" stroke-width="3"/>`
      + `<text x="32" y="43" text-anchor="middle" font-family="Georgia,serif" font-size="30" fill="#f3ede3">${esc(P.mark || P.name.charAt(0))}</text></svg>`);
    document.head.append(icon);
  }

  function setupCalibration() {
    if (!calibrate) return;
    document.body.classList.add("is-calibrating");
    const out = $("#calib");
    out.hidden = false;
    out.textContent = "Move over the image to read coordinates";
    let last = "";
    viewport.addEventListener("pointermove", e => {
      if (!currentLayer) return;
      const r = currentLayer.getBoundingClientRect();
      last = `[${((e.clientX - r.left) / r.width).toFixed(3)}, ${((e.clientY - r.top) / r.height).toFixed(3)}]`;
      out.textContent = `${last}  ·  press C to copy`;
    });
    addEventListener("keydown", e => {
      if (e.key.toLowerCase() !== "c" || !last || e.target.closest("input, textarea")) return;
      if (navigator.clipboard) navigator.clipboard.writeText(last).then(() => { out.textContent = `${last}  ·  copied`; });
    });
  }

  let resizeFrame = 0;
  addEventListener("resize", () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      viewport.querySelectorAll(".layer").forEach(el => { if (el._scene) place(el, layout(el._scene)); });
      if (hovered != null && currentLayer) {
        const poly = currentLayer.querySelector(`[data-floor="${hovered}"]`);
        if (poly) positionCard(poly);
      }
    });
  });

  addEventListener("keydown", e => {
    if (e.key !== "Escape" || lead.open) return;
    if (hovered != null) return hideFloor();
    if (current && current.view === "room") go({ view: "plan", floor: current.floor });
    else if (current && current.view === "plan") go({ view: "tower" });
  });

  addEventListener("hashchange", route);
  setupChrome();
  setupCalibration();
  route();
})();
