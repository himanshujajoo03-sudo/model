// Pure Client-Side Web Audio API Synthesizer for Weather Operations
// Zero external audio files or network requests required.

let audioCtx = null

function getAudioContext() {
  if (typeof window === 'undefined') return null
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    if (AudioContextClass) {
      audioCtx = new AudioContextClass()
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume()
  }
  return audioCtx
}

export function isAudioMuted() {
  if (typeof window === 'undefined') return false
  return localStorage.getItem('meteo_audio_muted') === 'true'
}

export function setAudioMuted(muted) {
  if (typeof window === 'undefined') return
  localStorage.setItem('meteo_audio_muted', String(muted))
}

export function toggleAudioMute() {
  const current = isAudioMuted()
  setAudioMuted(!current)
  return !current
}

/**
 * High-tech subtle radar chirp / ping for telemetry ingestion
 */
export function playRadarChirp() {
  if (isAudioMuted()) return
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    const now = ctx.currentTime
    osc.frequency.setValueAtTime(880, now)
    osc.frequency.exponentialRampToValueAtTime(1760, now + 0.12)

    gain.gain.setValueAtTime(0.04, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(now)
    osc.stop(now + 0.16)
  } catch (err) {
    console.debug('Audio chirp silenced:', err)
  }
}

/**
 * 2-tone warning alert chime for critical / extreme meteorological hazards
 */
export function playHazardSiren() {
  if (isAudioMuted()) return
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime
    const osc1 = ctx.createOscillator()
    const osc2 = ctx.createOscillator()
    const gain = ctx.createGain()

    osc1.type = 'triangle'
    osc2.type = 'sine'

    osc1.frequency.setValueAtTime(660, now)
    osc1.frequency.setValueAtTime(880, now + 0.12)
    osc2.frequency.setValueAtTime(440, now)
    osc2.frequency.setValueAtTime(587, now + 0.12)

    gain.gain.setValueAtTime(0.06, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35)

    osc1.connect(gain)
    osc2.connect(gain)
    gain.connect(ctx.destination)

    osc1.start(now)
    osc2.start(now)
    osc1.stop(now + 0.36)
    osc2.stop(now + 0.36)
  } catch (err) {
    console.debug('Audio hazard siren silenced:', err)
  }
}

/**
 * Pleasant notification chime for operational dispatches
 */
export function playNotificationChime() {
  if (isAudioMuted()) return
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.setValueAtTime(523.25, now) // C5
    osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.08) // E5
    osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.16) // G5

    gain.gain.setValueAtTime(0.05, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(now)
    osc.stop(now + 0.32)
  } catch (err) {
    console.debug('Notification chime silenced:', err)
  }
}
