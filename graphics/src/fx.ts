// Motion primitives shared by every V12 effect comp.
//
// The V5-V10 cards animate with raw `interpolate`, which is linear: a move
// starts and stops at full speed. That is why pushes read mechanical. Every
// helper here eases, so moves settle instead of stopping dead.

export type Vec2 = [number, number];

// ------------------------------------------------------------------ easings
// All take and return 0..1.
export const linear = (t: number) => t;
export const easeInCubic = (t: number) => t * t * t;
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
export const easeOutQuint = (t: number) => 1 - Math.pow(1 - t, 5);
export const easeOutExpo = (t: number) =>
  t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
export const easeInOutExpo = (t: number) =>
  t <= 0 ? 0 : t >= 1 ? 1
  : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2
  : (2 - Math.pow(2, -20 * t + 10)) / 2;

// Slight overshoot then settle - for type and card entrances.
export const easeOutBack = (t: number, overshoot = 1.70158) =>
  1 + (overshoot + 1) * Math.pow(t - 1, 3) + overshoot * Math.pow(t - 1, 2);

// Decaying oscillation - for impact hits.
export const easeOutElastic = (t: number) => {
  if (t <= 0 || t >= 1) return t <= 0 ? 0 : 1;
  const c = (2 * Math.PI) / 3;
  return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c) + 1;
};

export const EASINGS = {
  linear, easeInCubic, easeOutCubic, easeInOutCubic, easeOutQuint,
  easeOutExpo, easeInOutExpo, easeOutBack, easeOutElastic,
} as const;

export type EaseName = keyof typeof EASINGS;

export const ease = (name: EaseName | undefined, t: number) =>
  (EASINGS[name ?? 'easeInOutCubic'])(clamp01(t));

// ------------------------------------------------------------------- helpers
export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
export const clamp = (v: number, lo: number, hi: number) =>
  v < lo ? lo : v > hi ? hi : v;
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
export const mix2 = (a: Vec2, b: Vec2, t: number): Vec2 =>
  [mix(a[0], b[0], t), mix(a[1], b[1], t)];

// Normalized progress across a comp, with optional hold at head/tail so a
// move can start late or finish early inside its own segment.
export const progress = (
  frame: number, dur: number,
  opts: {inFrames?: number; outFrames?: number} = {},
) => {
  const a = opts.inFrames ?? 0;
  const b = dur - 1 - (opts.outFrames ?? 0);
  if (b <= a) return 1;
  return clamp01((frame - a) / (b - a));
};

// ---------------------------------------------------------- virtual camera
// One camera move drives every parallax layer, so layers can never disagree
// about where the camera is. `depth` 0 = far background (moves least),
// 1 = foreground (moves most).
export interface CameraMove {
  zoomFrom?: number; zoomTo?: number;
  panFrom?: Vec2; panTo?: Vec2;   // normalized 0..1 focal point
  rotFrom?: number; rotTo?: number; // degrees, keep tiny (<0.8)
  easing?: EaseName;
}

export interface CameraState {
  zoom: number; pan: Vec2; rot: number; t: number;
}

export const camera = (
  frame: number, dur: number, m: CameraMove = {},
): CameraState => {
  const t = ease(m.easing ?? 'easeInOutCubic', progress(frame, dur));
  return {
    t,
    zoom: mix(m.zoomFrom ?? 1.0, m.zoomTo ?? 1.12, t),
    pan: mix2(m.panFrom ?? [0.5, 0.5], m.panTo ?? [0.5, 0.5], t),
    rot: mix(m.rotFrom ?? 0, m.rotTo ?? 0, t),
  };
};

// Transform for one parallax layer under a camera state.
//
// `strength` scales how far this layer translates relative to the camera pan.
// Overscan is applied so a layer can never expose an edge: a layer that moves
// must also be scaled up enough to cover the travel.
export const layerTransform = (
  cam: CameraState,
  depth: number,
  opts: {strength?: number; overscan?: number} = {},
) => {
  const strength = opts.strength ?? 1;
  const k = depth * strength;
  const dx = (0.5 - cam.pan[0]) * 100 * k;
  const dy = (0.5 - cam.pan[1]) * 100 * k;
  // Zoom differential: nearer layers zoom slightly more than far ones.
  const z = 1 + (cam.zoom - 1) * (0.55 + 0.45 * depth);
  const cover = 1 + (opts.overscan ?? 0.06) * k;
  return {
    transform:
      `scale(${(z * cover).toFixed(5)}) ` +
      `translate(${dx.toFixed(4)}%, ${dy.toFixed(4)}%) ` +
      `rotate(${(cam.rot * (0.4 + 0.6 * depth)).toFixed(4)}deg)`,
    scale: z * cover,
  };
};

// ------------------------------------------------------------------- shake
// Decaying impact shake. Amount is in px at frame 0.
export const shake = (frame: number, amount = 7, decayFrames = 9) => {
  const d = Math.max(0, 1 - frame / decayFrames);
  return {
    x: Math.sin(frame * 2.7) * amount * d,
    y: Math.cos(frame * 3.3) * (amount * 0.72) * d,
  };
};

// Handheld drift - a slow, non-repeating wobble for otherwise static frames.
export const handheld = (frame: number, amount = 3, speed = 1) => ({
  x: (Math.sin(frame * 0.021 * speed) + 0.5 * Math.sin(frame * 0.047 * speed))
     * amount,
  y: (Math.cos(frame * 0.017 * speed) + 0.5 * Math.cos(frame * 0.039 * speed))
     * amount * 0.8,
});
