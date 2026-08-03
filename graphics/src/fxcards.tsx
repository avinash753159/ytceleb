import React from 'react';
import {
  AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {V5} from './tokens_v5';
import {
  CameraMove, EaseName, camera, clamp01, ease, handheld, layerTransform,
  mix, progress, shake,
} from './fx';

const FontFace: React.FC = () => (
  <style>{`@font-face {
    font-family: 'Anton';
    src: url('${staticFile('fonts/Anton-Regular.ttf')}') format('truetype');
    font-display: block;
  }`}</style>
);

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};

// Assets may arrive as data URLs (assemble.py's convention, because Chrome
// blocks file://) or as paths relative to graphics/public. Resolve the
// latter through staticFile so callers never have to base64 a 1080p plate.
const asset = (src: string) =>
  !src || src.startsWith('data:') || src.startsWith('http')
    ? src : staticFile(src);

// ============================================================ FilmGrain
// SVG fractal-noise grain. Cheap, resolution-independent, and it animates:
// a static grain plate reads as a dirty lens, not as film.
export const FilmGrain: React.FC<{
  opacity?: number; scale?: number; animate?: boolean;
}> = ({opacity = 0.06, scale = 0.9, animate = true}) => {
  const {frame} = useT();
  const seed = animate ? (frame % 8) + 1 : 1;
  return (
    <AbsoluteFill style={{
      opacity, mixBlendMode: 'overlay', pointerEvents: 'none',
    }}>
      <svg width="100%" height="100%">
        <filter id={`grain${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency={scale}
            numOctaves={3} seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

// ============================================================ Vignette
export const Vignette: React.FC<{strength?: number}> = ({strength = 0.55}) => (
  <AbsoluteFill style={{
    pointerEvents: 'none',
    background:
      `radial-gradient(ellipse at 50% 50%, transparent 42%, ` +
      `rgba(0,0,0,${strength}) 100%)`,
  }} />
);

// ============================================================ KenBurns2
// Eased Ken Burns. Differences from the V5 <KenBurns>:
//   - eases (default easeInOutCubic) so the move settles instead of stopping
//   - optional tiny rotation drift, which is what sells a "camera" move
//   - optional handheld wobble for otherwise dead-static stills
//   - overscan guarantees the pan can never expose a frame edge
export const KenBurns2: React.FC<{
  src: string;
  zoomFrom?: number; zoomTo?: number;
  panFrom?: [number, number]; panTo?: [number, number];
  rotFrom?: number; rotTo?: number;
  easing?: EaseName;
  drift?: number;          // handheld amount in px, 0 = locked off
  grain?: number;          // 0 = none
  vignette?: number;       // 0 = none
}> = ({
  src, zoomFrom = 1.04, zoomTo = 1.18, panFrom = [0.5, 0.5],
  panTo = [0.5, 0.5], rotFrom = 0, rotTo = 0, easing = 'easeInOutCubic',
  drift = 0, grain = 0, vignette = 0,
}) => {
  const {frame, dur} = useT();
  const cam = camera(frame, dur, {
    zoomFrom, zoomTo, panFrom, panTo, rotFrom, rotTo, easing,
  });
  const wob = drift > 0 ? handheld(frame, drift) : {x: 0, y: 0};
  // Overscan must cover both the pan travel and the rotation corner sweep.
  const travel = Math.max(
    Math.abs(panTo[0] - panFrom[0]), Math.abs(panTo[1] - panFrom[1]),
  );
  const cover = 1 + travel * 0.5 + Math.abs(rotTo - rotFrom) * 0.012;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <Img src={asset(src)} style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform:
          `translate(${wob.x}px, ${wob.y}px) ` +
          `scale(${(cam.zoom * cover).toFixed(5)}) ` +
          `translate(${((0.5 - cam.pan[0]) * 100).toFixed(4)}%, ` +
          `${((0.5 - cam.pan[1]) * 100).toFixed(4)}%) ` +
          `rotate(${cam.rot.toFixed(4)}deg)`,
      }} />
      {vignette > 0 ? <Vignette strength={vignette} /> : null}
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
    </AbsoluteFill>
  );
};

// ============================================================ ParallaxPhoto
// True multi-layer parallax. Layers are supplied back-to-front with a depth
// (0 = far, 1 = near); one virtual camera drives all of them, so they can
// never disagree about where the camera is.
//
// Layer images are produced by pipeline/fx.py (depth-sliced or subject
// cutout) and handed in as data URLs.
export const ParallaxPhoto: React.FC<{
  layers: {src: string; depth: number}[];
  zoomFrom?: number; zoomTo?: number;
  panFrom?: [number, number]; panTo?: [number, number];
  rotFrom?: number; rotTo?: number;
  easing?: EaseName;
  strength?: number;
  drift?: number;
  grain?: number;
  vignette?: number;
}> = ({
  layers, zoomFrom = 1.0, zoomTo = 1.10, panFrom = [0.42, 0.5],
  panTo = [0.58, 0.5], rotFrom = 0, rotTo = 0, easing = 'easeInOutCubic',
  strength = 1, drift = 0, grain = 0, vignette = 0,
}) => {
  const {frame, dur} = useT();
  const cam = camera(frame, dur, {
    zoomFrom, zoomTo, panFrom, panTo, rotFrom, rotTo, easing,
  });
  const wob = drift > 0 ? handheld(frame, drift) : {x: 0, y: 0};
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <AbsoluteFill style={{
        transform: `translate(${wob.x}px, ${wob.y}px)`,
      }}>
        {layers.map((l, i) => {
          const lt = layerTransform(cam, l.depth, {strength});
          return (
            <AbsoluteFill key={i} style={{overflow: 'hidden'}}>
              <Img src={asset(l.src)} style={{
                width: '100%', height: '100%', objectFit: 'cover',
                transform: lt.transform,
              }} />
            </AbsoluteFill>
          );
        })}
      </AbsoluteFill>
      {vignette > 0 ? <Vignette strength={vignette} /> : null}
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
    </AbsoluteFill>
  );
};

// ============================================================ ParallaxStage
// The card equivalent: the dark stage background, its accent rings and the
// foreground content all travel at different rates, so a graphic card gets
// depth instead of sliding in flat.
export const ParallaxStage: React.FC<{
  children?: React.ReactNode;
  accent?: string;
  bgSrc?: string;          // optional photo behind the stage
  amount?: number;
  impact?: boolean;
  title?: string;          // props-driven content, so the comp can render
  sub?: string;            // standalone without a JSX parent
}> = ({children, accent, bgSrc, amount = 1, impact = true, title, sub}) => {
  const {frame, dur} = useT();
  const a = accent ?? V5.accent;
  const cam = camera(frame, dur, {
    zoomFrom: 1.0, zoomTo: 1.05, panFrom: [0.47, 0.5], panTo: [0.53, 0.5],
    easing: 'easeInOutCubic',
  });
  const sh = impact ? shake(frame) : {x: 0, y: 0};
  const breathe = 1 + 0.18 * Math.sin(frame / 34);
  const far = layerTransform(cam, 0.15, {strength: amount});
  const mid = layerTransform(cam, 0.45, {strength: amount});
  const near = layerTransform(cam, 0.9, {strength: amount});
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 60%, ${V5.bg1}, ${V5.bg0})`,
      overflow: 'hidden',
    }}>
      <FontFace />
      {bgSrc ? (
        <AbsoluteFill style={{opacity: 0.34, overflow: 'hidden'}}>
          <Img src={asset(bgSrc)} style={{
            width: '100%', height: '100%', objectFit: 'cover',
            filter: 'blur(3px) saturate(0.7)',
            transform: far.transform,
          }} />
        </AbsoluteFill>
      ) : null}

      {/* accent rings ride the mid plane */}
      <AbsoluteFill style={{transform: mid.transform}}>
        {[420, 680, 940].map((r, i) => (
          <div key={i} style={{
            position: 'absolute', left: '50%', top: '50%',
            width: r * 2, height: r * 2, marginLeft: -r, marginTop: -r,
            borderRadius: r, border: `1.5px solid ${V5.ring}`,
            transform: `scale(${1 + 0.012 * Math.sin(frame / 18 + i)})`,
          }} />
        ))}
        <div style={{
          position: 'absolute', left: '50%', top: '58%',
          width: 900, height: 500, marginLeft: -450, marginTop: -250,
          background:
            `radial-gradient(ellipse, ${a}38, transparent 65%)`,
          filter: 'blur(30px)', opacity: breathe,
        }} />
      </AbsoluteFill>

      {/* content rides the near plane */}
      <AbsoluteFill style={{
        transform: `translate(${sh.x}px, ${sh.y}px) ${near.transform}`,
      }}>
        {children}
        {!children && title ? (
          <AbsoluteFill style={{
            justifyContent: 'center', alignItems: 'center',
            flexDirection: 'column',
          }}>
            <div style={{
              width: 120, height: 8, background: a, marginBottom: 30,
            }} />
            <div style={{
              fontFamily: V5.fontDisplay, fontSize: 120, color: V5.ink,
              textTransform: 'uppercase', textAlign: 'center',
              letterSpacing: 1, lineHeight: 1.02, maxWidth: 1500,
            }}>{title}</div>
            {sub ? (
              <div style={{
                fontFamily: V5.fontBody, fontSize: 40, color: V5.inkDim,
                marginTop: 22, textAlign: 'center', maxWidth: 1300,
              }}>{sub}</div>
            ) : null}
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================ FreezePunch
// Documentary beat: the frame locks, the camera punches in, a line of type
// snaps on. Used on "the moment" in a chapter.
export const FreezePunch: React.FC<{
  src: string;
  title?: string;
  sub?: string;
  accent?: string;
  punch?: number;
  holdMs?: number;         // hold before the punch starts
  desatTo?: number;        // 1 = no desat, 0 = full mono
}> = ({
  src, title, sub, accent, punch = 1.22, holdMs = 260, desatTo = 0.62,
}) => {
  const {frame, fps, dur} = useT();
  const hold = Math.round((holdMs / 1000) * fps);
  const p = ease('easeOutQuint', progress(frame, dur, {inFrames: hold}));
  const a = accent ?? V5.accent;
  const z = mix(1.0, punch, p);
  const sat = mix(1, desatTo, p);
  const tIn = clamp01((frame - hold - 3) / 9);
  const typeP = ease('easeOutBack', tIn);
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <FontFace />
      <Img src={asset(src)} style={{
        width: '100%', height: '100%', objectFit: 'cover',
        filter: `saturate(${sat.toFixed(3)}) contrast(${(1 + p * 0.12)
          .toFixed(3)})`,
        transform: `scale(${z.toFixed(5)})`,
      }} />
      <Vignette strength={0.35 + p * 0.25} />
      {title ? (
        <div style={{
          position: 'absolute', left: 96, bottom: 132,
          opacity: clamp01(tIn * 1.4),
          transform: `translateY(${((1 - typeP) * 34).toFixed(2)}px)`,
        }}>
          <div style={{
            width: 92, height: 7, background: a, marginBottom: 22,
            transform: `scaleX(${typeP.toFixed(3)})`,
            transformOrigin: 'left center',
          }} />
          <div style={{
            fontFamily: V5.fontDisplay, fontSize: 96, lineHeight: 1.02,
            color: V5.ink, textTransform: 'uppercase',
            letterSpacing: '0.5px', textShadow: '0 6px 34px rgba(0,0,0,0.75)',
          }}>{title}</div>
          {sub ? (
            <div style={{
              fontFamily: V5.fontBody, fontSize: 34, color: V5.inkDim,
              marginTop: 14, textShadow: '0 4px 18px rgba(0,0,0,0.8)',
            }}>{sub}</div>
          ) : null}
        </div>
      ) : null}
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

// ============================================================ SplitSqueeze
// Two frames arrive from opposite edges and meet on a hard accent seam.
// Honest before/after: both sides keep their own date label.
export const SplitSqueeze: React.FC<{
  leftSrc: string; rightSrc: string;
  leftLabel?: string; rightLabel?: string;
  accent?: string;
  seam?: number;
}> = ({
  leftSrc, rightSrc, leftLabel, rightLabel, accent, seam = 8,
}) => {
  const {frame, dur} = useT();
  const p = ease('easeOutExpo', progress(frame, dur, {outFrames: Math.round(dur * 0.45)}));
  const a = accent ?? V5.accent;
  const off = (1 - p) * 100;
  const Side: React.FC<{src: string; label?: string; dir: number}> = ({
    src, label, dir,
  }) => (
    <div style={{
      position: 'absolute', top: 0, bottom: 0, width: '50%',
      [dir < 0 ? 'left' : 'right']: 0, overflow: 'hidden',
      transform: `translateX(${(off * dir).toFixed(3)}%)`,
    } as React.CSSProperties}>
      <Img src={asset(src)} style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform: `scale(${(1.06 + 0.05 * p).toFixed(4)})`,
      }} />
      {label ? (
        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 54,
          textAlign: 'center', fontFamily: V5.fontDisplay, fontSize: 46,
          color: V5.ink, textTransform: 'uppercase', letterSpacing: 1,
          opacity: clamp01((p - 0.55) * 3),
          textShadow: '0 4px 22px rgba(0,0,0,0.85)',
        }}>{label}</div>
      ) : null}
    </div>
  );
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <FontFace />
      <Side src={leftSrc} label={leftLabel} dir={-1} />
      <Side src={rightSrc} label={rightLabel} dir={1} />
      <div style={{
        position: 'absolute', top: 0, bottom: 0, left: '50%',
        width: seam, marginLeft: -seam / 2, background: a,
        opacity: clamp01(p * 2), boxShadow: `0 0 40px ${a}`,
      }} />
      <FilmGrain opacity={0.04} />
    </AbsoluteFill>
  );
};

// ============================================================ KineticCaptions
// Burned-in word-synced captions on a transparent background, composited
// over footage by the assembler. Shows a rolling window of words and pops
// the active one. `words` come from the same faster-whisper word timings
// the beat segmenter already produces.
export const KineticCaptions: React.FC<{
  words: {text: string; atMs: number; endMs?: number}[];
  perLine?: number;
  accent?: string;
  fontSize?: number;
  bottom?: number;
  box?: boolean;
}> = ({
  words, perLine = 4, accent, fontSize = 68, bottom = 118, box = true,
}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const nowMs = (frame / fps) * 1000;

  // Active word = last word whose atMs has passed.
  let active = -1;
  for (let i = 0; i < words.length; i++) {
    if (words[i].atMs <= nowMs) active = i; else break;
  }
  if (active < 0) return <AbsoluteFill />;

  const lineIdx = Math.floor(active / perLine);
  const line = words.slice(lineIdx * perLine, (lineIdx + 1) * perLine);
  const lineStart = words[lineIdx * perLine].atMs;
  const inP = ease('easeOutBack', clamp01((nowMs - lineStart) / 180));

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <FontFace />
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom,
        display: 'flex', justifyContent: 'center', gap: 18,
        padding: '0 120px', flexWrap: 'wrap',
        transform: `translateY(${((1 - inP) * 26).toFixed(2)}px)`,
        opacity: clamp01(inP * 1.6),
      }}>
        {line.map((w, i) => {
          const gi = lineIdx * perLine + i;
          const isActive = gi === active;
          const pop = isActive
            ? ease('easeOutBack', clamp01((nowMs - w.atMs) / 130)) : 1;
          const s = isActive ? mix(0.86, 1.0, pop) : 1;
          return (
            <span key={i} style={{
              fontFamily: V5.fontDisplay,
              fontSize,
              lineHeight: 1.08,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: isActive ? '#fff' : V5.inkDim,
              background: box
                ? (isActive ? a : 'rgba(0,0,0,0.62)') : 'transparent',
              padding: box ? '6px 18px 10px' : 0,
              borderRadius: box ? 8 : 0,
              transform: `scale(${s.toFixed(4)})`,
              textShadow: box ? 'none' : '0 4px 20px rgba(0,0,0,0.9)',
              opacity: gi > active ? 0 : 1,
            }}>{w.text}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
