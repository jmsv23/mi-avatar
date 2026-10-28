/* Reproductor del avatar: timeline.json -> estado del avatar en el tiempo t (función pura de t).
 *
 *   const player = AVPLAYER.mount(bodyEl, stageEl, manifest, timeline);
 *   player.render(t);            // pinta el frame t (seek-safe: no guarda nada entre frames)
 *   AVPLAYER.drive(tl, player);  // un solo tween proxy en el timeline pausado llama render(t)
 *
 * bodyEl recibe el movimiento procedural (respiración, balanceo, rebote, gestos) con
 * transform-origin abajo al centro; stageEl contiene el avatar (pose + boca + párpados).
 */
(function () {
  const TRANS = 0.05; // s de transición entre visemas
  const OPEN = { A: 1, E_I: 0.55, O_U: 0.8, FV: 0.3, CONS: 0.35, MBP: 0, REST: 0 };
  const BLINK = { close: 0.06, hold: 0.04, open: 0.07 };
  const BOUNCE = 0.35; // s del rebote al cambiar de pose

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

  function mount(bodyEl, stageEl, manifest, timeline, opts = {}) {
    const avatar = AVATAR.create(stageEl, manifest, { base: opts.base || "" });
    const { visemas, poses, parpadeos, gestos } = timeline;

    function render(t) {
      const pi = Math.max(0, find(poses, t, "t"));
      const pose = poses[pi].pose;
      const v = visemeAt(visemas, t);
      const habla = manifest.poses[pose].habla !== false;
      avatar.set({ pose, mouth: habla ? v.mouth : null, lids: lidsAt(parpadeos, t) });

      // movimiento procedural, todo función de t
      const talk = talkingAt(visemas, t);
      let y = -3.5 * talk * (0.5 + 0.5 * Math.sin((2 * Math.PI * t) / 0.62)) - 2.5 * v.open;
      let rot = 0.55 * Math.sin((2 * Math.PI * t) / 6.1 + 0.7) + 0.35 * talk * Math.sin((2 * Math.PI * t) / 1.9);
      let sy = 1 + 0.009 * Math.sin((2 * Math.PI * t) / 3.4);
      let s = 1;

      const since = t - poses[pi].t;
      if (pi > 0 && since < BOUNCE) {
        const k = since / BOUNCE;
        s *= 1 + 0.035 * Math.sin(Math.PI * k) * (1 - k);
        sy *= 1 - 0.03 * Math.sin(Math.PI * k * 2) * (1 - k);
      }
      const gi = find(gestos, t, "t");
      if (gi >= 0 && t - gestos[gi].t < gestos[gi].d) {
        const g = gestos[gi];
        const k = (t - g.t) / g.d;
        const wave = Math.sin(2 * Math.PI * 2 * k) * (1 - k);
        if (g.g === "asentir") y += 8 * wave;
        else if (g.g === "negar") rot += 2.4 * wave;
      }
      bodyEl.style.transform = `translateY(${y.toFixed(2)}px) rotate(${rot.toFixed(3)}deg) scale(${s.toFixed(4)}, ${(s * sy).toFixed(4)})`;
    }

    return { render, avatar };
  }

  function drive(tl, player, duration, at = 0) {
    const proxy = { t: 0 };
    player.render(0);
    tl.fromTo(proxy, { t: 0 }, { t: duration, duration, ease: "none", onUpdate: () => player.render(proxy.t) }, at);
  }

  window.AVPLAYER = { mount, drive, visemeAt, lidsAt };
})();
