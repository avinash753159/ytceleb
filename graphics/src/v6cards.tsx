import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {V5} from './tokens_v5';
import {Stage} from './v5cards';

// V6: SEMANTIC stat cards - each design matches what the number MEANS.
// No design may repeat back-to-back in the timeline (enforced by builder).

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps, config: {damping: 14, stiffness: 160,
                                           mass: 0.6}});
const P = (frame: number, fps: number, sec: number, from: number,
           to: number) =>
  interpolate(frame, [Math.round(sec * fps), Math.round((sec + 0.9) * fps)],
              [from, to],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

const Title: React.FC<{t: string; f?: number}> = ({t, f = 1}) => (
  <div style={{position: 'absolute', top: 110, width: '100%',
               textAlign: 'center', fontFamily: V5.fontDisplay,
               fontSize: 50, color: V5.ink, letterSpacing: 2,
               textTransform: 'uppercase', opacity: f}}>{t}</div>
);

// -------------------------------------------------- DonutGauge (percent)
export const DonutGauge: React.FC<{
  pct: number; title: string; sub?: string; accent?: string;
}> = ({pct, title, sub, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const p = P(frame, fps, 0.4, 0, pct);
  const R = 190, C = 2 * Math.PI * R;
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <svg width={520} height={520}>
          <circle cx={260} cy={260} r={R} fill="none" stroke="#26262e"
                  strokeWidth={44} />
          <circle cx={260} cy={260} r={R} fill="none" stroke={a}
                  strokeWidth={44} strokeLinecap="round"
                  strokeDasharray={`${(p / 100) * C} ${C}`}
                  transform="rotate(-90 260 260)"
                  style={{filter: `drop-shadow(0 0 24px ${a})`}} />
          <text x={260} y={250} textAnchor="middle" fill={V5.ink}
                fontFamily={V5.fontDisplay} fontSize={110}>
            {Math.round(p)}%</text>
          {sub ? (
            <text x={260} y={310} textAnchor="middle" fill={V5.inkDim}
                  fontFamily={V5.fontBody} fontSize={30}>{sub}</text>
          ) : null}
        </svg>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- ClockRing (sleep/hours)
export const ClockRing: React.FC<{
  fromH: number; toH: number; title: string; accent?: string;
}> = ({fromH, toH, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const sweep = P(frame, fps, 0.4, 0, (toH / 12) * 360);
  const R = 180, C = 2 * Math.PI * R;
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <svg width={520} height={520}>
          {Array.from({length: 12}, (_, i) => {
            const ang = (i / 12) * 2 * Math.PI - Math.PI / 2;
            return <circle key={i} cx={260 + Math.cos(ang) * 218}
                           cy={260 + Math.sin(ang) * 218} r={6}
                           fill={V5.inkDim} />;
          })}
          <circle cx={260} cy={260} r={R} fill="none" stroke="#26262e"
                  strokeWidth={36} />
          <circle cx={260} cy={260} r={R} fill="none" stroke={a}
                  strokeWidth={36} strokeLinecap="round"
                  strokeDasharray={`${(sweep / 360) * C} ${C}`}
                  transform="rotate(-90 260 260)"
                  style={{filter: `drop-shadow(0 0 22px ${a})`}} />
          <text x={260} y={245} textAnchor="middle" fill={V5.ink}
                fontFamily={V5.fontDisplay} fontSize={84}>
            {fromH}-{toH}h</text>
          <text x={260} y={300} textAnchor="middle" fill={V5.inkDim}
                fontFamily={V5.fontBody} fontSize={30}>😴 every night</text>
        </svg>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- CalendarGrid (days/week)
export const CalendarGrid: React.FC<{
  activeDays: number; title: string; accent?: string;
}> = ({activeDays, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', gap: 26}}>
          {names.map((n, i) => {
            const on = i < activeDays;
            const p = pop(frame, Math.round(fps * (0.4 + i * 0.14)), fps);
            return (
              <div key={n} style={{
                width: 150, height: 190, borderRadius: 18,
                background: on ? `linear-gradient(180deg, ${a}, #7a1622)`
                              : '#1a1a22',
                border: `1.5px solid ${on ? a : 'rgba(255,255,255,0.12)'}`,
                boxShadow: on ? `0 0 40px ${V5.accentSoft}` : 'none',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 12,
                transform: `scale(${p}) translateY(${(1 - p) * 30}px)`,
              }}>
                <div style={{fontFamily: V5.fontDisplay, fontSize: 30,
                             color: V5.ink}}>{n}</div>
                <div style={{fontSize: 44}}>{on ? '🏋️' : '💤'}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- PlateCounter (weight)
export const PlateCounter: React.FC<{
  display: string; title: string; sub?: string; accent?: string;
}> = ({display, title, sub, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 30}}>
          {[0, 1, 2].map((i) => (
            <div key={'l' + i} style={{
              width: 34 + i * 10, height: 190 - i * 30, borderRadius: 12,
              background: `linear-gradient(180deg, #2a2a34, #17171d)`,
              border: `2px solid ${a}`,
              opacity: pop(frame, Math.round(fps * (0.3 + i * 0.15)), fps),
            }} />
          ))}
          <div style={{
            fontFamily: V5.fontDisplay, fontSize: 120, color: V5.ink,
            textShadow: `0 0 50px ${V5.accentSoft}`, padding: '0 26px',
            opacity: pop(frame, Math.round(fps * 0.75), fps),
          }}>{display}</div>
          {[2, 1, 0].map((i) => (
            <div key={'r' + i} style={{
              width: 34 + i * 10, height: 190 - i * 30, borderRadius: 12,
              background: `linear-gradient(180deg, #2a2a34, #17171d)`,
              border: `2px solid ${a}`,
              opacity: pop(frame, Math.round(fps * (0.3 + i * 0.15)), fps),
            }} />
          ))}
        </div>
        {sub ? (
          <div style={{position: 'absolute', bottom: 150,
                       fontFamily: V5.fontBody, fontSize: 32,
                       color: V5.inkDim}}>{sub}</div>
        ) : null}
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- GramsBar (macro grams)
export const GramsBar: React.FC<{
  icon: string; display: string; title: string; frac?: number;
  accent?: string;
}> = ({icon, display, title, frac = 0.8, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const w = P(frame, fps, 0.5, 0, frac * 100);
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{width: 1000}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 26,
                       marginBottom: 26}}>
            <div style={{fontSize: 90,
                         opacity: pop(frame, 4, fps)}}>{icon}</div>
            <div style={{fontFamily: V5.fontDisplay, fontSize: 96,
                         color: V5.ink,
                         opacity: pop(frame, 8, fps)}}>{display}</div>
          </div>
          <div style={{height: 34, borderRadius: 17, background: '#22222a',
                       overflow: 'hidden'}}>
            <div style={{height: '100%', width: `${w}%`,
                         background: `linear-gradient(90deg, ${a}, #ff8a5c)`,
                         boxShadow: `0 0 34px ${V5.accentSoft}`}} />
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- TicketStub (cheat meals)
export const TicketStub: React.FC<{
  big: string; small: string; title: string; accent?: string;
}> = ({big, small, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const e = pop(frame, 4, fps);
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{
          display: 'flex', borderRadius: 22, overflow: 'hidden',
          boxShadow: `0 30px 90px rgba(0,0,0,.6), 0 0 70px ${V5.accentSoft}`,
          transform: `rotate(-2deg) scale(${0.9 + e * 0.1})`, opacity: e,
        }}>
          <div style={{background: a, padding: '46px 40px',
                       display: 'flex', alignItems: 'center'}}>
            <div style={{fontSize: 84}}>🍔</div>
          </div>
          <div style={{background: '#f6f2e8', padding: '36px 54px',
                       borderLeft: '4px dashed #999'}}>
            <div style={{fontFamily: V5.fontDisplay, fontSize: 66,
                         color: '#181818'}}>{big}</div>
            <div style={{fontFamily: V5.fontBody, fontSize: 30,
                         color: '#555', marginTop: 8}}>{small}</div>
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- BigCounter (calories)
export const BigCounter: React.FC<{
  from: number; to: number; suffix?: string; title: string; sub?: string;
  accent?: string;
}> = ({from, to, suffix = '', title, sub, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const v = Math.round(P(frame, fps, 0.4, from, to));
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{fontFamily: V5.fontDisplay, fontSize: 200,
                     color: V5.ink, lineHeight: 1,
                     textShadow: `0 0 80px ${V5.accentSoft}`}}>
          {v.toLocaleString('en-US')}{suffix}
        </div>
        {sub ? (
          <div style={{fontFamily: V5.fontBody, fontSize: 36,
                       color: V5.inkDim, marginTop: 20}}>{sub}</div>
        ) : null}
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- YearsTimeline
export const YearsTimeline: React.FC<{
  years: {y: string; label: string}[]; title: string; accent?: string;
}> = ({years, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{width: 1500}}>
          <div style={{height: 6, background: '#2a2a34', borderRadius: 3,
                       position: 'relative', margin: '90px 0'}}>
            <div style={{position: 'absolute', inset: 0, borderRadius: 3,
                         width: `${P(frame, fps, 0.3, 0, 100)}%`,
                         background: `linear-gradient(90deg, ${a}, #ff8a5c)`,
                         boxShadow: `0 0 30px ${V5.accentSoft}`}} />
            {years.map((yy, i) => {
              const x = (i / (years.length - 1)) * 100;
              const p = pop(frame, Math.round(fps * (0.5 + i * 0.3)), fps);
              return (
                <div key={i} style={{position: 'absolute', left: `${x}%`,
                                     top: -14,
                                     transform: 'translateX(-50%)'}}>
                  <div style={{width: 30, height: 30, borderRadius: 15,
                               background: a,
                               border: '4px solid #0d0d12',
                               transform: `scale(${p})`}} />
                  <div style={{textAlign: 'center', marginTop: 16,
                               opacity: p}}>
                    <div style={{fontFamily: V5.fontDisplay, fontSize: 38,
                                 color: V5.ink}}>{yy.y}</div>
                    <div style={{fontFamily: V5.fontBody, fontSize: 24,
                                 color: V5.inkDim, maxWidth: 200}}>
                      {yy.label}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- RangeSplit (X to Y)
export const RangeSplit: React.FC<{
  left: string; right: string; leftSub: string; rightSub: string;
  title: string; accent?: string;
}> = ({left, right, leftSub, rightSub, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const pL = pop(frame, Math.round(fps * 0.35), fps);
  const pR = pop(frame, Math.round(fps * 0.65), fps);
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 50}}>
          <div style={{textAlign: 'center', opacity: pL,
                       transform: `translateX(${(1 - pL) * -60}px)`}}>
            <div style={{fontFamily: V5.fontDisplay, fontSize: 130,
                         color: V5.ink}}>{left}</div>
            <div style={{fontFamily: V5.fontBody, fontSize: 30,
                         color: V5.inkDim}}>{leftSub}</div>
          </div>
          <div style={{width: 8, height: 220, borderRadius: 4,
                       background: a,
                       boxShadow: `0 0 40px ${V5.accentSoft}`,
                       transform: 'rotate(14deg)'}} />
          <div style={{textAlign: 'center', opacity: pR,
                       transform: `translateX(${(1 - pR) * 60}px)`}}>
            <div style={{fontFamily: V5.fontDisplay, fontSize: 130,
                         color: V5.ink}}>{right}</div>
            <div style={{fontFamily: V5.fontBody, fontSize: 30,
                         color: V5.inkDim}}>{rightSub}</div>
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// -------------------------------------------------- StepsRing (10k steps)
export const StepsRing: React.FC<{
  display: string; title: string; accent?: string;
}> = ({display, title, accent}) => {
  const {frame, fps} = useT();
  const a = accent ?? V5.accent;
  const n = 22;
  return (
    <Stage accent={a}>
      <Title t={title} f={pop(frame, 2, fps)} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <svg width={560} height={560}>
          {Array.from({length: n}, (_, i) => {
            const ang = (i / n) * 2 * Math.PI - Math.PI / 2;
            const on = frame > fps * (0.3 + i * 0.07);
            return (
              <text key={i} x={280 + Math.cos(ang) * 216}
                    y={288 + Math.sin(ang) * 216} textAnchor="middle"
                    fontSize={30} opacity={on ? 1 : 0.15}
                    transform={`rotate(${(ang * 180) / Math.PI + 90} ` +
                               `${280 + Math.cos(ang) * 216} ` +
                               `${280 + Math.sin(ang) * 216})`}>👟</text>
            );
          })}
          <text x={280} y={270} textAnchor="middle" fill={V5.ink}
                fontFamily={V5.fontDisplay} fontSize={92}>{display}</text>
          <text x={280} y={330} textAnchor="middle" fill={V5.inkDim}
                fontFamily={V5.fontBody} fontSize={32}>steps / day</text>
        </svg>
      </AbsoluteFill>
    </Stage>
  );
};
