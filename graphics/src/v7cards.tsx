import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {V5, msF} from './tokens_v5';
import {Stage} from './v5cards';

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps, config: {damping: 14, stiffness: 160,
                                           mass: 0.6}});

// ------------------------------------------------- IndexCards (square deal)
// Square index cards dealt one by one with a slight rotation fan.
export const IndexCards: React.FC<{
  title?: string;
  cards: {text: string; icon?: string; atMs: number}[];
  accent?: string;
}> = ({title, cards, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  return (
    <Stage accent={a}>
      {title ? (
        <div style={{position: 'absolute', top: 100, width: '100%',
                     textAlign: 'center', fontFamily: V5.fontDisplay,
                     fontSize: 48, color: V5.ink, letterSpacing: 2,
                     textTransform: 'uppercase',
                     opacity: pop(frame, 2, fps)}}>{title}</div>
      ) : null}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', gap: 40}}>
          {cards.map((c, i) => {
            const f0 = msF(c.atMs, fps);
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            const rot = (i - (cards.length - 1) / 2) * 3;
            return (
              <div key={i} style={{
                width: 300, height: 340, borderRadius: 14,
                background: '#f7f4ec',
                boxShadow: '0 24px 70px rgba(0,0,0,.55)',
                transform: `rotate(${rot}deg) translateY(${(1 - p) * 120}px)`,
                opacity: p,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 20,
                borderTop: `12px solid ${a}`,
              }}>
                {c.icon ? <div style={{fontSize: 84}}>{c.icon}</div> : null}
                <div style={{fontFamily: V5.fontDisplay, fontSize: 32,
                             color: '#1b1b1f', textAlign: 'center',
                             padding: '0 22px', lineHeight: 1.25}}>
                  {c.text}</div>
                <div style={{width: 60, height: 5, background: a,
                             borderRadius: 3}} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------- Checklist (checkmarks)
export const Checklist: React.FC<{
  title?: string;
  items: {text: string; atMs: number}[];
  accent?: string;
}> = ({title, items, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  return (
    <Stage accent={a}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          width: 1000, borderRadius: 22, background: '#15151b',
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: `0 36px 110px rgba(0,0,0,.6), 0 0 70px ${V5.accentSoft}`,
          padding: '44px 56px',
        }}>
          {title ? (
            <div style={{fontFamily: V5.fontDisplay, fontSize: 44,
                         color: V5.ink, textTransform: 'uppercase',
                         letterSpacing: 2, marginBottom: 30,
                         opacity: pop(frame, 2, fps)}}>{title}</div>
          ) : null}
          {items.map((it, i) => {
            const f0 = msF(it.atMs, fps);
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'center',
                                   gap: 24, marginBottom: 22, opacity: p,
                                   transform:
                                     `translateX(${(1 - p) * -40}px)`}}>
                <svg width={54} height={54} viewBox="0 0 54 54">
                  <rect x={3} y={3} width={48} height={48} rx={12}
                        fill="none" stroke={a} strokeWidth={4} />
                  <path d="M 14 28 L 24 38 L 41 17" fill="none"
                        stroke={a} strokeWidth={6} strokeLinecap="round"
                        strokeDasharray={50}
                        strokeDashoffset={50 - 50 * Math.min(p, 1)} />
                </svg>
                <div style={{fontFamily: V5.fontBody, fontSize: 36,
                             fontWeight: 600, color: V5.ink}}>{it.text}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------- PhotoTiles (real images)
// Each named item = its own photo tile popping when the word is spoken.
export const PhotoTiles: React.FC<{
  title?: string;
  tiles: {src: string; label: string; atMs: number}[];
  accent?: string;
}> = ({title, tiles, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const w = tiles.length > 3 ? 380 : 440;
  return (
    <Stage accent={a}>
      {title ? (
        <div style={{position: 'absolute', top: 100, width: '100%',
                     textAlign: 'center', fontFamily: V5.fontDisplay,
                     fontSize: 48, color: V5.ink, letterSpacing: 2,
                     textTransform: 'uppercase',
                     opacity: pop(frame, 2, fps)}}>{title}</div>
      ) : null}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', gap: 36, flexWrap: 'wrap',
                     justifyContent: 'center', maxWidth: 1700}}>
          {tiles.map((t, i) => {
            const f0 = msF(t.atMs, fps);
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            return (
              <div key={i} style={{
                width: w, borderRadius: 18, overflow: 'hidden',
                background: '#15151b',
                border: '1px solid rgba(255,255,255,0.16)',
                boxShadow: `0 26px 80px rgba(0,0,0,.55)`,
                transform: `scale(${p}) rotate(${(i % 2 ? 1 : -1) * 1.5}deg)`,
                opacity: p,
              }}>
                <div style={{height: w * 0.66, overflow: 'hidden'}}>
                  <Img src={t.src} style={{width: '100%', height: '100%',
                                           objectFit: 'cover'}} />
                </div>
                <div style={{padding: '16px 20px',
                             borderTop: `6px solid ${a}`,
                             fontFamily: V5.fontDisplay, fontSize: 30,
                             color: V5.ink,
                             textAlign: 'center'}}>{t.label}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------- StepCards (numbered)
export const StepCards: React.FC<{
  title?: string;
  steps: {text: string; atMs: number}[];
  accent?: string;
}> = ({title, steps, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  return (
    <Stage accent={a}>
      {title ? (
        <div style={{position: 'absolute', top: 100, width: '100%',
                     textAlign: 'center', fontFamily: V5.fontDisplay,
                     fontSize: 48, color: V5.ink, letterSpacing: 2,
                     textTransform: 'uppercase',
                     opacity: pop(frame, 2, fps)}}>{title}</div>
      ) : null}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', flexDirection: 'column', gap: 24,
                     width: 1080}}>
          {steps.map((st, i) => {
            const f0 = msF(st.atMs, fps);
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'stretch', gap: 0,
                opacity: p,
                transform: `translateX(${(1 - p) * (i % 2 ? 70 : -70)}px)`,
                borderRadius: 16, overflow: 'hidden',
                boxShadow: '0 20px 60px rgba(0,0,0,.5)',
              }}>
                <div style={{width: 110, background: a, display: 'flex',
                             alignItems: 'center', justifyContent: 'center',
                             fontFamily: V5.fontDisplay, fontSize: 54,
                             color: '#0d0d12'}}>{i + 1}</div>
                <div style={{flex: 1, background: '#191921',
                             border: '1px solid rgba(255,255,255,0.12)',
                             borderLeft: 'none', display: 'flex',
                             alignItems: 'center', padding: '22px 34px',
                             fontFamily: V5.fontBody, fontSize: 34,
                             fontWeight: 600, color: V5.ink}}>{st.text}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------- ArrowCallout (ALPHA)
// Overlay on footage: arrow pointing at a person + name/age card.
export const ArrowCallout: React.FC<{
  name: string; sub?: string;
  targetX?: number; targetY?: number;      // 0-1 where the arrow points
  cardX?: number; cardY?: number;          // 0-1 card anchor
  atMs?: number;
  accent?: string;
}> = ({name, sub, targetX = 0.5, targetY = 0.35, cardX = 0.74,
       cardY = 0.72, atMs = 300, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const p = frame >= msF(atMs, fps) ? pop(frame, msF(atMs, fps), fps) : 0;
  const W = 1920, H = 1080;
  const tx = targetX * W, ty = targetY * H;
  const cx = cardX * W, cy = cardY * H;
  const bob = Math.sin(frame / 9) * 6;
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <marker id="arrhead" markerWidth="12" markerHeight="12"
                  refX="9" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill={a} />
          </marker>
        </defs>
        <path d={`M ${cx} ${cy - 20} Q ${(cx + tx) / 2 + 60} ` +
                 `${(cy + ty) / 2} ${tx + 14} ${ty + 12 + bob}`}
              fill="none" stroke={a} strokeWidth={7 * p}
              strokeLinecap="round" markerEnd="url(#arrhead)"
              opacity={p}
              style={{filter: `drop-shadow(0 0 12px ${a})`}} />
      </svg>
      <div style={{
        position: 'absolute', left: cx - 210, top: cy - 10, width: 420,
        background: 'rgba(12,12,16,0.88)', borderRadius: 14,
        border: `1px solid rgba(255,255,255,0.2)`,
        borderLeft: `10px solid ${a}`,
        boxShadow: '0 18px 60px rgba(0,0,0,.6)',
        padding: '18px 26px', opacity: p,
        transform: `translateY(${(1 - p) * 30}px)`,
      }}>
        <div style={{fontFamily: V5.fontDisplay, fontSize: 38,
                     color: V5.ink}}>{name}</div>
        {sub ? (
          <div style={{fontFamily: V5.fontBody, fontSize: 26,
                       color: V5.inkDim, marginTop: 4}}>{sub}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------- InstaCard (3D profile)
// Realistic Instagram profile mock with 3D tilt - real handle + real photos.
export const InstaCard: React.FC<{
  handle: string; name: string; bio: string;
  avatarSrc: string;
  gridSrcs?: string[];
  accent?: string;
}> = ({handle, name, bio, avatarSrc, gridSrcs = [], accent}) => {
  const {frame, fps, dur} = useT();
  const a = accent ?? V5.accent;
  const e = pop(frame, 4, fps);
  const tilt = interpolate(frame, [0, dur], [16, 4]);
  const swing = Math.sin(frame / 26) * 3;
  return (
    <Stage accent={a}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center',
                            perspective: 1600}}>
        <div style={{
          width: 700, borderRadius: 34, background: '#fff',
          overflow: 'hidden',
          boxShadow: `0 60px 140px rgba(0,0,0,.7), 0 0 90px ${V5.accentSoft}`,
          transform: `rotateY(${tilt + swing}deg) rotateX(4deg) ` +
                     `scale(${0.92 + e * 0.08})`,
          opacity: e,
        }}>
          <div style={{display: 'flex', alignItems: 'center', gap: 10,
                       padding: '18px 24px',
                       borderBottom: '1px solid #eee'}}>
            <div style={{fontFamily: V5.fontBody, fontWeight: 700,
                         fontSize: 30, color: '#111'}}>{handle}</div>
            <div style={{color: '#3897f0', fontSize: 26}}>✔</div>
          </div>
          <div style={{display: 'flex', gap: 30, padding: '22px 26px',
                       alignItems: 'center'}}>
            <div style={{width: 150, height: 150, borderRadius: 75,
                         overflow: 'hidden',
                         border: `4px solid ${a}`}}>
              <Img src={avatarSrc} style={{width: '100%', height: '100%',
                                           objectFit: 'cover'}} />
            </div>
            <div>
              <div style={{fontFamily: V5.fontBody, fontWeight: 700,
                           fontSize: 30, color: '#111'}}>{name}</div>
              <div style={{fontFamily: V5.fontBody, fontSize: 24,
                           color: '#333', maxWidth: 420,
                           marginTop: 6}}>{bio}</div>
              <div style={{marginTop: 14, background: '#3897f0',
                           color: '#fff', borderRadius: 10,
                           fontFamily: V5.fontBody, fontWeight: 700,
                           fontSize: 26, padding: '8px 0', width: 220,
                           textAlign: 'center'}}>Follow</div>
            </div>
          </div>
          <div style={{display: 'grid',
                       gridTemplateColumns: 'repeat(3, 1fr)', gap: 3}}>
            {gridSrcs.slice(0, 6).map((g, i) => {
              const p = pop(frame, Math.round(fps * (0.5 + i * 0.15)), fps);
              return (
                <div key={i} style={{aspectRatio: '1', overflow: 'hidden',
                                     opacity: p}}>
                  <Img src={g} style={{width: '100%', height: '100%',
                                       objectFit: 'cover'}} />
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
