import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {V5} from './tokens_v5';
import {Stage} from './v5cards';

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps,
          config: {damping: 11, stiffness: 170, mass: 0.7}});
const kb = (frame: number, dur: number) =>
  1 + interpolate(frame, [0, dur], [0, 0.14]);          // ken-burns zoom

// Diagonal shine sweep across a card after it lands.
const Shine: React.FC<{frame: number; f0: number}> = ({frame, f0}) => {
  const t = interpolate(frame - f0, [10, 34], [-60, 160],
                        {extrapolateLeft: 'clamp',
                         extrapolateRight: 'clamp'});
  if (t <= -60 || t >= 160) return null;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden',
                 borderRadius: 'inherit', pointerEvents: 'none'}}>
      <div style={{position: 'absolute', top: '-30%', bottom: '-30%',
                   left: `${t}%`, width: '26%',
                   background: 'linear-gradient(105deg, transparent,' +
                     ' rgba(255,255,255,0.34), transparent)',
                   transform: 'rotate(8deg)'}}/>
    </div>
  );
};

// Red ring that flashes outward when an element lands.
const RingFlash: React.FC<{frame: number; f0: number}> = ({frame, f0}) => {
  const p = interpolate(frame - f0, [4, 26], [0, 1],
                        {extrapolateLeft: 'clamp',
                         extrapolateRight: 'clamp'});
  if (p >= 1) return null;
  return (
    <div style={{position: 'absolute', inset: -14 - p * 44,
                 border: `${4 - p * 3}px solid ${V5.accent}`,
                 borderRadius: 30, opacity: 1 - p,
                 pointerEvents: 'none'}}/>
  );
};

// ------------------------------------------------ PhotoTiles2 (big + fx)
// Real photos, big labels, ken-burns, overshoot entrance, ring flash, shine.
export const PhotoTiles2: React.FC<{
  title: string;
  tiles: {src: string; label: string; atMs: number}[];
}> = ({title, tiles}) => {
  const {frame, fps, dur} = useT();
  const tp = pop(frame, 3, fps);
  const n = tiles.length;
  const tw = n <= 2 ? 700 : n === 3 ? 560 : 420;
  const th = n <= 3 ? 500 : 420;
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center', gap: 56}}>
        <div style={{opacity: tp,
                     transform: `translateY(${(1 - tp) * -40}px)`,
                     color: '#fff', fontFamily: V5.font, fontWeight: 900,
                     fontSize: 88, letterSpacing: 4,
                     textTransform: 'uppercase',
                     textShadow: `0 0 46px ${V5.accentSoft}`}}>
          {title}
          <div style={{height: 8, background: V5.accent, borderRadius: 4,
                       marginTop: 10,
                       width: `${tp * 100}%`,
                       boxShadow: `0 0 26px ${V5.accent}`}}/>
        </div>
        <div style={{display: 'flex', gap: 44, alignItems: 'center'}}>
          {tiles.map((t, i) => {
            const f0 = Math.round((t.atMs / 1000) * fps);
            const p = pop(frame, f0, fps);
            const drift = Math.sin(frame / 26 + i * 1.7) * 5;
            return (
              <div key={i} style={{
                position: 'relative',
                opacity: Math.min(1, p * 1.2),
                transform: `scale(${p}) translateY(${(1 - p) * 90 +
                  drift}px) rotate(${(1 - p) * (i % 2 ? 7 : -7)}deg)`,
                width: tw, borderRadius: 26, overflow: 'hidden',
                background: '#101014',
                border: '2px solid rgba(255,255,255,0.13)',
                boxShadow: `0 26px 70px rgba(0,0,0,0.55),
                            0 0 ${34 + Math.sin(frame / 12) * 12}px
                            ${V5.accentSoft}`,
              }}>
                <div style={{height: th, overflow: 'hidden'}}>
                  <Img src={t.src} style={{
                    width: '100%', height: '100%', objectFit: 'cover',
                    transform: `scale(${kb(Math.max(frame - f0, 0), dur)})`,
                  }}/>
                </div>
                <div style={{height: 7, background: V5.accent,
                             boxShadow: `0 0 22px ${V5.accent}`}}/>
                <div style={{padding: '26px 22px', textAlign: 'center',
                             color: '#fff', fontFamily: V5.font,
                             fontWeight: 800, fontSize: 54,
                             lineHeight: 1.12}}>
                  {t.label}
                </div>
                <Shine frame={frame} f0={f0}/>
                <RingFlash frame={frame} f0={f0}/>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ PhotoBurst (center + orbit)
// Replaces IconBurst: photos punch in around a glowing center label.
export const PhotoBurst: React.FC<{
  label: string;
  satellites: {src: string; label: string; atMs: number}[];
  labelAtMs?: number;
}> = ({label, satellites, labelAtMs = 300}) => {
  const {frame, fps, dur} = useT();
  const n = satellites.length;
  const lp = pop(frame, Math.round((labelAtMs / 1000) * fps), fps);
  const R = n > 5 ? 700 : 500;
  const cw = n > 5 ? 295 : 400;
  const ch = n > 5 ? 200 : 300;
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center'}}>
        {/* pulsing center label */}
        <div style={{
          position: 'absolute', zIndex: 3,
          opacity: lp, transform: `scale(${lp})`,
          background: 'rgba(12,12,15,0.92)',
          border: `3px solid ${V5.accent}`,
          borderRadius: 24, padding: '34px 60px',
          color: '#fff', fontFamily: V5.font, fontWeight: 900,
          fontSize: 66, letterSpacing: 3, textTransform: 'uppercase',
          textAlign: 'center', maxWidth: 760,
          boxShadow: `0 0 ${56 + Math.sin(frame / 9) * 22}px ${V5.accent}`,
        }}>{label}</div>
        {satellites.map((s, i) => {
          const f0 = Math.round((s.atMs / 1000) * fps);
          const p = pop(frame, f0, fps);
          const a = (i / n) * Math.PI * 2 - Math.PI / 2;
          const x = Math.cos(a) * R * (0.6 + 0.4 * p);
          const y = Math.sin(a) * R * (n > 5 ? 0.52 : 0.62) *
            (0.6 + 0.4 * p);
          const drift = Math.sin(frame / 24 + i * 2.1) * 6;
          return (
            <div key={i} style={{
              position: 'absolute',
              opacity: Math.min(1, p * 1.3),
              transform: `translate(${x}px, ${y + drift}px) scale(${p})
                          rotate(${(1 - p) * (i % 2 ? 10 : -10)}deg)`,
              width: cw, borderRadius: 20, overflow: 'hidden',
              background: '#101014',
              border: '2px solid rgba(255,255,255,0.14)',
              boxShadow: `0 18px 50px rgba(0,0,0,0.6),
                          0 0 30px ${V5.accentSoft}`,
            }}>
              <div style={{height: ch, overflow: 'hidden'}}>
                <Img src={s.src} style={{width: '100%', height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${kb(Math.max(frame - f0, 0), dur)})`,
                }}/>
              </div>
              <div style={{padding: '16px 14px', textAlign: 'center',
                           color: '#fff', fontFamily: V5.font,
                           fontWeight: 800, fontSize: 37,
                           borderTop: `5px solid ${V5.accent}`}}>
                {s.label}
              </div>
              <Shine frame={frame} f0={f0}/>
              <RingFlash frame={frame} f0={f0}/>
            </div>
          );
        })}
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ StepCards2 (photo steps)
export const StepCards2: React.FC<{
  title: string;
  steps: {text: string; src?: string; atMs: number}[];
}> = ({title, steps}) => {
  const {frame, fps, dur} = useT();
  const tp = pop(frame, 3, fps);
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center', gap: 48}}>
        <div style={{opacity: tp,
                     transform: `translateY(${(1 - tp) * -40}px)`,
                     color: '#fff', fontFamily: V5.font, fontWeight: 900,
                     fontSize: 84, letterSpacing: 4,
                     textTransform: 'uppercase',
                     textShadow: `0 0 40px ${V5.accentSoft}`}}>{title}</div>
        <div style={{display: 'flex', flexDirection: 'column', gap: 34}}>
          {steps.map((s, i) => {
            const f0 = Math.round((s.atMs / 1000) * fps);
            const p = pop(frame, f0, fps);
            return (
              <div key={i} style={{
                position: 'relative',
                opacity: Math.min(1, p * 1.25),
                transform: `translateX(${(1 - p) * (i % 2 ? 320 : -320)}px)
                            scale(${0.9 + p * 0.1})`,
                display: 'flex', alignItems: 'center', gap: 0,
                background: '#131318',
                borderRadius: 22, overflow: 'hidden',
                border: '2px solid rgba(255,255,255,0.12)',
                boxShadow: `0 18px 52px rgba(0,0,0,0.55),
                            0 0 26px ${V5.accentSoft}`,
                width: 1240, height: 172,
              }}>
                <div style={{width: 130, alignSelf: 'stretch',
                             background: V5.accent, display: 'flex',
                             alignItems: 'center', justifyContent: 'center',
                             color: '#fff', fontFamily: V5.font,
                             fontWeight: 900, fontSize: 84,
                             boxShadow: `0 0 34px ${V5.accent}`}}>
                  {i + 1}
                </div>
                <div style={{flex: 1, padding: '0 40px', color: '#fff',
                             fontFamily: V5.font, fontWeight: 800,
                             fontSize: 56, lineHeight: 1.08}}>
                  {s.text}
                </div>
                {s.src ? (
                  <div style={{width: 300, alignSelf: 'stretch',
                               overflow: 'hidden'}}>
                    <Img src={s.src} style={{width: '100%',
                      height: '100%', objectFit: 'cover',
                      transform:
                        `scale(${kb(Math.max(frame - f0, 0), dur)})`}}/>
                  </div>
                ) : null}
                <Shine frame={frame} f0={f0}/>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ Checklist2 (photo checks)
export const Checklist2: React.FC<{
  title: string;
  items: {text: string; src?: string; atMs: number}[];
}> = ({title, items}) => {
  const {frame, fps, dur} = useT();
  const tp = pop(frame, 3, fps);
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center', gap: 46}}>
        <div style={{opacity: tp,
                     transform: `translateY(${(1 - tp) * -40}px)`,
                     color: '#fff', fontFamily: V5.font, fontWeight: 900,
                     fontSize: 84, letterSpacing: 4,
                     textTransform: 'uppercase',
                     textShadow: `0 0 40px ${V5.accentSoft}`}}>{title}</div>
        <div style={{display: 'flex', flexDirection: 'column', gap: 30}}>
          {items.map((it, i) => {
            const f0 = Math.round((it.atMs / 1000) * fps);
            const p = pop(frame, f0, fps);
            const draw = interpolate(frame - f0, [4, 16], [0, 1],
                                     {extrapolateLeft: 'clamp',
                                      extrapolateRight: 'clamp'});
            return (
              <div key={i} style={{
                position: 'relative',
                opacity: Math.min(1, p * 1.25),
                transform: `translateX(${(1 - p) * -280}px)`,
                display: 'flex', alignItems: 'center', gap: 36,
                background: '#131318', borderRadius: 22,
                border: '2px solid rgba(255,255,255,0.12)',
                boxShadow: `0 16px 48px rgba(0,0,0,0.5),
                            0 0 24px ${V5.accentSoft}`,
                width: 1200, padding: '22px 40px', overflow: 'hidden',
              }}>
                <svg width={84} height={84} viewBox="0 0 48 48">
                  <rect x="4" y="4" width="40" height="40" rx="10"
                        fill="none" stroke={V5.accent} strokeWidth="4.5"/>
                  <path d="M14 25 L21 33 L35 16" fill="none" stroke="#fff"
                        strokeWidth="5.5" strokeLinecap="round"
                        strokeDasharray="40"
                        strokeDashoffset={40 * (1 - draw)}/>
                </svg>
                <div style={{flex: 1, color: '#fff', fontFamily: V5.font,
                             fontWeight: 800, fontSize: 56,
                             lineHeight: 1.08}}>{it.text}</div>
                {it.src ? (
                  <div style={{width: 260, height: 130, borderRadius: 16,
                               overflow: 'hidden', flexShrink: 0}}>
                    <Img src={it.src} style={{width: '100%',
                      height: '100%', objectFit: 'cover',
                      transform:
                        `scale(${kb(Math.max(frame - f0, 0), dur)})`}}/>
                  </div>
                ) : null}
                <Shine frame={frame} f0={f0}/>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ ChapterChip (alpha overlay)
// Small top-left chapter marker composited on the first beat of a section.
export const ChapterChip: React.FC<{part: string; title: string}> = (
    {part, title}) => {
  const {frame, fps, dur} = useT();
  const p = pop(frame, 4, fps);
  const out = interpolate(frame, [dur - 14, dur - 2], [1, 0],
                          {extrapolateLeft: 'clamp',
                           extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <div style={{
        position: 'absolute', left: 64, top: 60,
        opacity: Math.min(p, out),
        transform: `translateX(${(1 - p) * -120}px)`,
        display: 'flex', alignItems: 'center', gap: 0,
        borderRadius: 16, overflow: 'hidden',
        boxShadow: `0 10px 34px rgba(0,0,0,0.55)`,
      }}>
        <div style={{background: V5.accent, color: '#fff',
                     fontFamily: V5.font, fontWeight: 900, fontSize: 34,
                     letterSpacing: 2, padding: '14px 22px'}}>{part}</div>
        <div style={{background: 'rgba(10,10,13,0.9)', color: '#fff',
                     fontFamily: V5.font, fontWeight: 800, fontSize: 34,
                     letterSpacing: 3, padding: '14px 26px',
                     textTransform: 'uppercase'}}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};
