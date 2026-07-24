// Shared design tokens - ONE look across every graphic.
// Two fonts max, one accent per celebrity, consistent radius + easing.
// Per-celebrity accent comes in via input props (accent), falling back here.

export const TOKENS = {
  fontDisplay: '"Arial Black", "Segoe UI Black", sans-serif',
  fontBody: '"Segoe UI", Arial, sans-serif',
  accent: '#E63946',            // default; overridden per celebrity via props
  ink: '#FFFFFF',
  inkDim: 'rgba(255,255,255,0.72)',
  panel: 'rgba(10,10,14,0.78)',
  panelEdge: 'rgba(255,255,255,0.14)',
  radius: 14,
  pad: 28,
  // spring-ish cubic for entrances; never bounce more than once
  easing: [0.16, 1, 0.3, 1] as [number, number, number, number],
};

export const msToFrame = (ms: number, fps: number) =>
  Math.round((ms / 1000) * fps);
