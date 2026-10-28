/* Avatar 2D: pose PNG + boca SVG paramétrica + capa de vello facial + párpados.
 *
 * Todo vive en coordenadas del PNG normalizado (1024x1536). El contenedor se escala por CSS.
 * Sin estado temporal propio: quien anima llama avatar.set({...}) con valores ya calculados
 * para el tiempo t (seek-safe).
 *
 *   const av = AVATAR.create(el, manifest, { base: "../assets/" });
 *   av.set({ pose: "hablar", viseme: "A" });                 // visema puro
 *   av.set({ mouth: AVATAR.mixViseme("E_I", "O_U", 0.3) });  // mezcla entre visemas
 *   av.set({ lids: 1 });                                     // 0 abierto … 1 cerrado
 *
 * Colores, tamaño de ojo y escala de boca vienen del manifiesto (avatar anclajes).
 */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const DEFAULT_COLORS = {
    interior: "#3b1110",
    lengua: "#d0525a",
    dientes: "#fbf6ef",
    labio: "#f27f66",
    linea: "#24130c",
  };

  // Parámetros relativos al ancla (centro de la línea de labios), en unidades de una boca de 140 px
  // de ancho; la pose escala el grupo con boca.escala.
  //   w: media anchura · top/bottom: bordes de la apertura · corner: altura de comisuras
  //   round: 0 = boca ancha y plana, 1 = redonda · teethTop/teethBottom: alto visible de dientes
  //   tongue: 0..1 · lipT: grosor del labio inferior
  const VISEMES = {
    REST: null, // boca original del dibujo
    MBP: null, // labios cerrados = boca original
    A: { w: 48, top: -5, bottom: 34, corner: -6, round: 0.45, teethTop: 15, teethBottom: 0, tongue: 1, lipT: 9 },
    E_I: { w: 56, top: -4, bottom: 17, corner: -7, round: 0.25, teethTop: 14, teethBottom: 6, tongue: 0, lipT: 8 },
    O_U: { w: 25, top: -6, bottom: 26, corner: 4, round: 0.95, teethTop: 0, teethBottom: 0, tongue: 0.4, lipT: 10 },
    FV: { w: 44, top: -4, bottom: 8, corner: -5, round: 0.35, teethTop: 17, teethBottom: 0, tongue: 0, lipT: 12 },
    CONS: { w: 48, top: -3, bottom: 13, corner: -6, round: 0.35, teethTop: 12, teethBottom: 6, tongue: 0, lipT: 8 },
  };
  const CLOSED = { w: 52, top: 0, bottom: 0, corner: -6, round: 0.35, teethTop: 0, teethBottom: 0, tongue: 0, lipT: 6 };
  const KEYS = Object.keys(CLOSED);

  function mixViseme(a, b, k) {
    const pa = VISEMES[a] || CLOSED;
    const pb = VISEMES[b] || CLOSED;
    const out = {};
    for (const key of KEYS) out[key] = pa[key] + (pb[key] - pa[key]) * k;
    return out;
  }

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // Contorno de la apertura: dos curvas cúbicas comisura→comisura.
  function mouthPath(p) {
    const { w, top, bottom, corner, round } = p;
    const cx = w * (0.15 + 0.5 * (1 - round)); // control más al centro = más redonda
    const ty = top - (corner - top) * 0.35 * round;
    const by = bottom + (bottom - corner) * 0.3 * round;
    return (
      `M ${-w} ${corner} C ${-cx} ${ty} ${cx} ${ty} ${w} ${corner} ` +
      `C ${cx} ${by} ${-cx} ${by} ${-w} ${corner} Z`
    );
  }

  function lowerLipPath(p) {
    const { w, bottom, corner, round, lipT } = p;
    const cx = w * (0.15 + 0.5 * (1 - round));
    const by = bottom + (bottom - corner) * 0.3 * round;
    const lw = w * 0.82;
    return (
      `M ${-w} ${corner} C ${-cx} ${by} ${cx} ${by} ${w} ${corner} ` +
      `C ${lw * 0.7} ${by + lipT * 1.6} ${-lw * 0.7} ${by + lipT * 1.6} ${-w} ${corner} Z`
    );
  }

  let instances = 0;

  function create(root, manifest, opts = {}) {
    const base = opts.base || "";
    const uid = `av${++instances}`; // ids únicos: puede haber varios avatares en la página (PiP)
    const { ancho, alto } = manifest.lienzo;
    const COLORS = Object.assign({}, DEFAULT_COLORS, manifest.colores || {});
    const EYE = manifest.ojo || { rx: 38, ry: 22 };
    root.style.position = "relative";
    root.style.width = ancho + "px";
    root.style.height = alto + "px";
    const svg = el("svg", { viewBox: `0 0 ${ancho} ${alto}`, width: ancho, height: alto, style: "display:block;overflow:visible" }, root);
    const defs = el("defs", {}, svg);
    el("filter", { id: `${uid}-feather`, x: "-30%", y: "-60%", width: "160%", height: "220%" }, defs).appendChild(
      (() => {
        const f = document.createElementNS(NS, "feGaussianBlur");
        f.setAttribute("stdDeviation", "4");
        return f;
      })()
    );
    const poseImg = el("image", { x: 0, y: 0, width: ancho, height: alto }, svg);

    // boca: [borrado] [apertura + dientes + lengua] [labio] [vello facial]
    const mouthG = el("g", {}, svg);
    // parche de piel que tapa los labios dibujados: óvalo central + trazo extra opcional por pose
    // (manifest: borrado_extra, para comisuras que quedan fuera del óvalo, p. ej. una sonrisa de lado)
    const erase = el("g", { filter: `url(#${uid}-feather)` }, mouthG);
    const eraseFill = el("ellipse", { cx: 0, cy: 3, rx: 74, ry: 20 }, erase);
    const eraseExtra = el("path", { fill: "none", "stroke-width": 10, "stroke-linecap": "round" }, erase);
    const clip = el("clipPath", { id: `${uid}-mouth` }, defs);
    const clipPath = el("path", {}, clip);
    const interior = el("path", { fill: COLORS.interior }, mouthG);
    const inner = el("g", { "clip-path": `url(#${uid}-mouth)` }, mouthG);
    const tongue = el("ellipse", { fill: COLORS.lengua }, inner);
    const teethTop = el("rect", { fill: COLORS.dientes, x: -80, width: 160 }, inner);
    const teethBottom = el("rect", { fill: COLORS.dientes, x: -80, width: 160 }, inner);
    const lip = el("path", { fill: COLORS.labio, stroke: COLORS.linea, "stroke-width": 2.5, "stroke-linejoin": "round" }, mouthG);
    const outline = el("path", { fill: "none", stroke: COLORS.linea, "stroke-width": 3.5, "stroke-linejoin": "round" }, mouthG);
    const hair = el("image", {}, mouthG);

    // párpados: rectángulo de piel recortado por la elipse del ojo + línea de pestañas
    const { rx, ry } = EYE;
    const lidG = el("g", {}, svg);
    const lids = {};
    for (const side of ["izq", "der"]) {
      const g = el("g", {}, lidG);
      const cp = el("clipPath", { id: `${uid}-eye-${side}` }, defs);
      el("ellipse", { cx: 0, cy: ry * 0.05, rx, ry }, cp);
      const lid = el("rect", { x: -rx - 6, y: -ry - 8, width: 2 * rx + 12, height: 0, "clip-path": `url(#${uid}-eye-${side})` }, g);
      const lash = el("path", { fill: "none", stroke: COLORS.linea, "stroke-width": Math.max(3, ry * 0.27), "stroke-linecap": "round" }, g);
      lids[side] = { g, lid, lash };
    }

    let pose = null;
    const state = {};

    function setPose(id) {
      if (pose && pose.id === id) return;
      const p = manifest.poses[id];
      if (!p) throw new Error(`pose desconocida: ${id}`);
      pose = { id, ...p };
      poseImg.setAttribute("href", base + p.archivo);
      const b = p.boca;
      mouthG.setAttribute("transform", `translate(${b.x} ${b.y}) rotate(${b.rotacion || 0}) scale(${b.escala || 1})`);
      // la capa de vello se midió en px del PNG (ya escalada); el grupo de la boca la vuelve a escalar
      const s = b.escala || 1;
      if (p.vello) {
        hair.setAttribute("href", base + p.vello.archivo);
        hair.setAttribute("x", p.vello.x / s);
        hair.setAttribute("y", p.vello.y / s);
        hair.setAttribute("width", p.vello.ancho / s);
        hair.setAttribute("height", p.vello.alto / s);
      } else {
        hair.removeAttribute("href");
      }
      const skin = p.piel_boca || "#fda769";
      eraseFill.setAttribute("fill", skin);
      eraseExtra.setAttribute("stroke", skin);
      eraseExtra.setAttribute("d", p.borrado_extra || "");
      for (const side of ["izq", "der"]) {
        const e = p.ojos[side];
        lids[side].g.setAttribute("transform", `translate(${e.x} ${e.y}) rotate(${b.rotacion || 0})`);
        lids[side].lid.setAttribute("fill", e.piel);
      }
    }

    function setMouth(m) {
      const open = m && m.bottom - m.top > 1.5;
      mouthG.style.display = open ? "" : "none";
      if (!open) return;
      const d = mouthPath(m);
      clipPath.setAttribute("d", d);
      interior.setAttribute("d", d);
      outline.setAttribute("d", d);
      lip.setAttribute("d", lowerLipPath(m));
      teethTop.setAttribute("y", m.top - 20);
      teethTop.setAttribute("height", Math.max(0, 20 + m.teethTop));
      teethBottom.setAttribute("y", m.bottom + m.corner * 0 - m.teethBottom);
      teethBottom.setAttribute("height", m.teethBottom > 0 ? m.teethBottom + 20 : 0);
      const tw = m.w * 0.6;
      tongue.setAttribute("cx", 0);
      tongue.setAttribute("cy", m.bottom + 4);
      tongue.setAttribute("rx", tw);
      tongue.setAttribute("ry", Math.max(0, (m.bottom - m.top) * 0.45 * m.tongue));
    }

    function setLids(k) {
      const blink = pose.parpadeo !== false;
      for (const side of ["izq", "der"]) {
        const c = blink ? Math.max(0, Math.min(1, k)) : 0;
        const { lid, lash } = lids[side];
        const edge = ry * (-0.95 + 1.36 * c); // borde inferior del párpado (cerrado = un poco abajo del centro)
        lid.setAttribute("height", c > 0.02 ? edge + ry + 8 : 0);
        const sag = ry * (0.18 + 0.27 * c); // el borde se curva hacia abajo al cerrar
        const lift = ry * 0.18 * (1 - c);
        const lx = rx * 0.97;
        lash.setAttribute("d", c > 0.02 ? `M ${-lx} ${edge - lift} Q 0 ${edge + sag} ${lx} ${edge - lift}` : "");
      }
    }

    function set(s) {
      Object.assign(state, s);
      setPose(state.pose || "neutral");
      setMouth(state.mouth !== undefined ? state.mouth : VISEMES[state.viseme || "REST"]);
      setLids(state.lids || 0);
    }

    return { set, svg, get pose() { return pose; } };
  }

  window.AVATAR = { create, mixViseme, VISEMES, CLOSED };
})();
