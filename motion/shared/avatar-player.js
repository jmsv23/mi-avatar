/* Reproductor del avatar: timeline.json -> estado del avatar en el tiempo t (función pura de t).
 *
 *   const player = AVPLAYER.mount(bodyEl, stageEl, manifest, timeline);
 *   player.render(t);            // pinta el frame t (seek-safe: no guarda nada entre frames)
 *   AVPLAYER.drive(tl, player);  // un solo tween proxy en el timeline pausado llama render(t)
 *
 * bodyEl recibe el movimiento procedural (respiración, balanceo, rebote, gestos) con
 * transform-origin abajo al centro; stageEl contiene el avatar (pose + boca + párpados).
 *
 * Cambio de pose: dos capas del avatar dentro de stageEl; la pose nueva aparece con un fundido corto
 * sobre la anterior. Cada pose se desplaza para que su cara (ojos + boca) quede donde la de `neutral`,
 * así la cabeza no salta aunque las imágenes de las poses no estén alineadas al píxel.
 */
(function () {
  const TRANS = 0.05; // s de transición entre visemas
  const OPEN = { A: 1, E_I: 0.55, O_U: 0.8, FV: 0.3, CONS: 0.35, MBP: 0, REST: 0 };
  const BLINK = { close: 0.06, hold: 0.04, open: 0.07 };
  const FADE = 0.18; // s del fundido entre poses (sin corte seco ni rebote)

  const smooth = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

  // último índice i con arr[i][key] <= t (o -1)
  function find(arr, t, key) {
    let lo = 0, hi = arr.length - 1, ans = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const v = key ? arr[mid][key] : arr[mid];
      if (v <= t) { ans = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return ans;
  }

  function visemeAt(vis, t) {
    const i = find(vis, t, "t");
    if (i < 0) return { mouth: AVATAR.mixViseme("REST", "REST", 0), open: 0 };
    const cur = vis[i];
    const end = cur.t + cur.d;
    const curV = t < end ? cur.v : "REST"; // después del último visema (o en un hueco) la boca descansa
    const next = vis[i + 1];
    const nextV = next && Math.abs(next.t - end) < 0.02 ? next.v : "REST";
    const k = smooth((t - (end - TRANS / 2)) / TRANS);
    return { mouth: AVATAR.mixViseme(curV, nextV, k), open: OPEN[curV] * (1 - k) + OPEN[nextV] * k };
  }

  // qué tan "hablando" está en t: 0..1, suavizado en ±0.25 s
  function talkingAt(vis, t) {
    let acc = 0, n = 0;
    for (let dt = -0.25; dt <= 0.25; dt += 0.05) {
      const i = find(vis, t + dt, "t");
      const v = i >= 0 && t + dt < vis[i].t + vis[i].d ? vis[i].v : "REST";
      acc += v === "REST" ? 0 : 1;
      n++;
    }
    return acc / n;
  }

  function lidsAt(blinks, t) {
    const i = find(blinks, t);
    if (i < 0) return 0;
    const dt = t - blinks[i];
    if (dt < BLINK.close) return dt / BLINK.close;
    if (dt < BLINK.close + BLINK.hold) return 1;
    const o = (dt - BLINK.close - BLINK.hold) / BLINK.open;
    return o < 1 ? 1 - o : 0;
  }

  function faceCenter(p) {
    return { x: (p.ojos.izq.x + p.ojos.der.x + p.boca.x) / 3, y: (p.ojos.izq.y + p.ojos.der.y + p.boca.y) / 3 };
  }

  function mount(bodyEl, stageEl, manifest, timeline, opts = {}) {
    const ref = faceCenter(manifest.poses.neutral || Object.values(manifest.poses)[0]);
    const off = {};
    for (const [k, p] of Object.entries(manifest.poses)) {
      const c = faceCenter(p);
      off[k] = { x: ref.x - c.x, y: ref.y - c.y };
    }
    const layers = [0, 1].map(() => {
      const el = stageEl.appendChild(document.createElementNS("http://www.w3.org/1999/xhtml", "div"));
      const av = AVATAR.create(el, manifest, { base: opts.base || "" });
      Object.assign(el.style, { position: "absolute", left: "0px", top: "0px" });
      return { el, av };
    });
    const { visemas, poses, parpadeos, gestos } = timeline;

    function paint(layer, pose, opacity, v, lids) {
      const habla = manifest.poses[pose].habla !== false;
      layer.av.set({ pose, mouth: habla ? v.mouth : null, lids });
      layer.el.style.opacity = String(opacity);
      layer.el.style.transform = `translate(${off[pose].x.toFixed(2)}px, ${off[pose].y.toFixed(2)}px)`;
    }

    function render(t) {
      const pi = Math.max(0, find(poses, t, "t"));
      const pose = poses[pi].pose;
      const v = visemeAt(visemas, t);
      const lids = lidsAt(parpadeos, t);
      const since = t - poses[pi].t;
      if (pi > 0 && since < FADE) {
        paint(layers[0], poses[pi - 1].pose, 1, v, lids);
        paint(layers[1], pose, smooth(since / FADE), v, lids);
      } else {
        paint(layers[0], pose, 0, v, lids);
        paint(layers[1], pose, 1, v, lids);
      }

      // movimiento procedural, todo función de t
      const talk = talkingAt(visemas, t);
      let y = -3.5 * talk * (0.5 + 0.5 * Math.sin((2 * Math.PI * t) / 0.62)) - 2.5 * v.open;
      let rot = 0.55 * Math.sin((2 * Math.PI * t) / 6.1 + 0.7) + 0.35 * talk * Math.sin((2 * Math.PI * t) / 1.9);
      const sy = 1 + 0.009 * Math.sin((2 * Math.PI * t) / 3.4);
      const gi = find(gestos, t, "t");
      if (gi >= 0 && t - gestos[gi].t < gestos[gi].d) {
        const g = gestos[gi];
        const k = (t - g.t) / g.d;
        const wave = Math.sin(2 * Math.PI * 2 * k) * (1 - k);
        if (g.g === "asentir") y += 8 * wave;
        else if (g.g === "negar") rot += 2.4 * wave;
      }
      bodyEl.style.transform = `translateY(${y.toFixed(2)}px) rotate(${rot.toFixed(3)}deg) scale(1, ${sy.toFixed(4)})`;
    }

    return { render, avatar: layers[1].av };
  }

  function drive(tl, player, duration, at = 0) {
    const proxy = { t: 0 };
    player.render(0);
    tl.fromTo(proxy, { t: 0 }, { t: duration, duration, ease: "none", onUpdate: () => player.render(proxy.t) }, at);
  }

  window.AVPLAYER = { mount, drive, visemeAt, lidsAt };
})();
