/* Video narrado por el avatar: fondo de marca + escenas de motion graphics + avatar con layout por escena.
 *
 *   const render = ESCENAS.mount(root, { manifest, timeline, marca, ancho, alto, base });
 *   render(t);   // función pura de t (seek-safe): no guarda estado entre frames
 *
 * Tipos de escena (timeline.escenas[i].tipo): avatar, titulo, lista, dato, cita, imagen, video.
 * avatar: completo (protagonista) | narrador (a un lado, los gráficos ocupan el resto) | oculto.
 * Los <video> los crea la composición (HyperFrames los reproduce); aquí solo se animan sus contenedores.
 */
(function () {
  const MOVE = 0.55; // s del cambio de layout del avatar
  const IN = 0.45; // s de entrada de cada elemento
  const OUT = 0.3; // s de salida al final de la escena

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const outCubic = (x) => { x = clamp(x, 0, 1); return 1 - Math.pow(1 - x, 3); };
  const outBack = (x) => { x = clamp(x, 0, 1); const c = 1.5; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };

  // Layout por formato: escala y centro x del avatar, y el área libre para gráficos en cada modo.
  // REACH: media anchura del personaje con los brazos abiertos, en px del PNG (1024 de ancho).
  const REACH = 470;
  function side(W, H, s, pad) {
    const cx = W - s * (REACH - 40);
    const x = pad;
    return { s, cx, area: { x, y: pad + 30, w: cx - s * REACH - 30 - x, h: H - 2 * pad - 60 } };
  }
  function layouts(W, H) {
    const v = H > W * 1.2, sq = !v && H > W * 0.8;
    if (v) return {
      completo: { s: 1.05, cx: W / 2, area: { x: 70, y: 150, w: W - 140, h: 300 } },
      narrador: { s: 0.6, cx: W / 2, area: { x: 70, y: 150, w: W - 140, h: H - 0.6 * 1536 - 170 } },
      oculto: { s: 0.6, cx: W / 2, hide: true, area: { x: 70, y: 150, w: W - 140, h: H - 300 } },
    };
    // horizontal y cuadrado: en "completo" la cabeza baja para dejar una franja de título arriba
    const top = { s: (H - 190) / 1536 / 0.92, cx: W / 2, area: { x: 60, y: 40, w: W - 120, h: 130 } };
    const nar = sq ? side(W, H, 0.46, 60) : side(W, H, 0.64, 80);
    return {
      completo: top,
      narrador: nar,
      oculto: { ...nar, hide: true, area: { x: 80, y: 80, w: W - 160, h: H - 160 } },
    };
  }

  function div(cls, parent, text) {
    const n = document.createElement("div");
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    parent.appendChild(n);
    return n;
  }

  // tamaño de letra que cabe en el área sin medir el DOM (determinista aunque la fuente tarde)
  function fitFont(text, w, h, max, min, lineH, widthK) {
    const chars = Math.max(1, String(text).length);
    const k = widthK * 1.12; // margen: las letras anchas (m, w, mayúsculas) superan el promedio
    for (let fs = max; fs >= min; fs -= 2) {
      const perLine = Math.max(1, Math.floor(w / (fs * k)));
      const lines = Math.ceil(chars / perLine);
      if (lines * fs * lineH <= h) return fs;
    }
    return min;
  }

  function words(el, text) {
    return String(text).split(/\s+/).filter(Boolean).map((w) => {
      const s = document.createElement("span");
      s.className = "w";
      s.textContent = w;
      el.appendChild(s);
      el.appendChild(document.createTextNode(" "));
      return s;
    });
  }

  // aparición de un elemento: entra en [t0, t0+IN], sale en [t1-OUT, t1]
  function show(el, t, t0, t1, dy) {
    const a = outCubic((t - t0) / IN) * (1 - smooth((t - (t1 - OUT)) / OUT));
    el.style.opacity = a.toFixed(3);
    el.style.transform = `translateY(${((1 - outCubic((t - t0) / IN)) * (dy || 40)).toFixed(1)}px)`;
    return a;
  }

  function fmtNum(v, dec, lang) {
    return v.toLocaleString(lang === "en" ? "en-US" : "es-MX", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function build(sc, layer, L, lang) {
    const a = L[sc.avatar].area;
    const box = div(`sc sc-${sc.tipo}`, layer);
    Object.assign(box.style, { left: a.x + "px", top: a.y + "px", width: a.w + "px", height: a.h + "px" });
    const parts = [];
    const dur = sc.t1 - sc.t0;
    const at = (k) => sc.t0 + k;

    if (sc.tipo === "avatar" && sc.texto) {
      const h = div("title small", box);
      h.style.fontSize = fitFont(sc.texto, a.w, a.h, 96, 40, 1.12, 0.56) + "px";
      words(h, sc.texto).forEach((w, i) => parts.push({ el: w, t: at(0.1 + i * 0.06), dy: 30 }));
    } else if (sc.tipo === "titulo") {
      const h = div("title", box);
      h.style.fontSize = fitFont(sc.titulo || "", a.w, a.h * 0.62, 150, 48, 1.08, 0.58) + "px";
      words(h, sc.titulo || "").forEach((w, i) => parts.push({ el: w, t: at(0.1 + i * 0.07), dy: 50 }));
      const bar = div("bar", box);
      parts.push({ el: bar, t: at(0.25), bar: true });
      if (sc.subtitulo) {
        const s = div("sub", box, sc.subtitulo);
        s.style.fontSize = fitFont(sc.subtitulo, a.w, a.h * 0.25, 60, 30, 1.2, 0.52) + "px";
        parts.push({ el: s, t: at(0.6) });
      }
    } else if (sc.tipo === "lista") {
      const items = (sc.items || []).map((it) => (typeof it === "string" ? { texto: it } : it));
      if (sc.titulo) {
        const h = div("title list-title", box, sc.titulo);
        h.style.fontSize = fitFont(sc.titulo, a.w, a.h * 0.2, 90, 40, 1.1, 0.58) + "px";
        parts.push({ el: h, t: at(0.1) });
      }
      const room = a.h * (sc.titulo ? 0.72 : 0.95) / Math.max(1, items.length);
      const longest = items.reduce((m, it) => Math.max(m, it.texto.length), 1);
      const fs = fitFont("x".repeat(longest), a.w - 110, room * 0.82, 72, 30, 1.15, 0.52);
      const span = Math.min(dur * 0.6, 0.8 * items.length);
      items.forEach((it, i) => {
        const row = div("item", box);
        row.style.fontSize = fs + "px";
        div("num", row, String(i + 1));
        div("txt", row, it.texto);
        const t = it.t !== undefined ? it.t : at(0.35 + (span * i) / Math.max(1, items.length));
        parts.push({ el: row, t, dy: 0, dx: -60 });
      });
    } else if (sc.tipo === "dato") {
      const n = div("num-big", box);
      const label = `${sc.prefijo || ""}${sc.valor}${sc.sufijo || ""}`;
      n.style.fontSize = fitFont(label, a.w, a.h * 0.5, 260, 80, 1.0, 0.62) + "px";
      parts.push({ el: n, t: at(0.1), count: { el: n, v: Number(sc.valor) || 0, pre: sc.prefijo || "", suf: sc.sufijo || "",
        dec: String(sc.valor).includes(".") ? String(sc.valor).split(".")[1].length : 0 } });
      if (sc.texto) {
        const s = div("sub", box, sc.texto);
        s.style.fontSize = fitFont(sc.texto, a.w, a.h * 0.3, 64, 30, 1.2, 0.52) + "px";
        parts.push({ el: s, t: at(0.5) });
      }
    } else if (sc.tipo === "cita") {
      div("quote-mark", box, "“");
      const q = div("quote", box, sc.texto || "");
      q.style.fontSize = fitFont(sc.texto || "", a.w, a.h * 0.6, 96, 36, 1.18, 0.52) + "px";
      parts.push({ el: q, t: at(0.15) });
      if (sc.autor) parts.push({ el: div("sub author", box, "— " + sc.autor), t: at(0.6) });
    } else if (sc.tipo === "imagen") {
      const card = div("card", box);
      const img = document.createElement("img");
      img.src = sc._src;
      card.appendChild(img);
      parts.push({ el: card, t: at(0), dy: 60, kb: img });
      if (sc.texto) parts.push(...caption(box, sc.texto, a, at(0.35)));
    } else if (sc.tipo === "video") {
      if (sc.texto) parts.push(...caption(box, sc.texto, a, at(0.25)));
    }
    return { box, parts };
  }

  function caption(box, text, a, t) {
    const c = div("caption", box);
    c.style.fontSize = fitFont(text, a.w - 60, 220, 84, 36, 1.12, 0.58) + "px";
    div("hl", c, text);
    return [{ el: c, t, dy: 30 }];
  }

  function mount(root, o) {
    const { manifest, timeline, marca, ancho: W, alto: H } = o;
    const L = layouts(W, H);
    const escenas = timeline.escenas;
    root.style.setProperty("--fondo", marca.fondo);
    root.style.setProperty("--acento", marca.acento);
    root.style.setProperty("--texto", marca.texto);

    const layer = root.querySelector(".graficos");
    const built = escenas.map((sc) => build(sc, layer, L, timeline.idioma));
    const vwraps = escenas.map((sc, i) => root.querySelector(`[data-vwrap="${i}"]`));
    escenas.forEach((sc, i) => {
      const w = vwraps[i];
      if (!w) return;
      const a = sc.avatar === "oculto" ? { x: 0, y: 0, w: W, h: H } : L[sc.avatar].area;
      Object.assign(w.style, { left: a.x + "px", top: a.y + "px", width: a.w + "px", height: a.h + "px" });
      if (sc.avatar === "oculto") w.classList.add("full");
    });

    const place = root.querySelector(".avatar-place");
    const sparks = root.querySelector(".sparks");
    const player = AVPLAYER.mount(root.querySelector(".avatar-body"), root.querySelector(".avatar-stage"), manifest, timeline, { base: o.base });

    function sceneAt(t) {
      let i = 0;
      for (let k = 0; k < escenas.length; k++) if (escenas[k].t0 <= t) i = k;
      return i;
    }

    function placeFor(mode) {
      const l = L[mode];
      return { x: l.cx - 512 * l.s, y: H - 1536 * l.s + (l.hide ? 1536 * l.s + 80 : 0), s: l.s };
    }

    return function render(t) {
      const i = sceneAt(t);
      const sc = escenas[i];
      // layout del avatar: interpola desde el modo de la escena anterior
      const prev = i > 0 ? escenas[i - 1].avatar : sc.avatar;
      const k = smooth((t - sc.t0) / MOVE);
      const p0 = placeFor(prev), p1 = placeFor(sc.avatar);
      const x = p0.x + (p1.x - p0.x) * k, y = p0.y + (p1.y - p0.y) * k, s = p0.s + (p1.s - p0.s) * k;
      place.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) scale(${s.toFixed(4)})`;
      sparks.style.opacity = (sc.avatar === "completo" ? k : prev === "completo" ? 1 - k : 0).toFixed(3);
      player.render(t);

      built.forEach((b, j) => {
        const e = escenas[j];
        const live = t >= e.t0 - 0.01 && t <= e.t1 + 0.01;
        b.box.style.display = live ? "" : "none";
        if (!live) return;
        for (const p of b.parts) {
          if (p.bar) {
            const w = outCubic((t - p.t) / 0.5) * (1 - smooth((t - (e.t1 - OUT)) / OUT));
            p.el.style.transform = `scaleX(${w.toFixed(3)})`;
            continue;
          }
          const a = outCubic((t - p.t) / IN) * (1 - smooth((t - (e.t1 - OUT)) / OUT));
          const m = 1 - outCubic((t - p.t) / IN);
          p.el.style.opacity = a.toFixed(3);
          p.el.style.transform = p.dx ? `translateX(${(m * p.dx).toFixed(1)}px)` : `translateY(${(m * (p.dy === undefined ? 40 : p.dy)).toFixed(1)}px)`;
          if (p.count) {
            const c = p.count;
            const v = c.v * outCubic((t - p.t) / 1.3);
            p.el.textContent = c.pre + fmtNum(v, c.dec, timeline.idioma) + c.suf;
            p.el.style.transform += ` scale(${(0.85 + 0.15 * outBack((t - p.t) / 0.6)).toFixed(3)})`;
          }
          if (p.kb) p.kb.style.transform = `scale(${(1.04 + 0.08 * clamp((t - e.t0) / Math.max(1, e.t1 - e.t0), 0, 1)).toFixed(4)})`;
        }
      });
      vwraps.forEach((w, j) => {
        if (!w) return;
        const e = escenas[j];
        const a = clamp((t - e.t0) / 0.3, 0, 1) * (1 - clamp((t - (e.t1 - 0.25)) / 0.25, 0, 1));
        w.style.opacity = a.toFixed(3);
        w.style.transform = `scale(${(0.96 + 0.04 * outCubic((t - e.t0) / IN)).toFixed(4)})`;
      });
      // destellos de acento: pulso suave
      const pulse = 1 + 0.06 * Math.sin((2 * Math.PI * t) / 1.6);
      sparks.style.scale = pulse.toFixed(3);
    };
  }

  function drive(tl, render, duration) {
    const proxy = { t: 0 };
    render(0);
    tl.fromTo(proxy, { t: 0 }, { t: duration, duration, ease: "none", onUpdate: () => render(proxy.t) }, 0);
  }

  window.ESCENAS = { mount, drive, layouts };
})();
