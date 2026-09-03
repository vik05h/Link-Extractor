// audio.ts — Web Audio API Synthesizer for Gaming Haptics

let audioCtx: AudioContext | null = null;
let muted = false;

// Initialize mute state from localStorage
if (typeof window !== 'undefined') {
  muted = localStorage.getItem('sound_muted') === 'true';
}

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

export function isAudioMuted(): boolean {
  return muted;
}

export function setAudioMuted(val: boolean): void {
  muted = val;
  if (typeof window !== 'undefined') {
    localStorage.setItem('sound_muted', String(val));
  }
}

export function toggleAudioMute(): boolean {
  setAudioMuted(!muted);
  return muted;
}

/**
 * High-tech tactile blip when a part captcha/Turnstile is solved.
 */
export function playBypassSound(): void {
  if (muted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  const now = ctx.currentTime;
  osc.type = 'sine';
  osc.frequency.setValueAtTime(880, now);
  osc.frequency.exponentialRampToValueAtTime(1320, now + 0.08);

  gain.gain.setValueAtTime(0.08, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.08);
}

/**
 * Subtle UI click sound for interactions.
 */
export function playClickSound(): void {
  if (muted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  const now = ctx.currentTime;
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(440, now);
  osc.frequency.exponentialRampToValueAtTime(220, now + 0.04);

  gain.gain.setValueAtTime(0.04, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.04);
}

/**
 * Celebratory harmonic chord on 100% extraction and validation.
 */
export function playSuccessChime(): void {
  if (muted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const freqs = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6

  freqs.forEach((f, i) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(f, now + i * 0.06);

    gain.gain.setValueAtTime(0.06, now + i * 0.06);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6 + i * 0.06);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now + i * 0.06);
    osc.stop(now + 0.6 + i * 0.06);
  });
}
