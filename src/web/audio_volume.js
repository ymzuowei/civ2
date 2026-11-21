// CIV2-T008: browser-local master audio preference, independent of game files/saves.
// No AudioContext is created until the game's existing user gesture/audio path.
const KEY = 'openciv2.browser-audio.v1';
const clamp = (n) => Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : 100;

export function createAudioVolume(storage) {
    let backend = null;
    try { backend = storage === undefined ? globalThis.localStorage : storage; } catch (_) { /* private browsing */ }
    let saved = {};
    try { saved = JSON.parse(backend?.getItem(KEY) || '{}') || {}; } catch (_) { /* blocked or corrupted preference */ }
    let level = typeof saved.level === 'number' ? clamp(saved.level) : 100;
    let muted = saved.muted === true;
    const listeners = new Set();
    const gain = () => muted ? 0 : level / 100;
    function notify() {
        try { backend?.setItem(KEY, JSON.stringify({level, muted})); } catch (_) { /* optional */ }
        for (const listener of listeners)
            listener(gain());
    }
    return {
        get level() { return level; },
        get muted() { return muted; },
        get gain() { return gain(); },
        setLevel(next) {
            const value = clamp(Number(next));
            if (value !== level) { level = value; notify(); }
        },
        setMuted(next) {
            const value = !!next;
            if (value !== muted) { muted = value; notify(); }
        },
        subscribe(listener) {
            listeners.add(listener);
            return () => listeners.delete(listener);
        },
    };
}

 // Short accessible browser-toolbar labels. Non-Chinese locales fall back to English
 // without altering the game's complete existing native translation catalogs.
export function audioLabels(code) {
    const locale = String(code || '').toLowerCase();
    if (/^zh[-_](hans|cn|sg)/.test(locale))
        return {volume: '音量', mute: '静音', unmute: '取消静音'};
    if (/^zh[-_](hant|tw|hk|mo)/.test(locale))
        return {volume: '音量', mute: '靜音', unmute: '取消靜音'};
    return {volume: 'Volume', mute: 'Mute', unmute: 'Unmute'};
}
