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

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames, t: frame / fps};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps, config: {damping: 14, stiffness: 160,
                                           mass: 0.6}});

// Dark stage with radiating accent circles (the reference's signature bg)
export const Stage: React.FC<{children?: React.ReactNode;
                              accent?: string}> = ({children, accent}) => {
  const {frame} = useT();
  const a = accent ?? V5.accent;
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 60%, ${V5.bg1}, ${V5.bg0})`,
      overflow: 'hidden'}}>
      {[420, 680, 940].map((r, i) => (
        <div key={i} style={{
          position: 'absolute', left: '50%', top: '50%',
          width: r * 2, height: r * 2, marginLeft: -r, marginTop: -r,
          borderRadius: r, border: `1.5px solid ${V5.ring}`,
          transform: `scale(${1 + 0.012 * Math.sin(frame / 18 + i)})`,
        }} />
      ))}
      <div style={{position: 'absolute', left: '50%', top: '58%',
        width: 900, height: 500, marginLeft: -450, marginTop: -250,
        background: `radial-gradient(ellipse, ${V5.accentSoft}, transparent 65%)`,
        filter: 'blur(30px)'}} />
      {children}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- SiteZoom
// Real website screenshot: slow zoom toward a focus point, then a YELLOW
// marker sweeps across the key phrase (highlightRect in % of image).
export const SiteZoom: React.FC<{
  src: string;
  zoomFrom?: number; zoomTo?: number;
  focusX?: number; focusY?: number;           // 0-1 zoom target
  highlightRect?: {x: number; y: number; w: number; h: number} | null;
  highlightAtMs?: number;
  label?: string;
  accent?: string;
}> = ({src, zoomFrom = 1.0, zoomTo = 1.6, focusX = 0.5, focusY = 0.35,
       highlightRect = null, highlightAtMs = 900, label, accent}) => {
  const {frame, fps, dur} = useT();
  const z = interpolate(frame, [0, dur], [zoomFrom, zoomTo]);
  const hl = highlightRect
    ? interpolate(frame, [msF(highlightAtMs, fps),
                          msF(highlightAtMs, fps) + Math.round(fps * 0.6)],
                  [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : 0;
  const enter = pop(frame, 0, fps);
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          width: 1560, height: 880, borderRadius: V5.radius,
          overflow: 'hidden', background: '#fff',
          border: `1px solid rgba(255,255,255,0.15)`,
          boxShadow: `0 40px 120px rgba(0,0,0,0.6), 0 0 80px ${V5.accentSoft}`,
          opacity: enter, transform: `scale(${0.94 + enter * 0.06})`,
        }}>
          <div style={{height: 54, background: '#1b1b22', display: 'flex',
                       alignItems: 'center', gap: 8, padding: '0 18px'}}>
            {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
              <div key={c} style={{width: 14, height: 14, borderRadius: 7,
                                   background: c}} />
            ))}
            {label ? (
              <div style={{marginLeft: 16, fontFamily: V5.fontBody,
                           fontSize: 20, color: '#bbb',
                           background: '#26262e', borderRadius: 8,
                           padding: '6px 18px'}}>{label}</div>
            ) : null}
          </div>
          <div style={{position: 'relative', width: '100%',
                       height: 880 - 54, overflow: 'hidden'}}>
            <Img src={src} style={{
              width: '100%',
              transformOrigin: `${focusX * 100}% ${focusY * 100}%`,
              transform: `scale(${z})`,
            }} />
            {highlightRect ? (
              <div style={{
                position: 'absolute',
                left: `${highlightRect.x}%`, top: `${highlightRect.y}%`,
                width: `${highlightRect.w * hl}%`,
                height: `${highlightRect.h}%`,
                background: V5.marker, mixBlendMode: 'multiply',
                borderRadius: 6,
                transform: 'rotate(-0.6deg)',
              }} />
            ) : null}
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- IconBurst
// Central glowing emoji/icon; satellites fly in with connector lines pointing
// at it; bottom label announces.
export const IconBurst: React.FC<{
  center: string;                    // emoji or short text
  satellites?: {icon: string; label?: string; atMs: number}[];
  label?: string;
  labelAtMs?: number;
  accent?: string;
}> = ({center, satellites = [], label, labelAtMs = 1600, accent}) => {
  const {frame, fps} = useT();
  const c = pop(frame, 4, fps);
  const R = 330;
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          width: 220, height: 220, borderRadius: 110,
          background: `radial-gradient(circle at 35% 30%, #23232c, #101014)`,
          border: `2px solid ${accent ?? V5.accent}`,
          boxShadow: `0 0 90px ${V5.accentSoft}, inset 0 0 40px rgba(0,0,0,.6)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 108, transform: `scale(${c})`,
        }}>{center}</div>
        {satellites.map((s, i) => {
          const ang = (-90 + (360 / Math.max(satellites.length, 1)) * i)
            * Math.PI / 180;
          const x = Math.cos(ang) * R;
          const y = Math.sin(ang) * R * 0.72;
          const p = frame >= msF(s.atMs, fps)
            ? pop(frame, msF(s.atMs, fps), fps) : 0;
          const lineLen = Math.hypot(x, y) - 190;
          const lineAng = Math.atan2(-y, -x) * 180 / Math.PI;
          return (
            <React.Fragment key={i}>
              <div style={{
                position: 'absolute',
                transform: `translate(${x}px, ${y}px) scale(${p})`,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', gap: 8, opacity: p,
              }}>
                <div style={{
                  width: 120, height: 120, borderRadius: 26,
                  background: '#191920',
                  border: '1.5px solid rgba(255,255,255,0.18)',
                  boxShadow: `0 12px 40px rgba(0,0,0,.5)`,
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 58,
                }}>{s.icon}</div>
                {s.label ? (
                  <div style={{fontFamily: V5.fontBody, fontSize: 24,
                               color: V5.inkDim}}>{s.label}</div>
                ) : null}
              </div>
              <div style={{
                position: 'absolute',
                width: Math.max(lineLen, 0) * p, height: 3,
                background: `linear-gradient(90deg, transparent, ${accent ?? V5.accent})`,
                transform: `translate(${x * 0.5}px, ${y * 0.5}px) ` +
                           `rotate(${lineAng}deg)`,
                opacity: 0.8 * p,
              }} />
            </React.Fragment>
          );
        })}
        {label ? (
          <div style={{
            position: 'absolute', bottom: 110,
            fontFamily: V5.fontDisplay, fontSize: 46, color: V5.ink,
            letterSpacing: 1, textTransform: 'uppercase',
            opacity: frame >= msF(labelAtMs, fps)
              ? pop(frame, msF(labelAtMs, fps), fps) : 0,
            textShadow: `0 4px 30px rgba(0,0,0,.8)`,
          }}>{label}</div>
        ) : null}
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- PeopleRow
// Person icons multiplying with a bottom caption ("by users and non-users").
export const PeopleRow: React.FC<{
  count?: number;
  startMs?: number; stepMs?: number;
  caption?: string;
  highlightIndex?: number;
  accent?: string;
}> = ({count = 5, startMs = 300, stepMs = 320, caption,
       highlightIndex = -1, accent}) => {
  const {frame, fps} = useT();
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', gap: 44}}>
          {Array.from({length: count}, (_, i) => {
            const f0 = msF(startMs + stepMs * i, fps);
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            const hot = i === highlightIndex;
            return (
              <div key={i} style={{
                fontSize: 120, transform: `scale(${p})`, opacity: p,
                filter: hot ? 'none' : 'grayscale(35%)',
                textShadow: hot
                  ? `0 0 60px ${accent ?? V5.accent}` : 'none',
              }}>🧍</div>
            );
          })}
        </div>
        {caption ? (
          <div style={{
            position: 'absolute', bottom: 120,
            fontFamily: V5.fontDisplay, fontSize: 44, color: V5.ink,
            textTransform: 'uppercase', letterSpacing: 1,
            opacity: frame >= msF(startMs + stepMs * count + 200, fps)
              ? pop(frame, msF(startMs + stepMs * count + 200, fps), fps) : 0,
          }}>{caption}</div>
        ) : null}
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- BarsRise
// Red bars rising with value counters (macros, calories, comparisons).
export const BarsRise: React.FC<{
  bars: {label: string; value: number; display?: string}[];
  title?: string;
  accent?: string;
}> = ({bars, title, accent}) => {
  const {frame, fps} = useT();
  const maxV = Math.max(...bars.map((b) => b.value));
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        {title ? (
          <div style={{position: 'absolute', top: 120,
                       fontFamily: V5.fontDisplay, fontSize: 52,
                       color: V5.ink, textTransform: 'uppercase',
                       letterSpacing: 2, opacity: pop(frame, 0, fps)}}>
            {title}</div>
        ) : null}
        <div style={{display: 'flex', gap: 90, alignItems: 'flex-end',
                     height: 520, marginTop: 60}}>
          {bars.map((b, i) => {
            const f0 = Math.round(fps * (0.3 + i * 0.25));
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            const h = (b.value / maxV) * 420 * p;
            const shown = Math.round(b.value * Math.min(p, 1));
            return (
              <div key={i} style={{display: 'flex', flexDirection: 'column',
                                   alignItems: 'center', gap: 16}}>
                <div style={{fontFamily: V5.fontDisplay, fontSize: 44,
                             color: V5.ink, opacity: p}}>
                  {b.display
                    ? b.display.replace(/[0-9][0-9,]*/,
                        shown.toLocaleString('en-US'))
                    : shown.toLocaleString('en-US')}
                </div>
                <div style={{
                  width: 130, height: Math.max(h, 4),
                  background: `linear-gradient(180deg, ${accent ?? V5.accent}, #7a1622)`,
                  borderRadius: 10,
                  boxShadow: `0 0 50px ${V5.accentSoft}`,
                }} />
                <div style={{fontFamily: V5.fontBody, fontSize: 30,
                             color: V5.inkDim}}>{b.label}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- TypeOn
// Search/prompt bar with text typing itself out.
export const TypeOn: React.FC<{
  text: string;
  startMs?: number;
  cps?: number;                       // chars per second
  accent?: string;
}> = ({text, startMs = 400, cps = 24, accent}) => {
  const {frame, fps} = useT();
  const t = Math.max(0, frame / fps - startMs / 1000);
  const n = Math.min(text.length, Math.floor(t * cps));
  const enter = pop(frame, 0, fps);
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          width: 1300, borderRadius: 40, background: '#f6f6f4',
          boxShadow: `0 30px 100px rgba(0,0,0,0.55), 0 0 70px ${V5.accentSoft}`,
          padding: '30px 44px', display: 'flex', alignItems: 'center',
          gap: 24, opacity: enter, transform: `scale(${0.94 + enter * 0.06})`,
        }}>
          <div style={{fontSize: 40, color: '#666'}}>🔍</div>
          <div style={{fontFamily: V5.fontBody, fontSize: 40, color: '#1c1c22',
                       whiteSpace: 'nowrap', overflow: 'hidden'}}>
            {text.slice(0, n)}
            <span style={{opacity: frame % fps < fps / 2 ? 1 : 0}}>|</span>
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- EraCard
// IMDb-style movie era card: poster-ish panel, year badge, physique stats.
export const EraCard: React.FC<{
  year: string; title: string; sub?: string;
  imageSrc?: string;
  stats?: {k: string; v: string}[];
  accent?: string;
}> = ({year, title, sub, imageSrc, stats = [], accent}) => {
  const {frame, fps} = useT();
  const e = pop(frame, 2, fps);
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          display: 'flex', gap: 44, alignItems: 'stretch',
          background: '#15151b', borderRadius: V5.radius,
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: `0 40px 120px rgba(0,0,0,.6), 0 0 80px ${V5.accentSoft}`,
          padding: 36, opacity: e, transform: `translateY(${(1 - e) * 40}px)`,
        }}>
          <div style={{width: 430, height: 560, borderRadius: 12,
                       overflow: 'hidden', background: '#0c0c10',
                       display: 'flex', alignItems: 'center',
                       justifyContent: 'center'}}>
            {imageSrc ? (
              <Img src={imageSrc}
                   style={{width: '100%', height: '100%',
                           objectFit: 'cover'}} />
            ) : (
              <div style={{fontSize: 130}}>🎬</div>
            )}
          </div>
          <div style={{width: 620, display: 'flex', flexDirection: 'column',
                       justifyContent: 'center', gap: 20}}>
            <div style={{alignSelf: 'flex-start',
                         fontFamily: V5.fontDisplay, fontSize: 36,
                         color: '#0c0c10',
                         background: accent ?? V5.accent,
                         borderRadius: 10, padding: '6px 22px'}}>{year}</div>
            <div style={{fontFamily: V5.fontDisplay, fontSize: 62,
                         lineHeight: 1.05, color: V5.ink}}>{title}</div>
            {sub ? (
              <div style={{fontFamily: V5.fontBody, fontSize: 32,
                           color: V5.inkDim}}>{sub}</div>
            ) : null}
            <div style={{display: 'flex', flexDirection: 'column', gap: 12,
                         marginTop: 8}}>
              {stats.map((s, i) => {
                const f0 = Math.round(fps * (0.7 + i * 0.28));
                const p = frame >= f0 ? pop(frame, f0, fps) : 0;
                return (
                  <div key={i} style={{display: 'flex', gap: 16,
                                       opacity: p,
                                       transform:
                                         `translateX(${(1 - p) * -30}px)`}}>
                    <div style={{fontFamily: V5.fontBody, fontSize: 30,
                                 color: V5.inkDim, width: 210}}>{s.k}</div>
                    <div style={{fontFamily: V5.fontDisplay, fontSize: 30,
                                 color: V5.ink}}>{s.v}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ---------------------------------------------------------------- MacroApp
// Nutrition-app mockup: rings/rows filling in for cals/protein/carbs/fats.
export const MacroApp: React.FC<{
  cals?: string;
  rows?: {label: string; value: string; frac: number}[];
  accent?: string;
}> = ({cals = '2,600-3,200',
       rows = [{label: 'Protein', value: '200-250 g', frac: 0.9},
               {label: 'Carbs', value: '150-300 g', frac: 0.65},
               {label: 'Fats', value: '70-100 g', frac: 0.4}],
       accent}) => {
  const {frame, fps} = useT();
  const e = pop(frame, 2, fps);
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          width: 760, borderRadius: 34, background: '#101016',
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: `0 40px 120px rgba(0,0,0,.65), 0 0 80px ${V5.accentSoft}`,
          padding: '44px 52px', opacity: e,
          transform: `scale(${0.94 + e * 0.06})`,
        }}>
          <div style={{fontFamily: V5.fontBody, fontSize: 26,
                       color: V5.inkDim, letterSpacing: 3,
                       textTransform: 'uppercase'}}>Daily target</div>
          <div style={{fontFamily: V5.fontDisplay, fontSize: 84,
                       color: V5.ink, margin: '6px 0 8px'}}>{cals}</div>
          <div style={{fontFamily: V5.fontBody, fontSize: 28,
                       color: V5.inkDim, marginBottom: 30}}>calories</div>
          {rows.map((r, i) => {
            const f0 = Math.round(fps * (0.5 + i * 0.3));
            const p = frame >= f0 ? pop(frame, f0, fps) : 0;
            return (
              <div key={i} style={{marginBottom: 26, opacity: p}}>
                <div style={{display: 'flex',
                             justifyContent: 'space-between',
                             fontFamily: V5.fontBody, fontSize: 30,
                             color: V5.ink, marginBottom: 10}}>
                  <span>{r.label}</span>
                  <span style={{fontFamily: V5.fontDisplay}}>{r.value}</span>
                </div>
                <div style={{height: 16, borderRadius: 8,
                             background: '#22222a'}}>
                  <div style={{height: 16, borderRadius: 8,
                               width: `${r.frac * 100 * Math.min(p, 1)}%`,
                               background: `linear-gradient(90deg, ${accent ?? V5.accent}, #ff8a5c)`,
                               boxShadow: `0 0 30px ${V5.accentSoft}`}} />
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
