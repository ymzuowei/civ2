// One-time, browser-only map art preference. Not CIV.INI or save data.
// Explicit ?hd=N remains the reproducible comparison override.
export const GRAPHICS_PREFERENCE_KEY = 'graphics-art-choice-v1';
export function graphicsFromQuery(search = '') {
    const q = new URLSearchParams(search);
    if (!q.has('hd'))
        return null;
    const value = q.get('hd');
    return value === '' || /^(on|[1-4])$/i.test(value) ? 'hd' : 'classic';
}
export async function resolveGraphicsPreference(store, search, available, ask) {
    const explicit = graphicsFromQuery(search);
    if (explicit)
        return explicit;
    const saved = await store.getMeta(GRAPHICS_PREFERENCE_KEY);
    if (saved === 'classic' || saved === 'hd')
        return saved;
    const selected = await ask(available);
    const mode = selected === 'hd' && available ? 'hd' : 'classic';
    await store.setMeta(GRAPHICS_PREFERENCE_KEY, mode);
    return mode;
}
export const hdArg = (choice) => choice === 'hd' ? '1' : '0';
