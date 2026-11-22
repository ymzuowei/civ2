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
    // T017: keep the v1 master preference; new per-channel levels default
    // to 100%, preserving playback behavior for existing users.
    let musicLevel = typeof saved.musicLevel === 'number' ? clamp(saved.musicLevel) : 100;
    let effectsLevel = typeof saved.effectsLevel === 'number' ? clamp(saved.effectsLevel) : 100;
    const listeners = new Set();
    const gain = () => muted ? 0 : level / 100;
    function notify() {
        try { backend?.setItem(KEY, JSON.stringify({level, muted, musicLevel, effectsLevel})); } catch (_) { /* optional */ }
        for (const listener of listeners)
            listener(gain());
    }
    return {
        get level() { return level; },
        get muted() { return muted; },
        get gain() { return gain(); },
        get musicLevel() { return musicLevel; },
        get effectsLevel() { return effectsLevel; },
        get musicGain() { return musicLevel / 100; },
        get effectsGain() { return effectsLevel / 100; },
        setLevel(next) {
            const value = clamp(Number(next));
            if (value !== level) { level = value; notify(); }
        },
        setMusicLevel(next) {
            const value = clamp(Number(next));
            if (value !== musicLevel) { musicLevel = value; notify(); }
        },
        setEffectsLevel(next) {
            const value = clamp(Number(next));
            if (value !== effectsLevel) { effectsLevel = value; notify(); }
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
        return {volume: '总音量', music: '音乐', effects: '音效', mixer: '音量设置', mute: '静音', unmute: '取消静音'};
    if (/^zh[-_](hant|tw|hk|mo)/.test(locale))
        return {volume: '總音量', music: '音樂', effects: '音效', mixer: '音量設定', mute: '靜音', unmute: '取消靜音'};
    return {volume: 'Master', music: 'Music', effects: 'Effects', mixer: 'Audio levels', mute: 'Mute', unmute: 'Unmute'};
}
