import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TOKENS, msToFrame} from './tokens';

// Every component is an OVERLAY: transparent background, content only.
// Word-timed reveals: items carry atMs (offset from the start of this comp).

const useT = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return {frame, fps, tMs: (frame / fps) * 1000};
};

const enter = (frame: number, f0: number, fps: number) =>
  spring({frame: frame - f0, fps, config: {damping: 200, stiffness: 120}});

// ---------------------------------------------------------- <ListReveal>
// N items, staggered entrance keyed to word timestamps.
export const ListReveal: React.FC<{
  title?: string;
  items: {text: string; atMs: number}[];
  accent?: string;
  side?: 'left' | 'right';
}> = ({title, items, accent = TOKENS.accent, side = 'left'}) => {
  const {frame, fps, tMs} = useT();
  return (
    <AbsoluteFill
      style={{justifyContent: 'center',
              alignItems: side === 'left' ? 'flex-start' : 'flex-end'}}>
      <div style={{[side === 'left' ? 'marginLeft' : 'marginRight']: 80,
                   maxWidth: 760} as React.CSSProperties}>
        {title ? (
          <div
            style={{
              fontFamily: TOKENS.fontDisplay, fontSize: 38, color: TOKENS.ink,
              background: TOKENS.panel, border: `1px solid ${TOKENS.panelEdge}`,
              borderLeft: `10px solid ${accent}`, borderRadius: TOKENS.radius,
              padding: `${TOKENS.pad / 2}px ${TOKENS.pad}px`, marginBottom: 18,
              opacity: enter(frame, 0, fps),
              textTransform: 'uppercase', letterSpacing: 1,
            }}
          >
            {title}
          </div>
        ) : null}
        {items.map((it, i) => {
          const f0 = msToFrame(it.atMs, fps);
          const p = tMs >= it.atMs ? enter(frame, f0, fps) : 0;
          return (
            <div
              key={i}
              style={{
                display: 'flex', alignItems: 'center', gap: 18,
                marginBottom: 14, opacity: p,
                transform: `translateX(${(1 - p) * -40}px)`,
              }}
            >
              <div
                style={{
                  width: 46, height: 46, borderRadius: 23, background: accent,
                  color: TOKENS.ink, fontFamily: TOKENS.fontDisplay,
                  fontSize: 26, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div
                style={{
                  fontFamily: TOKENS.fontBody, fontSize: 30, fontWeight: 600,
                  color: TOKENS.ink, background: TOKENS.panel,
                  border: `1px solid ${TOKENS.panelEdge}`,
                  borderRadius: TOKENS.radius,
                  padding: `${TOKENS.pad / 2}px ${TOKENS.pad}px`,
                }}
              >
                {it.text}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------- <StatCard>
// Large number with counter animation + label.
export const StatCard: React.FC<{
  value: string;           // "20", "3,200", "8%"
  label: string;
  accent?: string;
  side?: 'left' | 'right' | 'center';
}> = ({value, label, accent = TOKENS.accent, side = 'center'}) => {
  const {frame, fps} = useT();
  const p = enter(frame, 0, fps);
  const numMatch = value.match(/^([\d.,]+)(.*)$/);
  let display = value;
  if (numMatch) {
    const target = parseFloat(numMatch[1].replace(/,/g, ''));
    const cur = Math.round(
      interpolate(Math.min(p, 1), [0, 1], [0, target])
    ).toLocaleString('en-US');
    display = cur + numMatch[2];
  }
  const align = side === 'center' ? 'center'
    : side === 'left' ? 'flex-start' : 'flex-end';
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: align}}>
      <div
        style={{
          background: TOKENS.panel, border: `1px solid ${TOKENS.panelEdge}`,
          borderTop: `8px solid ${accent}`, borderRadius: TOKENS.radius,
          padding: `${TOKENS.pad * 0.75}px ${TOKENS.pad * 1.4}px`,
          textAlign: 'center', opacity: p,
          transform: `scale(${0.9 + p * 0.1})`,
          margin: side === 'center' ? 0 : '0 80px',
        }}
      >
        <div
          style={{
            fontFamily: TOKENS.fontDisplay, fontSize: 110, lineHeight: 1.05,
            color: TOKENS.ink,
          }}
        >
          {display}
        </div>
        <div
          style={{
            fontFamily: TOKENS.fontBody, fontSize: 30, color: TOKENS.inkDim,
            textTransform: 'uppercase', letterSpacing: 3, marginTop: 6,
          }}
        >
          {label}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------- <PersonCard>
// Image, name, role, slow push-in on the image.
export const PersonCard: React.FC<{
  imageSrc: string;        // staticFile()-style path or data URL
  name: string;
  role: string;
  accent?: string;
  side?: 'left' | 'right' | 'center';
}> = ({imageSrc, name, role, accent = TOKENS.accent, side = 'center'}) => {
  const {frame, fps} = useT();
  const {durationInFrames} = useVideoConfig();
  const p = enter(frame, 0, fps);
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.12]);
  const align = side === 'center' ? 'center'
    : side === 'left' ? 'flex-start' : 'flex-end';
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: align}}>
      <div
        style={{
          width: 560, margin: side === 'center' ? 0 : '0 80px',
          borderRadius: TOKENS.radius, overflow: 'hidden',
          background: TOKENS.panel, border: `1px solid ${TOKENS.panelEdge}`,
          opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
        }}
      >
        <div style={{height: 400, overflow: 'hidden'}}>
          {imageSrc ? (
            <Img
              src={imageSrc}
              style={{
                width: '100%', height: '100%', objectFit: 'cover',
                transform: `scale(${zoom})`,
              }}
            />
          ) : (
            // monogram fallback: no licensed headshot available - never
            // show a wrong person under a real name
            <div
              style={{
                width: '100%', height: '100%', display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                background:
                  `radial-gradient(circle at 30% 25%, #2a2a34, #101014)`,
              }}
            >
              <div
                style={{
                  width: 260, height: 260, borderRadius: 130,
                  background: accent, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  fontFamily: TOKENS.fontDisplay, fontSize: 110,
                  color: TOKENS.ink, transform: `scale(${zoom})`,
                }}
              >
                {name.split(/\s+/).map((w) => w[0]).slice(0, 2).join('')}
              </div>
            </div>
          )}
        </div>
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 16,
            padding: `${TOKENS.pad / 2}px ${TOKENS.pad}px`,
            borderTop: `6px solid ${accent}`,
          }}
        >
          <div>
            <div style={{fontFamily: TOKENS.fontDisplay, fontSize: 42,
                         color: TOKENS.ink}}>{name}</div>
            <div style={{fontFamily: TOKENS.fontBody, fontSize: 28,
                         color: TOKENS.inkDim, textTransform: 'uppercase',
                         letterSpacing: 2}}>{role}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------- <LowerThird>
export const LowerThird: React.FC<{
  title: string;
  sub?: string;
  accent?: string;
}> = ({title, sub, accent = TOKENS.accent}) => {
  const {frame, fps} = useT();
  const p = enter(frame, 0, fps);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'flex-start'}}>
      <div
        style={{
          margin: `0 0 110px 96px`, background: TOKENS.panel,
          border: `1px solid ${TOKENS.panelEdge}`,
          borderLeft: `10px solid ${accent}`, borderRadius: TOKENS.radius,
          padding: `${TOKENS.pad / 2}px ${TOKENS.pad}px`,
          opacity: p, transform: `translateY(${(1 - p) * 24}px)`,
        }}
      >
        <div style={{fontFamily: TOKENS.fontDisplay, fontSize: 40,
                     color: TOKENS.ink}}>{title}</div>
        {sub ? (
          <div style={{fontFamily: TOKENS.fontBody, fontSize: 26,
                       color: TOKENS.inkDim, letterSpacing: 1}}>{sub}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------- <SplitCompare>
// Two-up with a wipe reveal of the right panel.
export const SplitCompare: React.FC<{
  leftSrc: string; rightSrc: string;
  leftLabel: string; rightLabel: string;
  accent?: string;
}> = ({leftSrc, rightSrc, leftLabel, rightLabel, accent = TOKENS.accent}) => {
  const {frame, fps} = useT();
  const wipe = interpolate(frame, [Math.round(fps * 0.4), Math.round(fps * 1.2)],
                           [0, 50], {extrapolateLeft: 'clamp',
                                     extrapolateRight: 'clamp'});
  const Panel: React.FC<{src: string; label: string; right?: boolean;
                         clip?: string}> =
    ({src, label, right, clip}) => (
      <div style={{position: 'absolute', inset: 0, clipPath: clip}}>
        <Img src={src} style={{width: '100%', height: '100%',
                               objectFit: 'cover'}} />
        <div
          style={{
            position: 'absolute', bottom: 60,
            [right ? 'right' : 'left']: 60,
            fontFamily: TOKENS.fontDisplay, fontSize: 38, color: TOKENS.ink,
            background: TOKENS.panel, borderRadius: TOKENS.radius,
            border: `1px solid ${TOKENS.panelEdge}`,
            borderBottom: `8px solid ${accent}`,
            padding: `${TOKENS.pad / 3}px ${TOKENS.pad}px`,
          } as React.CSSProperties}
        >
          {label}
        </div>
      </div>
    );
  return (
    <AbsoluteFill>
      <Panel src={leftSrc} label={leftLabel}
             clip={`inset(0 ${100 - 50}% 0 0)`} />
      <Panel src={rightSrc} label={rightLabel} right
             clip={`inset(0 0 0 ${100 - wipe}%)`} />
      <div style={{position: 'absolute', top: 0, bottom: 0,
                   left: `${50 - 0.3}%`, width: 6, background: accent}} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------- <KenBurns>
// Full-frame still with slow zoom/pan - used for still_pushin beats.
export const KenBurns: React.FC<{
  src: string;
  zoomFrom?: number; zoomTo?: number;
  panFrom?: [number, number]; panTo?: [number, number];  // 0-1 normalized
}> = ({src, zoomFrom = 1.0, zoomTo = 1.12,
       panFrom = [0.5, 0.5], panTo = [0.5, 0.5]}) => {
  const {frame} = useT();
  const {durationInFrames} = useVideoConfig();
  const t = frame / Math.max(durationInFrames - 1, 1);
  const z = zoomFrom + (zoomTo - zoomFrom) * t;
  const cx = panFrom[0] + (panTo[0] - panFrom[0]) * t;
  const cy = panFrom[1] + (panTo[1] - panFrom[1]) * t;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <Img
        src={src}
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          transform: `scale(${z}) translate(${(0.5 - cx) * 100}%, ` +
                     `${(0.5 - cy) * 100}%)`,
        }}
      />
    </AbsoluteFill>
  );
};
