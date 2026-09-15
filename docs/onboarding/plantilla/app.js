// Comportamiento de «AlejandrIA por dentro». Los datos llegan en DATA, que genera
// scripts/build_onboarding.py a partir de las specs, GitHub y docs/onboarding/*.yaml.
(() => {
  const T = DATA.tareas;
  const BY = Object.fromEntries(T.map(t => [t.id, t]));
  const EPICS = DATA.epicas;
  const SEVS = [["high", "Alta"], ["medium", "Media"], ["low", "Baja"]];
  const SEV_TXT = { high: "Alta", medium: "Media", low: "Baja" };
  const ESTADO_TXT = {
    lista: "Lista para empezar", espera: "Espera a otra tarea",
    hecha: "Hecha, falta cerrar el issue", "sin-issue": "Sin issue: falta /sdd-sync --apply",
  };
  const COLW = { olas: 176, persona: 100 };
  const REDUCE = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const S = {
    modo: "olas", epicas: new Set(EPICS.map(e => e.id)), sevs: new Set(SEVS.map(s => s[0])),
    solo: false, q: "", comp: null, hover: null, sel: null,
  };

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const irA = el => el && el.scrollIntoView({ behavior: REDUCE ? "auto" : "smooth", block: "start" });
  const estrecho = () => window.matchMedia("(max-width: 900px)").matches;

  // ── Grafo (solo tareas abiertas; las cerradas ya no bloquean) ──────────────
  const anc = (id, acc = new Set()) => { for (const d of BY[id].deps) if (BY[d] && !acc.has(d)) { acc.add(d); anc(d, acc); } return acc; };
  const desc = (id, acc = new Set()) => { for (const u of BY[id].unlocks) if (BY[u] && !acc.has(u)) { acc.add(u); desc(u, acc); } return acc; };
  const num = id => (id.match(/\d+/g) || []).map(Number);
  const cmpId = (a, b) => { const x = num(a.id), y = num(b.id); return (x[0] - y[0]) || (x[1] - y[1]); };
  const grupoDe = id => {
    for (let g = 0; g < DATA.reparto.length; g++) {
      const i = DATA.reparto[g].tareas.indexOf(id);
      if (i >= 0) return [g, i];
    }
    return [-1, 0];
  };

  // ── Controles ────────────────────────────────────────────────────────────
  function pintarControles() {
    $("#filtro-epicas").innerHTML = EPICS.map(e => {
      const n = T.filter(t => t.epic === e.id).length;
      return `<button type="button" class="chip-f" data-epica="${e.id}" aria-pressed="${S.epicas.has(e.id)}" title="${esc(e.nombre)}"><span class="mono">${e.id}</span> ${esc(e.corto)} <span class="cuenta">${n}</span></button>`;
    }).join("");
    $("#filtro-sev").innerHTML = SEVS.map(([k, lab]) =>
      `<button type="button" class="chip-f" data-sev="${k}" aria-pressed="${S.sevs.has(k)}"><i class="lg-sev sev-${k}"></i>${lab}</button>`).join("");
    $("#solo-listas").checked = S.solo;
    $("#buscar").value = S.q;
    $$(".seg [data-modo]").forEach(b => b.setAttribute("aria-checked", String(b.dataset.modo === S.modo)));
    const fc = $("#filtro-comp");
    fc.hidden = !S.comp;
    fc.innerHTML = S.comp
      ? `Solo tareas que tocan <strong>${esc(DATA.comps[S.comp].nombre)}</strong> <button type="button" class="btn btn-texto" data-quitar-comp>Quitar filtro</button>`
      : "";
  }

  function visibles() {
    const q = S.q.trim().toLowerCase();
    return T.filter(t => S.epicas.has(t.epic) && S.sevs.has(t.sev)
      && (!S.solo || t.estado === "lista")
      && (!S.comp || t.comps.includes(S.comp))
      && (!q || `${t.id} ${t.title} ${t.short} ${t.files.join(" ")} #${t.n || ""}`.toLowerCase().includes(q)));
  }

  function limpiarFiltros() {
    S.epicas = new Set(EPICS.map(e => e.id)); S.sevs = new Set(SEVS.map(s => s[0]));
    S.solo = false; S.q = ""; S.comp = null;
  }

  // ── Gantt ────────────────────────────────────────────────────────────────
  function render() {
    const vis = visibles();
    const vset = new Set(vis.map(t => t.id));
    const g = $("#gantt");
    let grupos, colOf, etiquetas;
    if (S.modo === "olas") {
      const olas = Math.max(1, ...T.map(t => t.ola + 1));
      etiquetas = Array.from({ length: olas }, (_, i) => i === 0 ? "Ola 1 · sin bloqueos" : `Ola ${i + 1}`);
      colOf = t => t.ola;
      grupos = EPICS.map(e => ({
        titulo: `<span class="mono">${e.id}</span> ${esc(e.nombre)}`,
        sub: e.n ? `<a class="g-enl" href="${DATA.repo}/issues/${e.n}" target="_blank" rel="noopener">#${e.n}</a>` : "",
        tareas: vis.filter(t => t.epic === e.id).sort((a, b) => a.ola - b.ola || cmpId(a, b)),
      }));
    } else {
      const largo = Math.max(1, ...DATA.reparto.map(r => r.tareas.length));
      etiquetas = Array.from({ length: largo }, (_, i) => `Paso ${String(i + 1).padStart(2, "0")}`);
      colOf = t => grupoDe(t.id)[1];
      grupos = DATA.reparto.map(r => ({
        titulo: esc(r.nombre), sub: `<span class="g-sub">${esc(r.foco)}</span>`,
        tareas: r.tareas.filter(id => vset.has(id)).map(id => BY[id]),
      }));
    }
    grupos = grupos.filter(x => x.tareas.length);
    g.dataset.modo = S.modo;
    g.style.setProperty("--col", COLW[S.modo] + "px");
    g.style.setProperty("--ncols", etiquetas.length);

    let h = `<div class="g-fila g-cab"><div class="g-etq">Tarea</div><div class="g-pista">${etiquetas.map(x => `<div class="g-col">${x}</div>`).join("")}</div></div>`;
    for (const gr of grupos) {
      h += `<div class="g-fila g-grupo"><div class="g-etq">${gr.titulo} ${gr.sub}</div><div class="g-pista"></div></div>`;
      for (const t of gr.tareas) {
        const cruce = S.modo === "persona" ? t.deps.filter(d => BY[d] && grupoDe(d)[0] !== grupoDe(t.id)[0]) : [];
        const titulo = `${t.id} · ${t.title}. ${ESTADO_TXT[t.estado]}. Severidad ${SEV_TXT[t.sev].toLowerCase()}.${cruce.length ? " Espera a " + cruce.join(", ") + " de otra persona." : ""}`;
        h += `<div class="g-fila g-tarea" data-id="${t.id}">
          <button type="button" class="g-etq g-etq-t" data-id="${t.id}" aria-label="Abrir ficha de ${t.id}">
            <span class="mono g-tid">${t.id}</span><span class="g-ttl">${esc(t.short)}</span><span class="g-iss mono">${t.n ? "#" + t.n : "sin issue"}</span>
          </button>
          <div class="g-pista">
            <button type="button" class="g-barra st-${t.estado}" data-id="${t.id}" style="--c:${colOf(t)}" title="${esc(titulo)}" aria-label="${esc(titulo)}">
              <span class="mono g-bid">${t.id}</span>${S.modo === "olas" ? `<span class="g-bt">${esc(t.short)}</span>` : ""}
              <span class="g-marcas"><i class="g-sev sev-${t.sev}"></i>${t.sensible ? '<i class="g-rev">R</i>' : ""}</span>
            </button>
          </div>
        </div>`;
      }
    }
    if (!grupos.length) {
      h += `<div class="g-vacio">Ninguna tarea cumple estos filtros. <button type="button" class="btn btn-texto" data-limpiar>Quitar filtros</button></div>`;
    }
    g.innerHTML = h + `<svg class="g-flechas" aria-hidden="true"></svg>`;
    dibujar(vis);
    resaltar();
    $("#gantt-nota").innerHTML = (S.modo === "olas"
      ? "Una tarea cae en la ola siguiente a la última de sus dependencias abiertas. La columna dice cuándo se puede empezar, no cuánto dura."
      : "La columna es el orden del reparto, no la duración. Las flechas que cruzan de un grupo a otro son esperas: esa tarea depende del trabajo de otra persona. El reparto se edita en docs/onboarding/tareas.yaml.")
      + ` <span class="cuenta-vis">Mostrando ${vis.length} de ${T.length} tareas.</span>`;
  }

  function dibujar(vis) {
    const g = $("#gantt");
    const svg = $(".g-flechas", g);
    if (!svg) return;
    const base = g.getBoundingClientRect();
    const W = g.scrollWidth, H = g.scrollHeight;
    svg.setAttribute("width", W); svg.setAttribute("height", H); svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const pos = {};
    $$(".g-barra", g).forEach(b => {
      const r = b.getBoundingClientRect();
      pos[b.dataset.id] = { l: r.left - base.left, r: r.right - base.left, y: r.top - base.top + r.height / 2 };
    });
    let paths = "";
    for (const t of vis) {
      for (const d of t.deps) {
        const a = pos[d], b = pos[t.id];
        if (!a || !b) continue;
        const xm = b.l - 9;
        const dd = a.r + 4 <= xm ? `M${a.r} ${a.y} H${xm} V${b.y} H${b.l}` : `M${a.r} ${a.y} H${a.r + 6} V${b.y} H${b.l}`;
        paths += `<path class="g-flecha" data-de="${d}" data-a="${t.id}" d="${dd}" marker-end="url(#gf)"/>`;
      }
    }
    svg.innerHTML = `<defs>
      <marker id="gf" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" class="gf"/></marker>
      <marker id="gf-on" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" class="gf-on"/></marker>
    </defs>${paths}`;
  }

  function resaltar() {
    const foco = S.hover || S.sel;
    const g = $("#gantt");
    const valido = foco && BY[foco] && $(`.g-tarea[data-id="${foco}"]`, g);
    g.classList.toggle("con-foco", !!valido);
    let arriba = null, abajo = null;
    if (valido) { arriba = anc(foco); arriba.add(foco); abajo = desc(foco); abajo.add(foco); }
    $$(".g-tarea", g).forEach(f => {
      const id = f.dataset.id;
      f.classList.toggle("en-cadena", !!valido && (arriba.has(id) || abajo.has(id)));
      f.classList.toggle("es-foco", id === foco);
      f.classList.toggle("es-sel", id === S.sel);
    });
    $$(".g-flecha", g).forEach(p => {
      const de = p.dataset.de, a = p.dataset.a;
      const on = !!valido && ((arriba.has(de) && arriba.has(a)) || (abajo.has(de) && abajo.has(a)));
      p.classList.toggle("on", on);
      p.setAttribute("marker-end", on ? "url(#gf-on)" : "url(#gf)");
    });
  }

  // ── Ficha de tarea ───────────────────────────────────────────────────────
  let volverFoco = null;
  const cmd = (texto, etiqueta = "") =>
    `<div class="cmd">${etiqueta ? `<span class="cmd-lab">${etiqueta}</span>` : ""}<code>${esc(texto)}</code><button type="button" class="btn btn-mini" data-copiar>Copiar</button></div>`;

  function refLista(ids) {
    return `<ul class="refs">${ids.map(d => {
      if (BY[d]) {
        const e = BY[d].estado;
        return `<li><button type="button" class="tref" data-ir="${d}">${d}</button><span class="tref-t">${esc(BY[d].short)}</span><span class="st-mini st-${e}">${ESTADO_TXT[e]}</span></li>`;
      }
      const c = DATA.cerradas[d];
      return `<li><span class="tref-cerrada">${d}</span><span class="tref-t">${esc(c ? c.title : "")}</span><span class="st-mini st-cerrada">Cerrada${c && c.n ? " · #" + c.n : ""}</span></li>`;
    }).join("")}</ul>`;
  }

  function bloqueEjecutar(t) {
    if (!t.n) {
      return `<div class="ejecutar"><p>Esta tarea está en su spec pero todavía no tiene issue. Sincroniza antes, en Claude Code:</p>${cmd("/sdd-sync")}${cmd("/sdd-sync --apply")}</div>`;
    }
    const abiertas = t.deps.filter(d => BY[d]);
    let aviso = "";
    if (t.estado === "hecha") {
      aviso = `<p class="aviso">Ya está implementada: falta cerrarla por el flujo (PR con su bitácora y <code>Closes #${t.n}</code>). Mientras siga abierta, bloquea a ${t.unlocks.length ? t.unlocks.join(", ") : "sus dependientes"}.</p>`;
    } else if (abiertas.length) {
      aviso = `<p class="aviso"><strong>Todavía no se puede ejecutar.</strong> <code>/resolve-task</code> se detendrá hasta que se cierren: ${abiertas.map(d => `${d}${BY[d].n ? " (#" + BY[d].n + ")" : ""}`).join(", ")}.</p>`;
    }
    return `<div class="ejecutar">
      <p>En Claude Code, desde la raíz del repo:</p>${cmd(`/resolve-task ${t.n}`)}
      <p>O sin sesión interactiva, en Git Bash:</p>${cmd(`bash scripts/run-task.sh ${t.n}`)}
      ${aviso}</div>`;
  }

  function abrir(id, desde) {
    const t = BY[id];
    if (!t) return;
    if (desde) volverFoco = desde;
    S.sel = id;
    const [gi, pi] = grupoDe(id);
    const reparto = gi >= 0 ? `Reparto: ${esc(DATA.reparto[gi].nombre)}, paso ${pi + 1} de ${DATA.reparto[gi].tareas.length}.` : "";
    $("#cajon-id").innerHTML = `<span class="mono">${t.id}</span>${t.n ? `<a href="${DATA.repo}/issues/${t.n}" target="_blank" rel="noopener">Issue #${t.n}</a>` : '<span class="nota">sin issue</span>'}`;
    $("#cajon-cuerpo").innerHTML = `
      <h3>${esc(t.title)}</h3>
      <div class="chips">
        <span class="chip st-${t.estado}">${ESTADO_TXT[t.estado]}</span>
        <span class="chip sevc-${t.sev}">Severidad ${SEV_TXT[t.sev].toLowerCase()}</span>
        ${t.sensible ? `<span class="chip chip-rev">Revisión: ${esc(t.sensible)}</span>` : ""}
      </div>
      <h4>Ejecutarla</h4>${bloqueEjecutar(t)}
      <h4>Alcance</h4><p>${t.alcance}</p>
      <h4>Hecha cuando</h4><ul class="dod">${t.dod.map(x => `<li>${x}</li>`).join("")}</ul>
      <div class="deps2">
        <div><h4>Depende de</h4>${t.deps.length ? refLista(t.deps) : '<p class="nada">Nada: puede empezar ya.</p>'}</div>
        <div><h4>Desbloquea</h4>${t.unlocks.length ? refLista(t.unlocks) : '<p class="nada">Nada: cierra su épica.</p>'}</div>
      </div>
      ${t.cuidado ? `<h4>Ojo con</h4><p class="cuidado">${t.cuidado}</p>` : ""}
      ${t.files.length ? `<h4>Archivos</h4><ul class="archivos">${t.files.map(f => `<li><code>${esc(f)}</code></li>`).join("")}</ul>` : ""}
      ${t.comps.length ? `<h4>Componentes que toca</h4><div class="comps-t">${t.comps.map(c => `<button type="button" class="chip-f" data-vercomp="${c}">${esc(DATA.comps[c].nombre)}</button>`).join("")}</div>` : ""}
      ${t.rama ? `<h4>Rama sugerida</h4>${cmd(t.rama)}` : ""}
      ${reparto ? `<p class="nota">${reparto}</p>` : ""}`;
    const cajon = $("#cajon");
    cajon.hidden = false;
    $("#velo").hidden = !estrecho();
    requestAnimationFrame(() => cajon.classList.add("abierto"));
    $("#cajon-cuerpo").scrollTop = 0;
    $("#cajon-cerrar").focus({ preventScroll: true });
    resaltar();
  }

  function cerrar() {
    const cajon = $("#cajon");
    if (cajon.hidden) return;
    cajon.classList.remove("abierto");
    $("#velo").hidden = true;
    if (REDUCE) cajon.hidden = true; else setTimeout(() => { cajon.hidden = true; }, 200);
    S.sel = null;
    resaltar();
    if (volverFoco && document.contains(volverFoco)) volverFoco.focus({ preventScroll: true });
  }

  function irATarea(id) {
    if (!visibles().some(t => t.id === id)) { limpiarFiltros(); pintarControles(); render(); }
    const fila = $(`.g-tarea[data-id="${id}"]`);
    if (fila) fila.scrollIntoView({ behavior: REDUCE ? "auto" : "smooth", block: "center" });
    abrir(id, fila ? $(".g-barra", fila) : null);
  }

  // ── Arquitectura ─────────────────────────────────────────────────────────
  const tareasDe = c => T.filter(t => t.comps.includes(c));

  function pintarPanel(id) {
    const c = DATA.comps[id];
    const ts = tareasDe(id);
    $("#arq-panel").innerHTML = `
      <p class="panel-capa">${esc(DATA.capas[c.capa])}${c.nuevo ? ' <span class="chip chip-nuevo">por construir</span>' : ""}</p>
      <h3>${esc(c.nombre)}</h3>
      <p class="panel-ruta"><code>${esc(c.ruta)}</code></p>
      <p>${c.que}</p>
      ${c.reglas.length ? `<h4>Reglas que no conviene romper</h4><ul class="reglas">${c.reglas.map(r => `<li>${r}</li>`).join("")}</ul>` : ""}
      ${c.rel.length ? `<h4>Se relaciona con</h4><ul class="rels">${c.rel.map(([to, lab]) => `<li><button type="button" class="rel-btn" data-comp-ir="${to}">${esc(DATA.comps[to].nombre)}</button><span>${esc(lab)}</span></li>`).join("")}</ul>` : ""}
      <h4>Tareas abiertas que lo tocan</h4>
      ${ts.length ? `<ul class="refs">${ts.map(t => `<li><button type="button" class="tref" data-tarea-ir="${t.id}">${t.id}</button><span class="tref-t">${esc(t.short)}</span></li>`).join("")}</ul>
        <button type="button" class="btn" data-filtrar-comp="${id}">Ver solo estas en el diagrama</button>` : '<p class="nada">Ninguna por ahora.</p>'}`;
  }

  function seleccionarComp(id) {
    if (!DATA.comps[id]) return;
    const relacionados = new Set(DATA.comps[id].rel.map(r => r[0]));
    Object.entries(DATA.comps).forEach(([k, v]) => { if (v.rel.some(r => r[0] === id)) relacionados.add(k); });
    $$(".comp").forEach(b => {
      const es = b.dataset.comp === id;
      b.classList.toggle("sel", es);
      b.setAttribute("aria-pressed", String(es));
      b.classList.toggle("rel", !es && relacionados.has(b.dataset.comp));
    });
    pintarPanel(id);
  }

  let pasoActual = -1;
  function pasoRecorrido(i) {
    const R = DATA.recorrido;
    const arq = $(".arq");
    $$(".comp .rec-badge").forEach(x => x.remove());
    if (i < 0 || i >= R.length) {
      pasoActual = -1;
      arq.classList.remove("en-recorrido");
      $$(".comp").forEach(b => b.classList.remove("rec-on"));
      $(".rec-ctl").hidden = true; $("#rec-txt").hidden = true; $("#rec-empezar").hidden = false;
      return;
    }
    pasoActual = i;
    arq.classList.add("en-recorrido");
    $("#rec-empezar").hidden = true; $(".rec-ctl").hidden = false; $("#rec-txt").hidden = false;
    const ids = new Set(R[i].ids);
    $$(".comp").forEach(b => {
      const on = ids.has(b.dataset.comp);
      b.classList.toggle("rec-on", on);
      if (on) { const s = document.createElement("span"); s.className = "rec-badge"; s.textContent = i + 1; b.appendChild(s); }
    });
    $("#rec-cont").textContent = `${i + 1} / ${R.length}`;
    $("#rec-txt").innerHTML = R[i].txt;
    $("#rec-prev").disabled = i === 0;
    $("#rec-next").textContent = i === R.length - 1 ? "Terminar" : "Siguiente";
    seleccionarComp(R[i].ids[0]);
  }

  // ── Pipeline ─────────────────────────────────────────────────────────────
  function agente(id) {
    const a = DATA.agentes.find(x => x.id === id);
    if (!a) return;
    $$(".p-agente").forEach(g => { const es = g.dataset.agente === id; g.classList.toggle("sel", es); g.setAttribute("aria-pressed", String(es)); });
    $("#agente-info").innerHTML = `<h3>${esc(a.nombre)}</h3><p>${esc(a.desc)}</p>
      <dl class="mini-dl">
        <div><dt>Capacidades</dt><dd>${a.requires.map(r => `<code>${esc(r)}</code>`).join(" ")}</dd></div>
        <div><dt>Código</dt><dd><code>backend/app/${esc(a.entry)}</code></dd></div>
        <div><dt>Perfil</dt><dd><code>backend/${esc(a.perfil)}</code></dd></div>
      </dl>`;
  }

  // ── Pestañas de «Cómo trabajar» ──────────────────────────────────────────
  function activarPestana(tab, enfocar) {
    const tabs = $$('.pestanas [role="tab"]');
    tabs.forEach(t => {
      const sel = t === tab;
      t.setAttribute("aria-selected", String(sel));
      t.tabIndex = sel ? 0 : -1;
      $("#" + t.getAttribute("aria-controls")).hidden = !sel;
    });
    if (enfocar) tab.focus();
  }

  // ── Copiar ───────────────────────────────────────────────────────────────
  function copiar(btn) {
    const code = btn.parentElement.querySelector("code");
    if (!code) return;
    const ok = () => { btn.textContent = "Copiado"; setTimeout(() => { btn.textContent = "Copiar"; }, 1500); };
    const manual = () => {
      const r = document.createRange(); r.selectNodeContents(code);
      const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
      btn.textContent = "Ctrl+C";
      setTimeout(() => { btn.textContent = "Copiar"; }, 2500);
    };
    try { navigator.clipboard.writeText(code.textContent).then(ok, manual); } catch (_) { manual(); }
  }

  // ── Eventos ──────────────────────────────────────────────────────────────
  function enlazar() {
    $$(".seg [data-modo]").forEach(b => b.addEventListener("click", () => { S.modo = b.dataset.modo; pintarControles(); render(); }));
    $("#filtro-epicas").addEventListener("click", e => {
      const b = e.target.closest("[data-epica]"); if (!b) return;
      const k = b.dataset.epica; S.epicas.has(k) ? S.epicas.delete(k) : S.epicas.add(k);
      pintarControles(); render();
    });
    $("#filtro-sev").addEventListener("click", e => {
      const b = e.target.closest("[data-sev]"); if (!b) return;
      const k = b.dataset.sev; S.sevs.has(k) ? S.sevs.delete(k) : S.sevs.add(k);
      pintarControles(); render();
    });
    $("#solo-listas").addEventListener("change", e => { S.solo = e.target.checked; render(); });
    $("#buscar").addEventListener("input", e => { S.q = e.target.value; render(); });
    $("#filtro-comp").addEventListener("click", e => { if (e.target.closest("[data-quitar-comp]")) { S.comp = null; pintarControles(); render(); } });

    const g = $("#gantt");
    g.addEventListener("pointerover", e => {
      const f = e.target.closest(".g-tarea"); const id = f ? f.dataset.id : null;
      if (id !== S.hover) { S.hover = id; resaltar(); }
    });
    g.addEventListener("pointerleave", () => { S.hover = null; resaltar(); });
    g.addEventListener("focusin", e => { const f = e.target.closest(".g-tarea"); S.hover = f ? f.dataset.id : null; resaltar(); });
    g.addEventListener("focusout", () => { S.hover = null; resaltar(); });
    g.addEventListener("click", e => {
      if (e.target.closest("[data-limpiar]")) { limpiarFiltros(); pintarControles(); render(); return; }
      const b = e.target.closest("button[data-id]"); if (b) abrir(b.dataset.id, b);
    });

    $("#cajon-cerrar").addEventListener("click", cerrar);
    $("#velo").addEventListener("click", cerrar);
    document.addEventListener("keydown", e => { if (e.key === "Escape") cerrar(); });
    $("#cajon-cuerpo").addEventListener("click", e => {
      const ir = e.target.closest("[data-ir]");
      if (ir) { irATarea(ir.dataset.ir); return; }
      const vc = e.target.closest("[data-vercomp]");
      if (vc) { cerrar(); seleccionarComp(vc.dataset.vercomp); irA($("#arquitectura")); }
    });
    document.addEventListener("click", e => { const b = e.target.closest("[data-copiar]"); if (b) copiar(b); });

    $$(".comp").forEach(b => b.addEventListener("click", () => {
      if (pasoActual >= 0) pasoRecorrido(-1);
      seleccionarComp(b.dataset.comp);
      if (estrecho()) irA($("#arq-panel"));
    }));
    $("#arq-panel").addEventListener("click", e => {
      const c = e.target.closest("[data-comp-ir]");
      if (c) { seleccionarComp(c.dataset.compIr); const d = $(`#comp-${c.dataset.compIr}`); if (d) d.focus({ preventScroll: true }); return; }
      const t = e.target.closest("[data-tarea-ir]");
      if (t) { irA($("#tareas")); irATarea(t.dataset.tareaIr); return; }
      const f = e.target.closest("[data-filtrar-comp]");
      if (f) { limpiarFiltros(); S.comp = f.dataset.filtrarComp; pintarControles(); render(); irA($("#tareas")); }
    });
    $("#rec-empezar").addEventListener("click", () => { pasoRecorrido(0); $("#rec-next").focus({ preventScroll: true }); });
    $("#rec-prev").addEventListener("click", () => pasoRecorrido(Math.max(0, pasoActual - 1)));
    $("#rec-next").addEventListener("click", () => {
      const i = pasoActual + 1;
      if (i >= DATA.recorrido.length) { pasoRecorrido(-1); $("#rec-empezar").focus({ preventScroll: true }); } else pasoRecorrido(i);
    });
    $("#rec-salir").addEventListener("click", () => { pasoRecorrido(-1); $("#rec-empezar").focus({ preventScroll: true }); });

    $$(".p-agente").forEach(el => {
      el.addEventListener("click", () => agente(el.dataset.agente));
      el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); agente(el.dataset.agente); } });
    });

    const tabs = $$('.pestanas [role="tab"]');
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => activarPestana(t, false));
      t.addEventListener("keydown", e => {
        const k = e.key;
        if (k === "ArrowRight" || k === "ArrowLeft" || k === "Home" || k === "End") {
          e.preventDefault();
          const j = k === "Home" ? 0 : k === "End" ? tabs.length - 1 : (i + (k === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
          activarPestana(tabs[j], true);
        }
      });
    });

    let raf = 0;
    window.addEventListener("resize", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => { dibujar(visibles()); resaltar(); }); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { dibujar(visibles()); resaltar(); });
  }

  // ── Arranque ─────────────────────────────────────────────────────────────
  $$(".comp").forEach(b => {
    const n = tareasDe(b.dataset.comp).length;
    const s = $(".comp-tareas", b);
    if (n) s.textContent = n === 1 ? "1 tarea abierta" : `${n} tareas abiertas`;
  });
  pintarControles();
  render();
  if (DATA.agentes.length) agente(DATA.agentes[0].id);
  seleccionarComp(DATA.comps.engine ? "engine" : Object.keys(DATA.comps)[0]);
  enlazar();
})();
