// The browser host's logic under node (no browser): keys, the wheel, the
// desktop's scale, pixels, the WASI file system, .zip reading and writing, the player's saves.
//   tools/toolchain/node/bin/node src/web/test/unit.mjs
import assert from 'node:assert/strict';
import {vkOf, Wheel, desktopScale, desktopUiScale, initialDesktopGeometry, argbToRgba, liveDesktopResize, canvasFitSize, displayModeFromSearch} from '../host.js';
import {MemFS, makeWasi, normalize} from '../wasi.js';
import {createAudioVolume, audioLabels} from '../audio_volume.js';
import {TOOLBAR_KEY, createToolbarCollapse, toolbarLabels} from '../toolbar.js';
import {unzip, zip as makeZip, crc32} from '../zip.js';
import {savesKind, playerFiles, importPath, savesToImport, exportSaves, importSaves} from '../saves.js';
import {deflateRawSync, inflateRawSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {sha256, sha256js, packFrom, keepPack, loadPack, packIndex, prunePack, drawn} from '../hdpack.js';
import {iniGet, iniSet, hdWanted, skipBrowserOpening, openingVideoPresent, openingVideoNeedsGesture, resumeOpeningAudioContext, siteBundlesGame} from '../options.js';
import {match} from '../locale.js';
import {makeNet} from '../net.js';
import {GRAPHICS_PREFERENCE_KEY, graphicsFromQuery, resolveGraphicsPreference, hdArg} from '../graphics_choice.js';

// Native and web language aliases distinguish Taiwan's traditional from
// Mainland/Singapore's simplified Chinese without changing existing saves.
const languageChoices = [{code:'zh-Hant',name:'繁體中文'},{code:'zh-Hans',name:'简体中文'},{code:'de',name:'Deutsch'}];
assert.equal(match('zh-CN',languageChoices),'zh-Hans');
assert.equal(match('zh_SG',languageChoices),'zh-Hans');
assert.equal(match('zh-Hans',languageChoices),'zh-Hans');
assert.equal(match('zh-TW',languageChoices),'zh-Hant');
assert.equal(match('zh-HK',languageChoices),'zh-Hant');
assert.equal(match('zh-MO',languageChoices),'zh-Hant');
assert.equal(match('de-AT',languageChoices),'de');
assert.equal(match('zh-CN',[]),'en');

// BYO-only sites must not request a missing /game/index.json. A GAME=1
// build sets exactly one HTML metadata flag and retains game installation.
const siteFlag = (content) => ({
    querySelector(selector) {
        assert.equal(selector, 'meta[name="openciv2-bundled-game"]');
        return content === null ? null : {content};
    }
});
assert.equal(siteBundlesGame(siteFlag('0')), false);
assert.equal(siteBundlesGame(siteFlag('1')), true);
assert.equal(siteBundlesGame(siteFlag(null)), false);
const byoh = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
assert.match(byoh, /<meta name="openciv2-bundled-game" content="0">/);
assert.match(byoh, /<link rel="icon" href="data:,">/);
const mainSource = readFileSync(new URL('../main.js', import.meta.url), 'utf8');
assert.match(mainSource, /siteBundlesGame\(document\)/);
assert.match(mainSource, /fetch\('game\/index\.json'/);

// Relay discovery should be completely idle during solo game startup.
// Only a real multiplayer connect/listen can probe /info.
const openedSockets = [];
class StubWebSocket {
    constructor(url) {
        openedSockets.push(url);
        this.binaryType = '';
    }
    addEventListener() {}
}
const relayTest = makeNet('ws://relay.test:8765', StubWebSocket);
assert.deepEqual(openedSockets, []);
assert.equal(relayTest.localAddr(), '127.0.0.1');
assert.equal(relayTest.udpOpen() >= 0, true);
assert.deepEqual(openedSockets, []);
const listenerHandle = relayTest.tcpOpen(4993);
assert.equal(openedSockets.length, 0);
assert.equal(relayTest.tcpListen(listenerHandle), 0);
assert.deepEqual(openedSockets, [
    'ws://relay.test:8765/info',
    'ws://relay.test:8765/listen?port=4993'
]);

// keys
assert.equal(vkOf({code: 'KeyA', key: 'a'}), 0x41);
assert.equal(vkOf({code: 'KeyQ', key: 'a'}), 0x41);          // AZERTY: the letter typed
assert.equal(vkOf({code: 'Digit7', key: '&'}), 0x37);
assert.equal(vkOf({code: 'F12', key: 'F12'}), 0x7B);
assert.equal(vkOf({code: 'Numpad8', key: '8'}), 0x68);       // Num Lock on
assert.equal(vkOf({code: 'Numpad8', key: 'ArrowUp'}), 0x26); // off
assert.equal(vkOf({code: 'Numpad5', key: 'Clear'}), 0x0C);
assert.equal(vkOf({code: 'Minus', key: '_'}), 0xBD);
assert.equal(vkOf({code: 'ShiftLeft', key: 'Shift'}), 0xA0);
assert.equal(vkOf({code: 'IntlRo', key: 'ro'}), 0);

// the wheel: notches away from the user positive, fractions added up, reset on turning back
const w = new Wheel();
assert.equal(w.notches(-100, 0), 1);
assert.equal(w.notches(-40, 0), 0);
assert.equal(w.notches(-60, 0), 1);
assert.equal(w.notches(-50, 0), 0);
assert.equal(w.notches(30, 0), 0);          // turned back: the half notch forgotten
assert.equal(w.notches(70, 0), -1);
assert.equal(w.notches(3, 1), -1);          // lines: 3 a notch

// The original startup movie is no longer removed silently. When locally
// present, it is unlocked by a click outside the AVI window; an explicit
// URL escape hatch still exists for recovery from unsupported codecs.
assert.equal(skipBrowserOpening(''), false);
assert.equal(skipBrowserOpening('?lang=zh-CN&display=fit'), false);
assert.equal(skipBrowserOpening('?intro=skip'), true);
assert.equal(skipBrowserOpening('?intro=play'), false);
assert.equal(skipBrowserOpening('?lang=zh-TW&intro=play&display=fit'), false);
assert.equal(skipBrowserOpening('?intro=diagnose'), false);
assert.equal(openingVideoPresent([]), false);
assert.equal(openingVideoPresent([['Video/OPENING.AVI']]), true);
assert.equal(openingVideoPresent([['civ2\\VIDEO\\opening.avi']]), true);
assert.equal(openingVideoPresent([['video/OTHER.AVI']]), false);
assert.equal(openingVideoPresent([['OPENING.AVI']]), false);
const ownedOpening = [['Civ2Art.dll'], ['Video/OPENING.AVI']];
assert.equal(openingVideoNeedsGesture(ownedOpening, false, ''), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, false, '?intro=diagnose'), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, false, '?intro=play'), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, false, '?intro=skip'), false);
// HD must not silently suppress a licensed original movie. This used to
// return false and start directly at the menu despite the stored AVI.
assert.equal(openingVideoNeedsGesture(ownedOpening, true, ''), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, true, '?intro=play'), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, true, '?intro=diagnose'), true);
assert.equal(openingVideoNeedsGesture(ownedOpening, true, '?intro=skip'), false);
assert.equal(openingVideoNeedsGesture([], true, ''), false);
assert.equal(openingVideoNeedsGesture([], false, ''), false);
const runningAudio = {state: 'running', resume() { throw new Error('already running'); }};
assert.equal(await resumeOpeningAudioContext(runningAudio), true);
const unlockedAudio = {state: 'suspended', resume() { this.state = 'running'; return Promise.resolve(); }};
assert.equal(await resumeOpeningAudioContext(unlockedAudio), true);
const deniedAudio = {state: 'suspended', resume() { return Promise.reject(new Error('denied')); }};
assert.equal(await resumeOpeningAudioContext(deniedAudio), false);
const stalledAudio = {state: 'suspended', resume() { return new Promise(() => {}); }};
assert.equal(await resumeOpeningAudioContext(stalledAudio, 1), false);
assert.equal(await resumeOpeningAudioContext({state: 'closed'}), false);
const startupSource = readFileSync(new URL('../main.js', import.meta.url), 'utf8');
assert.match(startupSource, /env\.CIV2_SKIP_OPENING = '1'/);
assert.match(startupSource, /const hdMovieOptIn = hdArtAvailable && introNeedsGesture/);
assert.match(startupSource, /if \(hdMovieOptIn\)\s+env\.CIV2_BROWSER_HD_OPENING = '1'/);
assert.match(startupSource, /hdMovieOptIn,/);
assert.match(startupSource, /openingVideoNeedsGesture\(entries, hdArtAvailable, location.search\)/);
assert.match(startupSource, /hd && !!window\.civ2Hd\?\.packBytes/);
for (const field of ['ownedOpeningPresent', 'hdArtAvailable', 'skipRequested', 'gestureRequired', 'silent-fallback'])
    assert.ok(startupSource.includes(field));
assert.match(startupSource, /window\.civ2Intro = \{/);
assert.match(startupSource, /await unlockOpeningAudio\(\)/);
assert.match(startupSource, /await resumeOpeningAudioContext\(audio\)/);
assert.match(startupSource, /env\.CIV2_NOSOUND = '1'/);
assert.match(startupSource, /env\.CIV2_LOG_VIDEO = '1'/);
assert.match(startupSource, /!introDiagnose && !new URLSearchParams/);
const hostSource = readFileSync(new URL('../host.js', import.meta.url), 'utf8');
assert.match(hostSource, /opts\.audioContext \|\| null/);
const gamePage = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
assert.match(gamePage, /id="intro-start"/);

// Browser graphics choice persists only as a preference; explicit URL wins.
assert.equal(graphicsFromQuery('?hd=1'), 'hd');
assert.equal(graphicsFromQuery('?hd=0'), 'classic');
assert.equal(graphicsFromQuery('?lang=zh-CN'), null);
assert.equal(hdArg('hd'), '1');
const pref = new Map(), prefs = {
    async getMeta(k) { return pref.get(k); },
    async setMeta(k, v) { pref.set(k, v); }
};
let prompts = 0;
assert.equal(await resolveGraphicsPreference(prefs, '', true, async () => {
    prompts++; return 'hd';
}), 'hd');
assert.equal(pref.get(GRAPHICS_PREFERENCE_KEY), 'hd');
assert.equal(await resolveGraphicsPreference(prefs, '', true, async () => {
    prompts++; return 'classic';
}), 'hd');
assert.equal(prompts, 1);
assert.equal(await resolveGraphicsPreference(prefs, '?hd=0', true, async () => {
    throw Error('explicit URL should never ask');
}), 'classic');
assert.equal(pref.get(GRAPHICS_PREFERENCE_KEY), 'hd');
pref.clear();
assert.equal(await resolveGraphicsPreference(prefs, '', false, async () => 'hd'), 'classic');
const graphicsPage = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
for (const id of ['graphics-mode', 'graphics-choice-dialog', 'graphics-first-classic',
                  'graphics-first-hd', 'graphics-first-unavailable'])
    assert.ok(graphicsPage.includes('id="' + id + '"'));
assert.match(startupSource, /await resolveGraphicsPreference/);
assert.match(startupSource, /web\.graphics_switch_confirm/);
assert.match(startupSource, /location\.assign\(url\.href\)/);

// // the desktop's scale (host.h's examples)
assert.equal(desktopScale(1920, 1080, 0), 1);
assert.equal(desktopScale(2560, 1440, 0), 2);
assert.equal(desktopScale(3840, 2160, 0), 3);
assert.equal(desktopScale(2940, 1782, 0), 3);
assert.equal(desktopScale(800, 600, 2), 1);

// Larger native UI targets original game readability, not Canvas stretching.
// Default game layout and explicit native-scale settings are unaffected.
assert.equal(desktopUiScale(2560, 1440, 0, ''), 2);
assert.equal(desktopUiScale(2560, 1440, 0, '?lang=zh-CN&ui=large'), 3);
assert.equal(desktopUiScale(1920, 1080, 0, '?ui=large'), 2);
assert.equal(desktopUiScale(3840, 2160, 0, '?ui=large'), 4);
assert.equal(desktopUiScale(2560, 1440, 2, '?ui=large'), 2);
assert.equal(desktopUiScale(1280, 720, 0, '?ui=large'), 1);
assert.deepEqual(initialDesktopGeometry(2560, 1440, 0, ''), {width: 1280, height: 720, scale: 2});
assert.deepEqual(initialDesktopGeometry(2560, 1440, 0, '?ui=large'), {width: 853, height: 560, scale: 3});
assert.deepEqual(initialDesktopGeometry(1920, 1080, 0, '?ui=large'), {width: 960, height: 560, scale: 2});
assert.deepEqual(initialDesktopGeometry(3840, 2160, 0, '?ui=large'), {width: 960, height: 560, scale: 4});
assert.deepEqual(initialDesktopGeometry(2560, 1440, 2, '?ui=large'), {width: 1280, height: 720, scale: 2});
assert.deepEqual(initialDesktopGeometry(1280, 720, 0, '?ui=large'), {width: 1280, height: 720, scale: 1});
assert.deepEqual(initialDesktopGeometry(640, 480, 0, '?ui=large'), {width: 640, height: 480, scale: 1});
assert.deepEqual(initialDesktopGeometry(800, 600, 0, '?ui=large'), {width: 800, height: 600, scale: 1});
const largeGeometry = initialDesktopGeometry(2560, 1440, 0, '?ui=large');
const safeFrame = canvasFitSize(largeGeometry.width, largeGeometry.height, 2560, 1440, 1, 'fit');
assert.ok(safeFrame.width <= 2560 && safeFrame.height <= 1440);
assert.ok(largeGeometry.height >= 560 && largeGeometry.width >= 800);
assert.ok(Math.abs(safeFrame.width / safeFrame.height - largeGeometry.width / largeGeometry.height) < 1e-12);





// The visible controls must be in the actual shipped page, outside the
// canvas, and labels must go through the standard game's translations.
const displayHtml = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
for (const name of ['game-controls', 'display-mode', 'fullscreen', 'saves-open'])
    assert.match(displayHtml, new RegExp('id="' + name + '"'));
for (const key of ['web.display', 'web.display_integer', 'web.display_fit', 'web.enter_fullscreen'])
    assert.match(displayHtml, new RegExp('data-t="' + key.replace('.', '\\.') + '"'));
const pageSource = readFileSync(new URL('../main.js', import.meta.url), 'utf8');
assert.match(pageSource, /addEventListener\('change',/);
assert.match(pageSource, /dispatchEvent\(new Event\('civ2-display-change'\)\)/);
assert.match(pageSource, /requestFullscreen\(\)/);
assert.match(pageSource, /controls\.addEventListener\('keydown'/);

// CIV2-T012: compact toolbar retains an explicit reopen handle, and the
// high-contrast mute button has two deterministic vector states (not emoji).
{
const toolbarHtml = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const toolbarMain = readFileSync(new URL('../main.js', import.meta.url), 'utf8');
for (const id of ['game-controls-content', 'controls-toggle', 'controls-toggle-chevron',
                  'audio-waves', 'audio-slash', 'display-help'])
    assert.match(toolbarHtml, new RegExp('id="' + id + '"'));
assert.match(toolbarHtml, /aria-controls="game-controls-content" aria-label="Collapse controls"/);
assert.match(toolbarHtml, /aria-expanded="true"/);
assert.match(toolbarHtml, /id="audio-mute" class="icon-button"/);
assert.match(toolbarHtml, /id="audio-slash"[^>]*style="display:none"/);
assert.match(toolbarHtml, /#game-controls #audio-mute\[aria-pressed="true"\]/);
assert.match(toolbarHtml, /#game-controls \.icon-button/);
assert.doesNotMatch(toolbarHtml, /🔊|🔇/);
assert.doesNotMatch(toolbarMain, /audioMute\.textContent/);
for (const token of ['content.hidden = collapsed', "toggle.setAttribute('aria-expanded'",
                     "toggle.setAttribute('aria-label'", "chevron.setAttribute('d'",
                     "audioMute.setAttribute('aria-pressed'", "$('audio-waves').style.display = muted ? 'none' : ''",
                     "$('audio-slash').style.display = muted ? '' : 'none'",
                     "controls.addEventListener('keydown', (e) => e.stopPropagation())",
                     "controls.addEventListener('keyup', (e) => e.stopPropagation())",
                     "window.dispatchEvent(new Event('civ2-display-change'))",
                     "mode.title = hint"]) {
    assert.ok(toolbarMain.includes(token), 'missing toolbar behavior: ' + token);
}
const local = new Map();
const fakeStorage = {
    getItem(key) { return local.get(key) ?? null; },
    setItem(key, value) { local.set(key, value); },
};
const toggleState = createToolbarCollapse(fakeStorage);
assert.equal(toggleState.collapsed, false); // default open: discoverable
toggleState.setCollapsed(true);
assert.equal(toggleState.collapsed, true);
assert.equal(local.get(TOOLBAR_KEY), 'collapsed');
assert.equal(createToolbarCollapse(fakeStorage).collapsed, true); // reload
toggleState.setCollapsed(false);
assert.equal(createToolbarCollapse(fakeStorage).collapsed, false);
assert.equal(local.get(TOOLBAR_KEY), 'expanded');
assert.equal(createToolbarCollapse({getItem() { throw new Error('denied'); }}).collapsed, false);
const blocked = createToolbarCollapse({getItem() { return 'collapsed'; }, setItem() { throw new Error('denied'); }});
blocked.setCollapsed(false);
assert.equal(blocked.collapsed, false); // storage failure never strands the menu
assert.equal(toolbarLabels('zh-Hans').expand, '展开工具栏');
assert.equal(toolbarLabels('zh-Hant').collapse, '收合工具列');
assert.equal(toolbarLabels('de').expand, 'Expand controls');
assert.match(toolbarLabels('zh-CN').integer, /整数倍/);
assert.match(toolbarLabels('zh-TW').fit, /整數倍/);
assert.match(toolbarLabels('en').fit, /fractional/);
// Same-size modes do NOT need different pixels: integer and fractional
// presentation coincide exactly at whole-number scaling or 1x.
assert.deepEqual(canvasFitSize(1280, 720, 2560, 1440, 1, 'integer'),
                 canvasFitSize(1280, 720, 2560, 1440, 1, 'fit'));
assert.deepEqual(canvasFitSize(800, 600, 800, 600, 1, 'integer'),
                 canvasFitSize(800, 600, 800, 600, 1, 'fit'));
}

// Display toolbar can switch between the existing modes without creating
// another game desktop or restarting it; URL parameters remain orthogonal.
assert.equal(displayModeFromSearch(''), 'integer');
assert.equal(displayModeFromSearch('?display=integer'), 'integer');
assert.equal(displayModeFromSearch('?display=fit'), 'fit');
assert.equal(displayModeFromSearch('?lang=zh-CN&display=fit'), 'fit');
assert.equal(displayModeFromSearch('?display=unsupported'), 'integer');

// Browser resize during animations is paint-only by default; dynamic game
// desktop reflow is a legacy opt-in for comparisons.
assert.equal(liveDesktopResize(''), false);
assert.equal(liveDesktopResize('?hd=0'), false);
assert.equal(liveDesktopResize('?desktopResize=fit'), false);
assert.equal(liveDesktopResize('?desktopResize=live'), true);
assert.equal(liveDesktopResize('?desktopResize=live&hd=0'), true);

// The physical viewport can be high-DPI (device pixels), while canvas sizes
// are CSS pixels. Fit fills the available viewport without changing aspect.
const integer = canvasFitSize(1024, 768, 2560, 1440);
assert.equal(integer.scale, 1);
assert.deepEqual([integer.width, integer.height], [1024, 768]);
const fitLarge = canvasFitSize(1024, 768, 2560, 1440, 1, 'fit');
assert.equal(fitLarge.scale, 1.875);
assert.deepEqual([fitLarge.width, fitLarge.height], [1920, 1440]);
assert.equal(fitLarge.width / fitLarge.height, 4 / 3);
const hiDpi = canvasFitSize(1280, 720, 2400, 1350, 1.25, 'fit');
assert.deepEqual([hiDpi.width, hiDpi.height], [1920, 1080]);
const exact = canvasFitSize(1280, 720, 2560, 1440, 1, 'integer');
assert.deepEqual([exact.width, exact.height], [2560, 1440]);
const shrink = canvasFitSize(1280, 720, 640, 360, 1.5, 'fit');
assert.deepEqual([shrink.width, shrink.height], [1280 / 3, 240]);

// pixels: ARGB words -> RGBA bytes, opaque
const dst = new Uint32Array(1);
argbToRgba(new Uint32Array([0x00112233]), dst, 1);
assert.deepEqual([...new Uint8Array(dst.buffer)], [0x11, 0x22, 0x33, 0xff]);

// WASI over the memory file system
assert.equal(normalize('/civ2/./a/../B.TXT'), '/civ2/B.TXT');
const fs = new MemFS(), changed = [];
fs.onchange = (p, removed) => changed.push(p + (removed ? ' -' : ''));
fs.put('/civ2/RULES.TXT', new TextEncoder().encode('hello'));
const mem = new WebAssembly.Memory({initial: 1});
const wasi = makeWasi(fs, ['civ2', '/civ2'], {CIV2_DATA: '/data'}, () => mem);
const v = new DataView(mem.buffer), u8 = new Uint8Array(mem.buffer);
const str = (at, s) => { const b = new TextEncoder().encode(s); u8.set(b, at); return b.length; };
// open, read
let n = str(1000, 'civ2/RULES.TXT');
assert.equal(wasi.path_open(3, 0, 1000, n, 0, 2n, 0n, 0, 2000), 0);
const fd = v.getUint32(2000, true);
v.setUint32(3000, 4000, true); v.setUint32(3004, 3, true);
assert.equal(wasi.fd_read(fd, 3000, 1, 3010), 0);
assert.equal(v.getUint32(3010, true), 3);
assert.equal(new TextDecoder().decode(u8.subarray(4000, 4003)), 'hel');
assert.equal(wasi.fd_seek(fd, 0n, 2, 3020), 0);
assert.equal(v.getBigUint64(3020, true), 5n);
assert.equal(wasi.fd_close(fd), 0);
// create, write, rename, unlink
n = str(1000, 'civ2/GAME.SAV');
assert.equal(wasi.path_open(3, 0, 1000, n, 1 | 8, 64n, 0n, 0, 2000), 0);
const out = v.getUint32(2000, true);
str(4000, 'saved!');
v.setUint32(3000, 4000, true); v.setUint32(3004, 6, true);
assert.equal(wasi.fd_write(out, 3000, 1, 3010), 0);
assert.equal(wasi.fd_close(out), 0);
assert.equal(new TextDecoder().decode(fs.get('/civ2/GAME.SAV')), 'saved!');
n = str(1000, 'civ2/GAME.SAV');
const m = str(1100, 'civ2/OTHER.SAV');
assert.equal(wasi.path_rename(3, 1000, n, 3, 1100, m), 0);
assert.equal(fs.get('/civ2/GAME.SAV'), null);
assert.equal(wasi.path_unlink_file(3, 1100, m), 0);
assert.deepEqual([...new Set(changed)], ['/civ2/GAME.SAV', '/civ2/GAME.SAV -', '/civ2/OTHER.SAV', '/civ2/OTHER.SAV -']);
// missing files, /dev/null
n = str(1000, 'civ2/NONE.TXT');
assert.equal(wasi.path_open(3, 0, 1000, n, 0, 2n, 0n, 0, 2000), 44);
n = str(1000, 'dev/null');
assert.equal(wasi.path_open(3, 0, 1000, n, 1, 64n, 0n, 0, 2000), 0);
assert.equal(wasi.fd_write(v.getUint32(2000, true), 3000, 1, 3010), 0);
assert.equal(v.getUint32(3010, true), 6);
// a directory's entries
n = str(1000, 'civ2');
assert.equal(wasi.path_open(3, 0, 1000, n, 2, 0n, 0n, 0, 2000), 0);
assert.equal(wasi.fd_readdir(v.getUint32(2000, true), 5000, 4096, 0n, 3030), 0);
const names = [];
for (let p = 5000, end = 5000 + v.getUint32(3030, true); p < end;) {
    const len = v.getUint32(p + 16, true);
    names.push(new TextDecoder().decode(u8.subarray(p + 24, p + 24 + len)));
    p += 24 + len;
}
assert.deepEqual(names, ['.', '..', 'RULES.TXT']);
// Civ II Save As "New Folder": WASI supports a real nested directory,
// and the same directory's relative autosave files can be created/rotated.
n = str(1000, 'civ2/20261121');
assert.equal(wasi.path_create_directory(3, 1000, n), 0);
assert.equal(wasi.path_create_directory(3, 1000, n), 20); // EXISTS
n = str(1000, 'civ2/20261121/_AUTO.SAV');
assert.equal(wasi.path_open(3, 0, 1000, n, 1 | 8, 64n, 0n, 0, 2000), 0);
assert.equal(wasi.fd_write(v.getUint32(2000, true), 3000, 1, 3010), 0);
assert.equal(wasi.fd_close(v.getUint32(2000, true)), 0);
assert.equal(new TextDecoder().decode(fs.get('/civ2/20261121/_AUTO.SAV')), 'saved!');
// The folder remains addressable after a manual save.
assert.deepEqual(fs.list('/civ2/20261121').map(([name]) => name), ['_AUTO.SAV']);

// exit
assert.throws(() => wasi.proc_exit(3), (e) => e.code === 3);

// .zip: stored and deflated
function zip(files) {
    const parts = [], central = [];
    let at = 0;
    for (const [name, data, deflate] of files) {
        const body = deflate ? deflateRawSync(data) : data, fname = Buffer.from(name);
        const h = Buffer.alloc(30);
        h.writeUInt32LE(0x04034b50, 0); h.writeUInt16LE(deflate ? 8 : 0, 8); h.writeUInt32LE(body.length, 18);
        h.writeUInt32LE(data.length, 22); h.writeUInt16LE(fname.length, 26);
        const c = Buffer.alloc(46);
        c.writeUInt32LE(0x02014b50, 0); c.writeUInt16LE(deflate ? 8 : 0, 10); c.writeUInt32LE(body.length, 20);
        c.writeUInt32LE(data.length, 24); c.writeUInt16LE(fname.length, 28); c.writeUInt32LE(at, 42);
        parts.push(h, fname, body);
        central.push(c, fname);
        at += 30 + fname.length + body.length;
    }
    const cd = Buffer.concat(central), e = Buffer.alloc(22);
    e.writeUInt32LE(0x06054b50, 0); e.writeUInt16LE(files.length, 8); e.writeUInt16LE(files.length, 10);
    e.writeUInt32LE(cd.length, 12); e.writeUInt32LE(at, 16);
    const b = Buffer.concat([...parts, cd, e]);
    return b.buffer.slice(b.byteOffset, b.byteOffset + b.length);
}
const text = Buffer.from('RULES '.repeat(100));
const files = await unzip(zip([['Civ2/RULES.TXT', text, true], ['Civ2/Sound\\A.WAV', Buffer.from('wav'), false]]));
assert.deepEqual(files.map((f) => f.name), ['Civ2/RULES.TXT', 'Civ2/Sound/A.WAV']);
assert.equal(Buffer.from(files[0].data).toString(), text.toString());

// .zip written (saves.js's export) and read back: deflated where smaller,
// stored otherwise, an empty file, a name not in ASCII
assert.equal(crc32(Buffer.from('123456789')), 0xcbf43926);
const big = new Uint8Array(100000).map((_, i) => (i * 7) & 0x3f), noise = new Uint8Array(300).map(() => Math.random() * 256);
const written = await makeZip([{name: 'A.SAV', data: big, mtime: Date.UTC(2026, 10, 14, 12)},
                               {name: 'Scenario/MINE.SCN', data: noise}, {name: 'EMPTY.SAV', data: new Uint8Array(0)},
                               {name: 'Été.SAV', data: Buffer.from('é')}]);
assert.ok(written.length < 20000);          // (the big one deflated)
const back = await unzip(written.buffer);
assert.deepEqual(back.map((f) => f.name), ['A.SAV', 'Scenario/MINE.SCN', 'EMPTY.SAV', 'Été.SAV']);
assert.deepEqual(back[0].data, big);
assert.deepEqual(back[1].data, noise);
assert.equal(back[2].data.length, 0);
assert.equal(Buffer.from(back[3].data).toString(), 'é');
const stored = await makeZip([{name: 'A.SAV', data: big}], {deflate: false});
assert.equal(stored.length, 30 + 5 + big.length + 46 + 5 + 22);
assert.deepEqual((await unzip(stored.buffer))[0].data, big);
// (the same as an independent reader, node's zlib, reads it: the deflated member raw)
const lh = new DataView(written.buffer);
assert.equal(lh.getUint16(8, true), 8);
assert.deepEqual(new Uint8Array(inflateRawSync(written.subarray(30 + 5, 30 + 5 + lh.getUint32(18, true)))), big);

// the player's files: saved games, settings in the game's folder, the scenarios they made
assert.equal(savesKind('GAME.SAV'), 'sav');
assert.equal(savesKind('Scenario/x.mp'), 'scn');
assert.equal(savesKind('civ.ini'), 'settings');
assert.equal(savesKind('Sub/CIV.INI'), null);
assert.equal(savesKind('RULES.TXT'), null);
const T = 1700000000000;
const stored2 = [['Civ2Art.dll', {mtime: T}], ['RULES.TXT', {mtime: T}], ['CIV.INI', {mtime: T + 5}],
                 ['ROME.SCN', {mtime: T}], ['EUROPE.MP', {mtime: T + 3600e3}], ['MINE.SCN', {mtime: T + 3600e3}],
                 ['Scenario/OLD.SCN', {mtime: T}], ['Ca_Auto.SAV', {mtime: T}], ['HALLFAME.DAT', {mtime: T + 9}]];
assert.deepEqual(playerFiles(stored2, {names: ['Civ2Art.dll', 'RULES.TXT', 'ROME.SCN', 'EUROPE.MP', 'Scenario/OLD.SCN',
                                               'CIV.INI'], at: T + 60e3}),
                 ['CIV.INI', 'EUROPE.MP', 'MINE.SCN', 'Ca_Auto.SAV', 'HALLFAME.DAT']);
// (no note of the game's copy: scenarios written well after Civ2Art.dll was copied)
assert.deepEqual(playerFiles(stored2, undefined), ['CIV.INI', 'EUROPE.MP', 'MINE.SCN', 'Ca_Auto.SAV', 'HALLFAME.DAT']);
// where imported files go: folders the game has kept, others left out, the case of what is there
const have = ['RULES.TXT', 'Scenario/OLD.SCN', 'Sound/A.WAV', 'civ.ini', 'GAME.SAV'];
assert.equal(importPath('NEW.SAV', have), 'NEW.SAV');
assert.equal(importPath('Civ2/NEW.SAV', have), 'NEW.SAV');
assert.equal(importPath('my saves/x/NEW.SAV', have), 'NEW.SAV');
assert.equal(importPath('scenario/MINE.SCN', have), 'Scenario/MINE.SCN');
assert.equal(importPath('Civ2/Scenario/MINE.SCN', have), 'Scenario/MINE.SCN');
assert.equal(importPath('CIV.INI', have), 'civ.ini');
assert.equal(importPath('game.sav', have), 'GAME.SAV');
assert.equal(importPath('../../etc/x.SAV', have), 'x.SAV');
const savesZip = await makeZip([{name: 'Civ2/ONE.SAV', data: Buffer.from('1')}, {name: 'Civ2/CIV.INI', data: Buffer.from('i')},
                                {name: 'Civ2/RULES.TXT', data: Buffer.from('no')}]);
const toPut = await savesToImport([{name: 'saves.zip', data: savesZip}, {name: 'TWO.SAV', data: Buffer.from('2')},
                                   {name: 'notes.txt', data: Buffer.from('no')}], have);
assert.deepEqual(toPut.map(([k, d]) => k + '=' + Buffer.from(d)), ['ONE.SAV=1', 'civ.ini=i', 'TWO.SAV=2']);
// T011: a self-exported save ZIP remembers user-created folders even in a
// fresh browser profile with no existing folder. Legacy untagged ZIPs still
// flatten unknown outer folders (tested above) for backward compatibility.
const campaignBytes = Buffer.from('autoturn 12');
const ownerStore = {
    async all() {
        return [
            ['20261121/_AUTO.SAV', {data: campaignBytes, mtime: T + 7000}],
            ['20261121/ROME.SAV', {data: Buffer.from('rome'), mtime: T + 8000}],
            ['20261122/_AUTO.SAV', {data: Buffer.from('other game'), mtime: T + 9000}],
            ['CIV.INI', {data: Buffer.from('[OpenCiv2]'), mtime: T + 5}],
            ['Civ2Art.dll', {data: Buffer.from('proprietary game file'), mtime: T}]
        ];
    },
    async getMeta() {
        return {names: ['Civ2Art.dll'], at: T};
    }
};
const savedCampaigns = await exportSaves(ownerStore);
const savedArchive = await unzip(savedCampaigns.data.buffer.slice(
    savedCampaigns.data.byteOffset, savedCampaigns.data.byteOffset + savedCampaigns.data.byteLength));
assert.deepEqual(savedCampaigns.names,
    ['20261121/_AUTO.SAV', '20261121/ROME.SAV', '20261122/_AUTO.SAV', 'CIV.INI']);
assert.ok(savedArchive.some((entry) => entry.name === 'openciv2-saves-manifest.json'));
assert.ok(!savedArchive.some((entry) => entry.name === 'Civ2Art.dll'));
const restoredCampaigns = await savesToImport([{name: 'downloaded.zip', data: savedCampaigns.data}], []);
assert.deepEqual(restoredCampaigns.map(([name]) => name), savedCampaigns.names);
assert.deepEqual(Buffer.from(restoredCampaigns[0][1]), campaignBytes);
// Re-import to an existing profile with differently cased keys should
// update those existing files, not create duplicates on case-sensitive IDB.
const existingCampaigns = await savesToImport(
    [{name: 'downloaded.zip', data: savedCampaigns.data}],
    ['20261121/rome.sav', 'civ.ini']);
assert.deepEqual(existingCampaigns.map(([name]) => name),
    ['20261121/_AUTO.SAV', '20261121/rome.sav', '20261122/_AUTO.SAV', 'civ.ini']);
// Also keep an existing directory's case when a restored campaign contains
// additional files or subfolders that do not already exist in IndexedDB.
const existingParent = await savesToImport(
    [{name: 'downloaded.zip', data: savedCampaigns.data}],
    ['20261121/other.sav', '20261122/old.sav']);
assert.deepEqual(existingParent.map(([name]) => name),
    ['20261121/_AUTO.SAV', '20261121/ROME.SAV', '20261122/_AUTO.SAV', 'CIV.INI']);
const nestedArchive = await makeZip([
    {name: 'openciv2-saves-manifest.json', data: Buffer.from(JSON.stringify({
        format: 'OpenCiv2-saves', version: 1,
        paths: ['Campaign/20261121/NEXT.SAV', 'Campaign/20261121/Nested/LATER.SAV']
    }))},
    {name: 'Campaign/20261121/NEXT.SAV', data: Buffer.from('first')},
    {name: 'Campaign/20261121/Nested/LATER.SAV', data: Buffer.from('second')}
]);
const differentlyCasedParents = await savesToImport(
    [{name: 'nested.zip', data: nestedArchive}], ['campaign/OLD.SAV']);
assert.deepEqual(differentlyCasedParents.map(([name]) => name),
    ['campaign/20261121/NEXT.SAV', 'campaign/20261121/Nested/LATER.SAV']);
// An injected/unsafe manifest path cannot escape the game's virtual folder.
const traversalArchive = await makeZip([
    {name: 'openciv2-saves-manifest.json', data: Buffer.from(JSON.stringify({
        format: 'OpenCiv2-saves', version: 1, paths: ['../outside.SAV', 'C:/evil.SAV', '20261121/GOOD.SAV']
    }))},
    {name: '../outside.SAV', data: Buffer.from('bad')},
    {name: 'C:/evil.SAV', data: Buffer.from('bad')},
    {name: '20261121/GOOD.SAV', data: Buffer.from('good')}
]);
assert.deepEqual((await savesToImport([{name: 'unsafe.zip', data: traversalArchive}], []))
    .map(([name]) => name), ['20261121/GOOD.SAV']);

// T013: fresh-profile import must canonicalize *within the same ZIP*,
// not just against pre-existing IndexedDB keys. Windows/Civ II treats
// Campaign/ROME.SAV and campaign/rome.sav as one file. The first
// spelling survives; the final data wins deterministically.
const caseArchive = await makeZip([
    {name: 'openciv2-saves-manifest.json', data: Buffer.from(JSON.stringify({
        format: 'OpenCiv2-saves', version: 1,
        paths: ['Campaign/ROME.SAV', 'campaign/rome.sav', 'CAMPAIGN/NEXT.SAV',
                'campaign/20261121/_AUTO.SAV', 'Campaign2/_AUTO.SAV']
    }))},
    {name: 'Campaign/ROME.SAV', data: Buffer.from('old data')},
    {name: 'campaign/rome.sav', data: Buffer.from('latest data')},
    {name: 'CAMPAIGN/NEXT.SAV', data: Buffer.from('next')},
    {name: 'campaign/20261121/_AUTO.SAV', data: Buffer.from('nested autosave')},
    {name: 'Campaign2/_AUTO.SAV', data: Buffer.from('separate game')}
]);
const caseFiles = [{name: 'portable.zip', data: caseArchive}];
const once = await savesToImport(caseFiles, []);
assert.deepEqual(once.map(([name]) => name), [
    'Campaign/ROME.SAV', 'Campaign/NEXT.SAV',
    'Campaign/20261121/_AUTO.SAV', 'Campaign2/_AUTO.SAV'
]);
assert.equal(Buffer.from(once[0][1]).toString(), 'latest data');
// Reimport must preserve exact existing case and must not create new
// browser keys that differ only in case.
const twice = await savesToImport(caseFiles, once.map(([name]) => name));
assert.deepEqual(twice.map(([name]) => name), once.map(([name]) => name));
// Also cover collisions among separate files selected together and the
// case of an existing differently spelled root key.
const independent = await savesToImport([
    {name: 'alpha.sav', data: Buffer.from('first')},
    {name: 'ALPHA.SAV', data: Buffer.from('last')},
    {name: 'CIV.INI', data: Buffer.from('settings')}
], ['civ.ini']);
assert.deepEqual(independent.map(([name]) => name), ['alpha.sav', 'civ.ini']);
assert.equal(Buffer.from(independent[0][1]).toString(), 'last');
// Store mutation must happen before live MemFS mutation, so a failed
// IndexedDB transaction leaves the player's currently running game
// untouched. Exercise both sides without touching real browser data.
const live = new MemFS();
live.mkdirs('/civ2');
const fakeStore = {
    written: [],
    async keys() { return []; },
    async putMany(rows) { this.written.push(...rows); }
};
const importedLive = await importSaves(fakeStore, caseFiles, live, '/civ2');
assert.deepEqual(importedLive, once.map(([name]) => name));
assert.equal(fakeStore.written.length, once.length);
assert.equal(new TextDecoder().decode(live.get('/civ2/Campaign/ROME.SAV')), 'latest data');
assert.equal(new TextDecoder().decode(live.get('/civ2/Campaign2/_AUTO.SAV')), 'separate game');
const failedLive = new MemFS();
failedLive.mkdirs('/civ2');
let attemptedWrite = false;
await assert.rejects(
    importSaves({
        async keys() { return []; },
        async putMany() { attemptedWrite = true; throw Error('simulated IndexedDB transaction failure'); }
    }, caseFiles, failedLive, '/civ2'),
    /simulated IndexedDB transaction failure/
);
assert.ok(attemptedWrite);
assert.equal(failedLive.files.size, 0); // no partially imported live saves

// ---- HD graphics' art (hdpack.js) ----

// a pack as the release's: C2ATLAS1, a count, a palette, entries in key order, the PNGs
function makePack(pics) {
    const keys = Object.keys(pics).sort(), head = 12 + 768 + 180 * keys.length;
    const out = new Uint8Array(head + keys.reduce((n, k) => n + pics[k].length, 0)), v = new DataView(out.buffer);
    out.set(Buffer.from('C2ATLAS1'));
    v.setUint32(8, keys.length, true);
    for (let i = 0; i < 768; i++)
        out[12 + i] = i & 255;
    // (the PNGs in reverse order: the stored pack's offsets need not follow its keys)
    let at = out.length;
    keys.forEach((k, i) => {
        const p = 12 + 768 + 180 * i;
        out.set(Buffer.from(k), p);
        v.setUint32(p + 160, 8, true);
        v.setUint32(p + 164, 4, true);
        at -= pics[k].length;
        v.setUint32(p + 168, at, true);
        v.setUint32(p + 172, pics[k].length, true);
        v.setUint32(p + 176, 12345, true);
        out.set(pics[k], at);
    });
    return out;
}
const pics = {'advance/0': Buffer.alloc(300, 1), 'crop/file/units/1,1,64,48': Buffer.alloc(200, 2),
              'dither/1/0': Buffer.from('dither'), 'file/units': Buffer.alloc(150, 4), 'fog/2': Buffer.from('f'),
              'crop/resource/mk.dll/gifs/236/1,1,225,275': Buffer.alloc(40, 7),
              'crop/resource/mk.dll/gifs/215/1,1,108,30': Buffer.alloc(30, 8),
              'resource/x/gifs/1': Buffer.alloc(500, 5), 'tint/crop/file/units/1,1,64,48/3': Buffer.alloc(90, 6)};
const pack = makePack(pics);
const hex = (b) => createHash('sha256').update(b).digest('hex');
assert.equal(await sha256(pack), hex(pack));
assert.deepEqual(packIndex(pack).map((e) => e.key), Object.keys(pics).sort());
// the leaders' portraits not drawn (hd.c's NOT_CROPPED), the diplomacy icons drawn
assert.ok(!drawn('crop/resource/mk.dll/gifs/236/1,1,225,275') && drawn('crop/resource/mk.dll/gifs/215/1,1,108,30'));
// the city view's houses of the industrial era only, its early landscapes only
assert.ok(drawn('crop/resource/cv.dll/gifs/310/1,231,158,114') && !drawn('crop/resource/cv.dll/gifs/310/1,116,158,114'));
assert.ok(!drawn('crop/resource/cv.dll/gifs/310/1,1,158,114') && !drawn('crop/resource/cv.dll/gifs/310/125,429,123,82'));
assert.ok(drawn('resource/cv.dll/gifs/351') && !drawn('resource/cv.dll/gifs/352'));
// the advances' pictures; not the advisors' parchments nor tiles.dll 86's thin glyphs
assert.ok(drawn('advance/12') && !drawn('resource/tiles.dll/gifs/52') && !drawn('crop/resource/tiles.dll/gifs/86/398,134,64,64'));
// the announcements' wide pictures, not the tall ones (hd.c's WHOLE)
assert.ok(drawn('resource/tiles.dll/gifs/72') && drawn('resource/tiles.dll/gifs/76') && !drawn('resource/tiles.dll/gifs/71') &&
          !drawn('resource/tiles.dll/gifs/75') && !drawn('resource/tiles.dll/gifs/77'));
assert.ok(!drawn('crop/file/icons/166,223,30,30') && drawn('crop/file/icons/166,356,32,32'));
// the pictures hd.c draws kept, in their order, each with its PNG, read in chunks
for (const chunk of [64, 100, 1 << 20]) {
    const reads = [];
    const pruned = await prunePack(async (k) => {
        reads.push(k);
        return pack.subarray(k * chunk, (k + 1) * chunk);
    }, chunk);
    const idx = packIndex(pruned);
    assert.deepEqual(idx.map((e) => e.key), Object.keys(pics).sort().filter((k) => drawn(k)));
    for (const e of idx)
        assert.deepEqual(Buffer.from(pruned.subarray(e.off, e.off + e.len)), pics[e.key]);
    assert.deepEqual(pruned.subarray(12, 12 + 768), pack.subarray(12, 12 + 768));
    assert.equal(new DataView(pruned.buffer).getUint32(12 + 768 + 176, true), 0);
    assert.equal(pruned.length, 12 + 768 + 180 * idx.length + idx.reduce((n, e) => n + e.len, 0));
    assert.equal(new Set(reads).size, reads.length);       // each chunk read once
}
// the site's pack: checked against the pin
const pinned = {tag: 'vT', pack_sha256: hex(pack), pack_size: pack.length};
const phases = new Set();
assert.deepEqual(await packFrom(new Blob([pack]), pinned, {progress: (ph) => phases.add(ph)}), pack);
assert.deepEqual([...phases], ['check']);
const other = makePack({...pics, 'fog/2': Buffer.from('g')});
await assert.rejects(packFrom(new Blob([other]), pinned), /not the one of the art's release vT/);
await assert.rejects(packFrom(new Blob([Buffer.from('hello world')]), pinned), /not an HD art pack/);
const stop = new AbortController();
stop.abort();
await assert.rejects(packFrom(new Blob([pack]), pinned, {signal: stop.signal}), {name: 'AbortError'});
// kept in the store in chunks, its description last; loaded for the game pruned
const hdStore = new Map();
const fake = {hdClear: async () => hdStore.clear(), hdPutMany: async (es) => es.forEach(([k, v]) => hdStore.set(k, v)),
              hdGet: async (k) => hdStore.get(k)};
const info = await keepPack(fake, pack, pinned);
assert.equal(info.size, pack.length);
assert.equal(info.chunks, 1);
assert.ok(hdStore.has('pruned') && hdStore.has('p0'));   // the pruned pack kept with it, read alone at a start
const again = {};
assert.deepEqual(await loadPack(fake, pinned, again), await prunePack(async () => pack));
assert.equal(again.packChunks, hdStore.get('pruned').chunks);
assert.equal(again.kept, undefined);
for (const k of [...hdStore.keys()])                    // (art kept before the pruned copy was: made at a start)
    if (/^p|pruned/.test(k))
        hdStore.delete(k);
const first = {};
assert.deepEqual(await loadPack(fake, pinned, first), await prunePack(async () => pack));
await first.kept;
assert.ok(hdStore.has('pruned') && hdStore.has('p0'));
assert.equal(await loadPack(fake, {...pinned, pack_sha256: 'other'}), null);         // another release's
await fake.hdClear();
assert.equal(await loadPack(fake, pinned), null);

// ---- the game's OpenCiv2 Options in CIV.INI, as the page reads them (options.js) ----

const ini0 = '[Civ2]\r\nFoo=1\r\n\r\n[OpenCiv2]\r\nMode=Standard\r\n\r\n[Other]\r\nx=y\r\n';
assert.equal(iniGet(ini0, 'openciv2', 'MODE'), 'Standard');
assert.equal(iniGet(ini0, 'OpenCiv2', 'Foo'), null);
assert.equal(iniSet(ini0, 'OpenCiv2', 'Mode', 'Classic'), ini0.replace('Mode=Standard', 'Mode=Classic'));
assert.equal(iniSet(ini0, 'OpenCiv2', 'Graphics', 'HD'), ini0.replace('Mode=Standard\r\n', 'Mode=Standard\r\nGraphics=HD\r\n'));
assert.equal(iniSet('', 'OpenCiv2', 'Graphics', 'HD'), '[OpenCiv2]\r\nGraphics=HD\r\n');
assert.equal(iniSet('[A]\nb=1\n', 'OpenCiv2', 'k', 'v'), '[A]\nb=1\n\n[OpenCiv2]\nk=v\n');
const ini1 = iniSet(ini0, 'OpenCiv2', 'Graphics', 'HD');
assert.equal(hdWanted(ini1, null), 0);         // (the density: Auto, unless CIV.INI has GraphicsDensity=)
assert.equal(hdWanted(iniSet(ini1, 'OpenCiv2', 'GraphicsDensity', '2'), null), 2);
assert.equal(hdWanted(ini0, null), -1);
assert.equal(hdWanted(ini0, '1'), 0);
assert.equal(hdWanted(ini0, ''), 0);
assert.equal(hdWanted(ini0, '3'), 3);
assert.equal(hdWanted(ini1, '0'), -1);
assert.equal(hdWanted(iniSet(ini1, 'OpenCiv2', 'Mode', 'Classic'), '2'), -1);
assert.equal(hdWanted(iniSet(ini1, 'OpenCiv2', 'Mode', 'Classic'), null), -1);

// SHA-256 without crypto.subtle (a plain http:// site): as node's, at the block boundaries
for (const n of [0, 1, 55, 56, 63, 64, 65, 119, 120, 1000]) {
    const b = Uint8Array.from({length: n}, (_, i) => (i * 37 + n) & 255);
    assert.equal(Buffer.from(sha256js(b)).toString('hex'), createHash('sha256').update(b).digest('hex'));
}

{
// CIV2-T008: one persisted browser preference for effects, music and AVI.
const prefs = new Map();
const storage = {getItem: (key) => prefs.get(key) ?? null, setItem: (key, val) => prefs.set(key, val)};
const master = createAudioVolume(storage);
assert.equal(master.level, 100);
assert.equal(master.gain, 1);
assert.equal(master.muted, false);
const gains = [];
const off = master.subscribe((gain) => gains.push(gain));
master.setLevel(35);
assert.equal(master.gain, 0.35);
master.setMuted(true);
assert.equal(master.gain, 0);
master.setLevel(70);
assert.equal(master.gain, 0);  // changing slider while muted remains silent
master.setMuted(false);
assert.equal(master.gain, 0.7); // restores retained slider position
assert.deepEqual(gains, [0.35, 0, 0, 0.7]);
off();
master.setLevel(150);
assert.equal(master.level, 100);
assert.equal(gains.length, 4);
const reloadMaster = createAudioVolume(storage);
assert.equal(reloadMaster.level, 100);
assert.equal(reloadMaster.muted, false);
reloadMaster.setLevel(-100);
assert.equal(reloadMaster.level, 0);
assert.equal(createAudioVolume({getItem: () => '{bad-json', setItem: () => {}}).gain, 1);
assert.equal(createAudioVolume({getItem: () => '{"level":50,"muted":true}', setItem: () => {}}).gain, 0);
assert.equal(audioLabels('zh-Hans').mute, '静音');
assert.equal(audioLabels('zh-Hant').unmute, '取消靜音');
assert.equal(audioLabels('en').volume, 'Volume');
}

console.log('src/web unit tests passed');
