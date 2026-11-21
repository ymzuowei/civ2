// CIV2-T012: browser-local toolbar presentation only. No game state,
// sound preferences, IndexedDB or native Civilization II input is changed.
export const TOOLBAR_KEY = 'openciv2.browser-toolbar.v1';

export function createToolbarCollapse(storage) {
    let backend = null;
    try { backend = storage === undefined ? globalThis.localStorage : storage; }
    catch (_) { /* private/incognito context or storage denied */ }
    let collapsed = false; // Discoverable the first time; respect later choice.
    try { collapsed = backend?.getItem(TOOLBAR_KEY) === 'collapsed'; }
    catch (_) { /* blocked storage: keep controls available */ }
    return {
        get collapsed() { return collapsed; },
        setCollapsed(next) {
            collapsed = !!next;
            try { backend?.setItem(TOOLBAR_KEY, collapsed ? 'collapsed' : 'expanded'); }
            catch (_) { /* never prevent gameplay on storage errors */ }
        },
    };
}

// Accessible names & on-hover mode explanations, with fallback for other
// native locales. We intentionally do not touch legacy codepage catalogs.
export function toolbarLabels(language) {
    const code = String(language || '').toLowerCase();
    if (/^zh[-_](hans|cn|sg)/.test(code))
        return {
            group: '游戏工具栏', collapse: '收起工具栏', expand: '展开工具栏',
            integer: '整数倍缩放：尽量保持像素清晰。如果游戏画面已经与窗口匹配，两种模式可能看起来相同。',
            fit: '适应窗口：允许非整数倍缩放以利用可用空间。恰好为整数倍时，效果可能与整数倍缩放相同。',
        };
    if (/^zh[-_](hant|tw|hk|mo)/.test(code))
        return {
            group: '遊戲工具列', collapse: '收合工具列', expand: '展開工具列',
            integer: '整數倍縮放：盡量保持像素清晰。若遊戲畫面已符合視窗，兩種模式可能看起來相同。',
            fit: '符合視窗：允許非整數倍縮放以利用可用空間。恰好為整數倍時，效果可能與整數倍縮放相同。',
        };
    return {
        group: 'Game controls', collapse: 'Collapse controls', expand: 'Expand controls',
        integer: 'Pixel perfect: prefer whole-number pixel scaling. Both modes may look identical when the game already fits the window.',
        fit: 'Fit viewport: allow fractional scaling to use more of the window. Both modes look the same at an exact integer scale.',
    };
}
