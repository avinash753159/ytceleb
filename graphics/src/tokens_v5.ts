// V5 design tokens - reference-video language: dark bg, single accent glow,
// radiating circles, pop-in springs, yellow marker highlights.
export const V5 = {
  bg0: '#0a0a0e',
  bg1: '#141018',
  accent: '#E63946',            // Deadpool red (per-celebrity)
  accentSoft: 'rgba(230,57,70,0.22)',
  ink: '#FFFFFF',
  inkDim: 'rgba(255,255,255,0.68)',
  marker: 'rgba(255,220,50,0.85)',   // yellow highlighter
  ring: 'rgba(230,57,70,0.16)',
  fontDisplay: '"Arial Black", "Segoe UI Black", sans-serif',
  fontBody: '"Segoe UI", Arial, sans-serif',
  radius: 16,
};

export const msF = (ms: number, fps: number) => Math.round((ms / 1000) * fps);
