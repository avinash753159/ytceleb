import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {V5} from './tokens_v5';
import {Stage} from './v5cards';
import {anteriorData, posteriorData} from './bodyPaths';

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps,
          config: {damping: 11, stiffness: 170, mass: 0.7}});

// free-exercise-db muscle names -> vendored body-model region keys
const MUSCLE_MAP: Record<string, string[]> = {
  'chest': ['chest'],
  'shoulders': ['front_deltoids', 'back_deltoids'],
  'biceps': ['biceps'],
  'triceps': ['triceps'],
  'forearms': ['forearm'],
  'abdominals': ['abs', 'obliques'],
  'quadriceps': ['quadriceps'],
  'hamstrings': ['hamstring'],
  'glutes': ['gluteal'],
  'calves': ['calves', 'left_soleus', 'right_soleus'],
  'lats': ['upper_back'],
  'middle back': ['upper_back'],
  'lower back': ['lower_back'],
  'traps': ['trapezius'],
  'neck': ['neck'],
  'abductors': ['abductors'],
  'adductors': ['adductor'],
};

const toRegions = (names: string[]) =>
  new Set(names.flatMap((n) => MUSCLE_MAP[n.toLowerCase()] ?? []));

// One body figure (front or back) with pulsing highlighted regions.
const Body: React.FC<{
  data: {muscle: string; svgPoints: string[]}[];
  primary: Set<string>; secondary: Set<string>;
  accent: string; pulse: number;
}> = ({data, primary, secondary, accent, pulse}) => (
  <svg viewBox="0 0 100 200" style={{height: '100%'}}>
    {data.map((m, i) =>
      m.svgPoints.map((pts, j) => {
        const isP = primary.has(m.muscle);
        const isS = secondary.has(m.muscle);
        return (
          <polygon key={`${i}-${j}`} points={pts}
            fill={isP ? accent : isS ? accent : '#3A3A42'}
            opacity={isP ? 0.55 + 0.45 * pulse
                     : isS ? 0.28 + 0.12 * pulse : 0.9}
            stroke="#0C0C0F" strokeWidth="0.3"/>
        );
      })
    )}
  </svg>
);

// ------------------------------------------------ ExerciseCard
// Real two-pose demo photos crossfading start<->finish + muscle map +
// animated set/rep/rest counters. The flagship V10 card.
export const ExerciseCard: React.FC<{
  name: string;
  img0?: string; img1?: string;        // start / finish pose photos
  videoSrc?: string;                   // looping demo video (data URI)
  videoStatic?: string;                // looping demo video (bundle public/)
  primaryMuscles?: string[]; secondaryMuscles?: string[];
  sets?: string; reps?: string; rest?: string;
  setsLabel?: string; repsLabel?: string; restLabel?: string;
  accent?: string;
}> = ({name, img0 = '', img1 = '', videoSrc, videoStatic,
       primaryMuscles = [], secondaryMuscles = [],
       sets, reps, rest,
       setsLabel = 'SETS', repsLabel = 'REPS', restLabel = 'REST',
       accent = V5.accent}) => {
  const vsrc = videoStatic ? staticFile(videoStatic) : videoSrc;
  const {frame, fps} = useT();
  const enter = pop(frame, 3, fps);
  // pose crossfade: eased alternation ~1.1s per pose
  const cyc = (frame / (1.1 * fps)) % 2;
  const xf = interpolate(
    cyc < 1 ? cyc : 2 - cyc, [0.25, 0.75], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pulse = 0.5 + 0.5 * Math.sin(frame / 7);
  const prim = toRegions(primaryMuscles);
  const sec = toRegions(secondaryMuscles);
  const stats = [
    sets ? {v: sets, l: setsLabel} : null,
    reps ? {v: reps, l: repsLabel} : null,
    rest ? {v: rest, l: restLabel} : null,
  ].filter(Boolean) as {v: string; l: string}[];
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center'}}>
        <div style={{
          opacity: enter, transform: `scale(${0.92 + enter * 0.08})`,
          display: 'grid', gridTemplateColumns: '1060px 520px',
          gap: 0, width: 1580, height: 800,
          background: '#101014', borderRadius: 30, overflow: 'hidden',
          border: '2px solid rgba(255,255,255,0.13)',
          boxShadow: `0 30px 90px rgba(0,0,0,0.6),
                      0 0 ${40 + pulse * 22}px ${accent}44`,
        }}>
          {/* demo media: video loop preferred, two-pose crossfade else */}
          <div style={{position: 'relative', overflow: 'hidden',
                       background: '#fff'}}>
            {vsrc ? (
              <OffthreadVideo src={vsrc} muted loop style={{
                position: 'absolute', inset: 0, width: '100%',
                height: '100%', objectFit: 'cover'}}/>
            ) : (
              <>
                <Img src={img0} style={{position: 'absolute', inset: 0,
                  width: '100%', height: '100%', objectFit: 'cover'}}/>
                <Img src={img1} style={{position: 'absolute', inset: 0,
                  width: '100%', height: '100%', objectFit: 'cover',
                  opacity: xf}}/>
              </>
            )}
            <div style={{position: 'absolute', left: 0, right: 0,
              bottom: 0, height: 10, background: accent,
              boxShadow: `0 0 26px ${accent}`}}/>
          </div>
          {/* right rail */}
          <div style={{padding: '34px 36px', display: 'flex',
                       flexDirection: 'column', gap: 16,
                       overflow: 'hidden'}}>
            <div style={{color: '#fff', fontFamily: V5.font,
                         fontWeight: 900, fontSize: 58, lineHeight: 1.05}}>
              {name}
            </div>
            <div style={{display: 'flex', gap: 18, flex: 1,
                         alignItems: 'center',
                         justifyContent: 'center'}}>
              <Body data={anteriorData} primary={prim} secondary={sec}
                    accent={accent} pulse={pulse}/>
              <Body data={posteriorData} primary={prim} secondary={sec}
                    accent={accent} pulse={pulse}/>
            </div>
            <div style={{color: '#9aa6b0', fontFamily: V5.font,
                         fontWeight: 700, fontSize: 34,
                         textTransform: 'capitalize'}}>
              {primaryMuscles.join(' · ')}
            </div>
            {stats.length ? (
              <div style={{display: 'flex', gap: 18}}>
                {stats.map((s, i) => {
                  const p = pop(frame, 14 + i * 7, fps);
                  return (
                    <div key={i} style={{
                      opacity: p, transform: `scale(${p})`,
                      background: '#1b1b21', borderRadius: 16,
                      padding: '10px 18px', textAlign: 'center',
                      border: `2px solid ${accent}55`}}>
                      <div style={{color: '#fff', fontFamily: V5.font,
                                   fontWeight: 900,
                                   fontSize: 40}}>{s.v}</div>
                      <div style={{color: '#8b95a0', fontFamily: V5.font,
                                   fontWeight: 700, fontSize: 20,
                                   letterSpacing: 2}}>{s.l}</div>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};


// ------------------------------------------------ DocumentCard
// The ACTUAL published document on screen: page image slowly panning,
// paper-tilt presentation, source citation bar (outlet / date / author).
export const DocumentCard: React.FC<{
  src: string;                       // page image (data URL)
  outlet: string; date: string; author?: string;
  note?: string;                     // e.g. "the original diary, page 2"
  accent?: string;
  panFrom?: number; panTo?: number;  // 0-1 vertical focus sweep
}> = ({src, outlet, date, author, note, accent = V5.accent,
       panFrom = 0.1, panTo = 0.75}) => {
  const {frame, fps, dur} = useT();
  const enter = pop(frame, 3, fps);
  const pan = interpolate(frame, [12, dur - 8], [panFrom, panTo],
                          {extrapolateLeft: 'clamp',
                           extrapolateRight: 'clamp'});
  return (
    <Stage accent={accent}>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center'}}>
        <div style={{
          opacity: enter,
          transform: `scale(${0.92 + enter * 0.08})
                      rotate(${(1 - enter) * -3 - 0.6}deg)`,
          width: 1150, height: 830, borderRadius: 14,
          overflow: 'hidden', background: '#fff',
          boxShadow: `0 40px 110px rgba(0,0,0,0.75),
                      0 0 60px ${accent}33`,
          position: 'relative',
        }}>
          <Img src={src} style={{
            width: '100%',
            transform: `translateY(${-pan * 55}%)`,
          }}/>
          <div style={{position: 'absolute', inset: 0, boxShadow:
            'inset 0 0 90px rgba(0,0,0,0.28)'}}/>
        </div>
        <div style={{
          opacity: pop(frame, 16, fps),
          marginTop: -34, zIndex: 3, display: 'flex',
          alignItems: 'center', gap: 0, borderRadius: 14,
          overflow: 'hidden',
          boxShadow: '0 14px 44px rgba(0,0,0,0.6)',
        }}>
          <div style={{background: accent, color: '#fff',
                       fontFamily: V5.fontDisplay, fontWeight: 400, letterSpacing: 2, fontSize: 34,
                       letterSpacing: 2, padding: '16px 26px'}}>
            SOURCE
          </div>
          <div style={{background: 'rgba(10,10,13,0.95)', color: '#fff',
                       fontFamily: V5.font, fontWeight: 700, fontSize: 34,
                       padding: '16px 30px'}}>
            {outlet} · {date}{author ? ` · ${author}` : ''}
            {note ? (
              <span style={{color: '#9aa6b0', fontSize: 26}}>
                {'  —  '}{note}</span>
            ) : null}
          </div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};


// ------------------------------------------------ BrandIntro (channel sting)
// Red circle sweep + CELEB WORKOUT in the channel's Anton style.
export const BrandIntro: React.FC<{sub?: string}> = (
    {sub = 'Workouts & Diet Secrets'}) => {
  const {frame, fps, dur} = useT();
  const circle = spring({frame, fps, config: {damping: 16,
                                              stiffness: 90, mass: 0.9}});
  const namep = spring({frame: frame - 10, fps,
                        config: {damping: 13, stiffness: 150, mass: 0.7}});
  const subp = spring({frame: frame - 22, fps,
                       config: {damping: 13, stiffness: 150, mass: 0.7}});
  const out = interpolate(frame, [dur - 10, dur - 1], [1, 0],
                          {extrapolateLeft: 'clamp',
                           extrapolateRight: 'clamp'});
  return (
    <Stage accent="#E3120B">
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center', opacity: out}}>
        <div style={{position: 'absolute', width: 1500 * circle,
                     height: 1500 * circle, borderRadius: '50%',
                     background: 'radial-gradient(circle,' +
                       ' rgba(227,18,11,0.32), rgba(227,18,11,0.05) 70%)',
                     border: '3px solid rgba(227,18,11,0.5)'}}/>
        <div style={{
          opacity: namep, transform: `scale(${0.8 + namep * 0.2})`,
          fontFamily: V5.fontDisplay, fontSize: 170, letterSpacing: 6,
          color: '#fff', textTransform: 'uppercase', lineHeight: 0.95,
          textAlign: 'center',
          textShadow: '0 10px 60px rgba(0,0,0,0.8)'}}>
          CELEB<span style={{color: '#E3120B'}}> WORKOUT</span>
        </div>
        <div style={{
          opacity: subp, transform: `translateY(${(1 - subp) * 30}px)`,
          marginTop: 26, fontFamily: V5.fontDisplay, fontSize: 44,
          letterSpacing: 10, color: '#EDEAE2',
          textTransform: 'uppercase'}}>{sub}</div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ LogoBug (corner watermark)
export const LogoBug: React.FC = () => (
  <AbsoluteFill>
    <div style={{position: 'absolute', right: 44, top: 38, opacity: 0.85,
                 fontFamily: V5.fontDisplay, fontSize: 30, letterSpacing: 2,
                 color: '#fff', textTransform: 'uppercase',
                 textShadow: '0 2px 14px rgba(0,0,0,0.9)'}}>
      CELEB<span style={{color: '#E3120B'}}> WORKOUT</span>
    </div>
  </AbsoluteFill>
);
