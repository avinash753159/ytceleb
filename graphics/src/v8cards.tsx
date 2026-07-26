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

const useT = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return {frame, fps, dur: durationInFrames};
};
const pop = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps, config: {damping: 14, stiffness: 160,
                                           mass: 0.6}});

// ------------------------------------------------ SubscribeCard (full-screen)
// YouTube-style subscribe row: animated cursor slides in, clicks SUBSCRIBE
// (button flips red->grey "SUBSCRIBED"), bell pops and rings, LIKE thumb
// pops with a burst. House style: dark stage + red glow.
export const SubscribeCard: React.FC<{
  channel?: string; sub?: string; safeZone?: boolean;
}> = ({channel = 'Celeb Workout', sub = 'New breakdowns every week',
       safeZone = false}) => {
  const {frame, fps} = useT();
  const enter = pop(frame, 4, fps);
  const clickF = Math.round(1.55 * fps);          // cursor clicks here
  const clicked = frame >= clickF;
  const cursorX = interpolate(frame, [0.4 * fps, clickF],
                              [560, 0], {extrapolateRight: 'clamp',
                                         extrapolateLeft: 'clamp'});
  const cursorY = interpolate(frame, [0.4 * fps, clickF],
                              [420, 0], {extrapolateRight: 'clamp',
                                         extrapolateLeft: 'clamp'});
  const press = clicked
    ? 1 - 0.25 * Math.exp(-(frame - clickF) / 3)
    : 1;
  const bell = pop(frame, clickF + 6, fps);
  const ring = clicked
    ? Math.sin((frame - clickF) / 2.2) *
      Math.max(0, 1 - (frame - clickF) / (1.2 * fps)) * 18
    : 0;
  const like = pop(frame, clickF + 14, fps);
  const burst = interpolate(frame - clickF - 14, [0, 18], [0, 1],
                            {extrapolateLeft: 'clamp',
                             extrapolateRight: 'clamp'});
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: safeZone ? 'flex-start' : 'center',
                            paddingLeft: safeZone ? 140 : 0,
                            paddingTop: safeZone ? 120 : 0}}>
        {/* safeZone leaves the top-right clear for YouTube end-screen
            elements added in Studio */}
        <div style={{opacity: enter,
                     transform: `scale(${0.9 + enter * 0.1})`,
                     display: 'flex', flexDirection: 'column',
                     alignItems: safeZone ? 'flex-start' : 'center',
                     gap: 54}}>
          <div style={{color: '#fff', fontFamily: V5.font,
                       fontWeight: 800, fontSize: 76,
                       letterSpacing: 1}}>{channel}</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 48}}>
            {/* subscribe button */}
            <div style={{position: 'relative'}}>
              <div style={{
                background: clicked ? '#2a2a2e' : V5.accent,
                color: '#fff', fontFamily: V5.font, fontWeight: 800,
                fontSize: 44, letterSpacing: 2, padding: '26px 64px',
                borderRadius: 14,
                transform: `scale(${press})`,
                boxShadow: clicked ? 'none'
                  : `0 0 60px ${V5.accentSoft}`,
              }}>
                {clicked ? 'SUBSCRIBED' : 'SUBSCRIBE'}
              </div>
              {/* cursor */}
              {frame < clickF + 10 ? (
                <svg width={54} height={54} viewBox="0 0 24 24" style={{
                  position: 'absolute', right: -20 - cursorX,
                  bottom: -18 - cursorY, filter:
                    'drop-shadow(0 4px 10px rgba(0,0,0,0.6))'}}>
                  <path d="M4 2 L20 12 L12.5 13.5 L16 21 L13 22.4 L9.6 15
                           L4 20 Z" fill="#fff" stroke="#111"
                        strokeWidth="1.2"/>
                </svg>
              ) : null}
            </div>
            {/* bell */}
            <div style={{transform:
                `scale(${bell}) rotate(${ring}deg)`,
                transformOrigin: '50% 12%', fontSize: 84}}>🔔</div>
            {/* like */}
            <div style={{position: 'relative',
                         transform: `scale(${like})`, fontSize: 84}}>
              👍
              {burst > 0 && burst < 1 ? (
                [...Array(8)].map((_, i) => {
                  const a = (i / 8) * Math.PI * 2;
                  return <div key={i} style={{
                    position: 'absolute', left: '50%', top: '50%',
                    width: 10, height: 10, borderRadius: 5,
                    background: V5.accent, opacity: 1 - burst,
                    transform: `translate(${Math.cos(a) * burst * 120}px,
                                ${Math.sin(a) * burst * 120}px)`}}/>;
                })
              ) : null}
            </div>
          </div>
          <div style={{color: 'rgba(255,255,255,0.55)',
                       fontFamily: V5.font, fontWeight: 600,
                       fontSize: 34}}>{sub}</div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ CommentPrompt (full-screen)
// Two comment bubbles pop in (option A vs option B) + "drop it in the
// comments" bar with a bouncing 👇.
export const CommentPrompt: React.FC<{
  a: string; b: string; prompt?: string;
}> = ({a, b, prompt = 'Drop it in the comments'}) => {
  const {frame, fps} = useT();
  const pa = pop(frame, 6, fps);
  const pb = pop(frame, 16, fps);
  const pc = pop(frame, 30, fps);
  const bounce = Math.abs(Math.sin(frame / 9)) * 14;
  const bubble = (txt: string, p: number, flip: boolean): React.ReactNode => (
    <div style={{
      opacity: p, transform: `scale(${p})
        rotate(${flip ? 2.5 : -2.5}deg)`,
      background: flip ? '#1d1d22' : V5.accent,
      border: `2px solid ${flip ? 'rgba(255,255,255,0.14)' : V5.accent}`,
      color: '#fff', fontFamily: V5.font, fontWeight: 800, fontSize: 46,
      padding: '30px 52px', borderRadius: 26,
      [flip ? 'borderBottomRightRadius' : 'borderBottomLeftRadius']: 6,
      boxShadow: flip ? 'none' : `0 0 70px ${V5.accentSoft}`,
      maxWidth: 640,
    } as React.CSSProperties}>{txt}</div>
  );
  return (
    <Stage>
      <AbsoluteFill style={{justifyContent: 'center',
                            alignItems: 'center', gap: 60}}>
        <div style={{display: 'flex', gap: 90, alignItems: 'flex-end'}}>
          {bubble(a, pa, false)}
          {bubble(b, pb, true)}
        </div>
        <div style={{opacity: pc, display: 'flex', alignItems: 'center',
                     gap: 26}}>
          <div style={{color: '#fff', fontFamily: V5.font,
                       fontWeight: 800, fontSize: 52}}>{prompt}</div>
          <div style={{fontSize: 66,
                       transform: `translateY(${bounce}px)`}}>👇</div>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};

// ------------------------------------------------ LikeSubBug (alpha overlay)
// Small bottom-left pill that pops in mid-video: thumbs-up + SUBSCRIBE,
// wiggles once, pops out. Rendered with alpha for compositing onto footage.
export const LikeSubBug: React.FC<{label?: string}> = (
    {label = 'SUBSCRIBE'}) => {
  const {frame, fps, dur} = useT();
  const inP = pop(frame, 3, fps);
  const out = interpolate(frame, [dur - 12, dur - 2], [1, 0],
                          {extrapolateLeft: 'clamp',
                           extrapolateRight: 'clamp'});
  const wig = Math.sin(frame / 3.5) *
    Math.max(0, 1 - frame / (1.4 * fps)) * 4;
  return (
    <AbsoluteFill>
      <div style={{
        position: 'absolute', left: 70, bottom: 78,
        opacity: Math.min(inP, out),
        transform: `scale(${0.8 + 0.2 * Math.min(inP, out)})
                    rotate(${wig}deg)`,
        display: 'flex', alignItems: 'center', gap: 20,
        background: 'rgba(12,12,14,0.88)',
        border: '2px solid rgba(255,255,255,0.16)',
        borderRadius: 60, padding: '18px 34px',
        boxShadow: `0 0 46px ${V5.accentSoft}`,
      }}>
        <div style={{fontSize: 46}}>👍</div>
        <div style={{background: V5.accent, color: '#fff',
                     fontFamily: V5.font, fontWeight: 800, fontSize: 30,
                     letterSpacing: 2, padding: '12px 26px',
                     borderRadius: 40}}>{label}</div>
        <div style={{fontSize: 40}}>🔔</div>
      </div>
    </AbsoluteFill>
  );
};
