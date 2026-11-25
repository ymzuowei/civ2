// CIV2-H021: reference-only terrain guide using the player's own classic
// TERRAIN1/TERRAIN2 sheets and the exact pinned HD pack already in IndexedDB.
// Never downloads a second HD pack, modifies game files, or changes a save.
import {packIndex, CHUNK} from './hdpack.js';

export const TERRAIN_ROWS = [
    ['沙漠', 'Desert', '绿洲', 'Oasis', '沙漠石油', 'Desert Oil'],
    ['平原', 'Plains', '野牛', 'Buffalo', '小麦', 'Wheat'],
    ['草原', 'Grassland', '草原特殊位 A', 'Grassland A', '草原特殊位 B', 'Grassland B'],
    ['森林', 'Forest', '雉鸡', 'Pheasant', '丝绸', 'Silk'],
    ['丘陵', 'Hills', '煤炭', 'Coal', '葡萄酒', 'Wine'],
    ['山地', 'Mountains', '黄金', 'Gold', '铁矿', 'Iron'],
    ['苔原', 'Tundra', '野生动物', 'Game', '毛皮', 'Furs'],
    ['冰川', 'Glacier', '象牙', 'Ivory', '冰川石油', 'Glacier Oil'],
    ['沼泽', 'Swamp', '泥炭', 'Peat', '香料', 'Spice'],
    ['丛林', 'Jungle', '宝石', 'Gems', '水果', 'Fruit'],
    ['海洋', 'Ocean', '鱼', 'Fish', '鲸鱼', 'Whales'],
];

const tile = (sheet, x, y, w = 64, h = 32) => ({sheet, x, y, w, h});
export const terrainTile = (index) => tile('terrain1', 1, 1 + index * 33);
export const specialTile = (index, slot) =>
    tile('terrain1', slot === 'A' ? 131 : 196, 1 + index * 33);
export const improvementTile = (stage) =>
    tile('terrain1', 456, stage === 'irrigation' ? 100 : 133);
const landDetail = (index) => {
    if (index === 3) return tile('terrain2', 1, 133); // forest representative
    if (index === 4) return tile('terrain2', 1, 265); // hills representative
    if (index === 5) return tile('terrain2', 1, 199); // mountain representative
    return null;
};
export const hdKey = (s) =>
    'crop/file/' + s.sheet + '/' + [s.x, s.y, s.w, s.h].join(',');

// A guide row is a source-art *example*, not a complete native adjacency render.
export function guideRows(section) {
    if (section === 'resources')
        return TERRAIN_ROWS.flatMap((t, index) => ['A', 'B'].map((slot) => ({
            name: slot === 'A' ? t[2] : t[4],
            english: slot === 'A' ? t[3] : t[5],
            terrain: t[0], terrainEn: t[1], index, slot,
            layers: [terrainTile(index), specialTile(index, slot)],
        })));
    if (section === 'improvements')
        return [1, 2].flatMap((index) => [
            {name: TERRAIN_ROWS[index][0], english: TERRAIN_ROWS[index][1],
             state: 'base', index, layers: [terrainTile(index)]},
            {name: TERRAIN_ROWS[index][0], english: TERRAIN_ROWS[index][1],
             state: 'irrigation', index, layers: [terrainTile(index), improvementTile('irrigation')]},
            {name: TERRAIN_ROWS[index][0], english: TERRAIN_ROWS[index][1],
             state: 'farmland', index, layers: [terrainTile(index), improvementTile('farmland')]},
        ]);
    return TERRAIN_ROWS.map((t, index) => ({
        name: t[0], english: t[1], index,
        layers: [terrainTile(index), ...(landDetail(index) ? [landDetail(index)] : [])],
    })).concat([{name: '海岸（拼接片段）', english: 'Coast (fragment)',
                 layers: [tile('terrain2', 67, 429, 32, 16)]}]);
}

export function guideLabels(lang) {
    const zh = /^zh[-_](hans|cn|sg)/i.test(lang || '');
    return zh ? {
        title: '地形与资源指南', open: '地形指南', close: '关闭指南',
        terrain: '基础地形', resources: '特殊资源', improvements: '地块改良',
        classic: '原版 UI', hd: '高清 UI', loading: '正在读取已导入的游戏素材…',
        classicUnavailable: '未找到原版 TERRAIN1/TERRAIN2，请检查已导入的游戏文件。',
        hdUnavailable: '当前浏览器尚未缓存 HD 地形包；原版图样仍可查看。',
        state: {base: '未改造', irrigation: '灌溉（第一次 I）', farmland: '农场（第二次 I）'},
        note: '真实图样裁切及代表性叠加预览；不是包含全部邻接、河流或城市效果的游戏截图。',
        caution: '平原和草原在灌溉/农场后仍是不同地形。相同的 HD 农业覆盖图样可能遮挡底色。',
    } : {
        title: 'Terrain & Resource Guide', open: 'Terrain guide', close: 'Close guide',
        terrain: 'Terrain', resources: 'Special resources', improvements: 'Improvements',
        classic: 'Original UI', hd: 'HD UI', loading: 'Reading your existing game artwork…',
        classicUnavailable: 'Original TERRAIN1/TERRAIN2 not found in imported game files.',
        hdUnavailable: 'HD art is not cached in this browser; original tiles remain available.',
        state: {base: 'Unimproved', irrigation: 'Irrigation (first I)', farmland: 'Farmland (second I)'},
        note: 'Real source sprites and representative composites, not full neighbor-aware gameplay screenshots.',
        caution: 'Plains and Grassland stay distinct after improvements. Shared HD field overlays may hide their base colors.',
    };
}

async function loadImage(bytes, mime, urls) {
    const url = URL.createObjectURL(new Blob([bytes], {type: mime}));
    urls.push(url);
    const image = new Image();
    image.src = url;
    await image.decode();
    return image;
}

async function classicSheets(store, urls) {
    const keys = await store.keys();
    const result = {};
    for (const id of ['terrain1', 'terrain2']) {
        // Root game art, not SCENARIO/* replacements.
        const matches = keys.filter((name) => typeof name === 'string' &&
            new RegExp('^' + id + '\\.(gif|bmp)$', 'i').test(name));
        const name = matches.find((n) => /\.bmp$/i.test(n)) || matches[0];
        if (!name) continue;
        const row = await store.get(name);
        if (!row?.data) continue;
        result[id] = await loadImage(row.data, /\.bmp$/i.test(name) ? 'image/bmp' : 'image/gif', urls);
    }
    return result;
}

// Read only the necessary four-MiB chunks of the already-cached/pruned HD
// pack. Do not fetch the 250-MB original art pack from the network.
export async function cachedHdReader(store) {
    const [meta, info] = await Promise.all([store.hdGet('pruned'), store.hdGet('info')]);
    if (!meta || !info || meta.sha256 !== info.sha256 || meta.at !== info.at ||
        !Number.isInteger(meta.size) || meta.size <= 0)
        return null;
    const cache = new Map();
    const chunk = async (k) => {
        if (!cache.has(k)) {
            const value = await store.hdGet('p' + k);
            if (!value) throw new Error('HD cache is incomplete');
            if (cache.size >= 2) cache.delete(cache.keys().next().value);
            cache.set(k, value);
        }
        return cache.get(k);
    };
    const read = async (offset, size) => {
        if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(size) ||
            offset < 0 || size < 0 || offset + size > meta.size)
            throw new Error('HD pack entry outside cached bytes');
        const out = new Uint8Array(size);
        for (let p = 0; p < size;) {
            const absolute = offset + p, k = Math.floor(absolute / CHUNK);
            const bytes = await chunk(k);
            const at = absolute % CHUNK;
            const n = Math.min(size - p, bytes.length - at);
            if (n <= 0) throw new Error('Invalid HD cache chunk');
            out.set(bytes.subarray(at, at + n), p);
            p += n;
        }
        return out;
    };
    const first = await read(0, 12);
    if (new TextDecoder().decode(first.subarray(0, 8)) !== 'C2ATLAS1')
        return null;
    const count = new DataView(first.buffer).getUint32(8, true);
    if (count > 100000) throw new Error('Unexpected HD pack index');
    const head = await read(0, 780 + count * 180);
    const entries = new Map(packIndex(head).map((e) => [e.key, e]));
    return async (key) => {
        const item = entries.get(key);
        return item ? read(item.off, item.len) : null;
    };
}

function classicCrop(sheet, sprite) {
    const c = document.createElement('canvas');
    c.width = 64; c.height = 32;
    const ctx = c.getContext('2d', {willReadFrequently: true});
    const {x, y, w, h} = sprite;
    ctx.drawImage(sheet, x, y, w, h, w === 64 ? 0 : 16, h === 32 ? 0 : 8,
                  w, h);
    const frame = ctx.getImageData(0, 0, 64, 32);
    const a = frame.data;
    for (let y0 = 0; y0 < 32; y0++)
        for (let x0 = 0; x0 < 64; x0++) {
            const p = (y0 * 64 + x0) * 4;
            // Civ2's transparent magenta; remove palette matte outside the
            // diamond, not pixels inside its authentic original artwork.
            const outside = Math.abs((x0 + .5 - 32) / 32) +
                            Math.abs((y0 + .5 - 16) / 16) > 1.03;
            const magenta = a[p] > 220 && a[p + 1] < 70 && a[p + 2] > 220;
            if (outside || magenta) a[p + 3] = 0;
        }
    ctx.putImageData(frame, 0, 0);
    return c;
}

async function paint(canvas, layers, mode, art) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = mode === 'hd';
    for (const sprite of layers) {
        try {
            if (mode === 'classic') {
                const source = art.classic[sprite.sheet];
                if (!source) continue;
                const c = classicCrop(source, sprite);
                ctx.imageSmoothingEnabled = false;
                ctx.drawImage(c, 0, 0, 256, 128);
            } else if (art.hd) {
                const key = hdKey(sprite);
                let image = art.images.get(key);
                if (image === undefined) {
                    const bytes = await art.hd(key);
                    image = bytes ? await loadImage(bytes, 'image/png', art.urls) : null;
                    art.images.set(key, image);
                }
                if (image) ctx.drawImage(image, 0, 0, 256, 128);
            }
        } catch (e) {
            // A missing art entry should never break the game or other cards.
            console.warn('Terrain guide image:', e.message);
        }
    }
}

// Initializes on the setup page too; all image/IDB work is deferred until
// the player explicitly opens the guide. No audio, WASM, or game input hooks.
export function installTerrainGuide(store, lang) {
    const dialog = document.getElementById('terrain-guide-dialog');
    const open = document.getElementById('terrain-guide-open');
    const close = document.getElementById('terrain-guide-close');
    const area = document.getElementById('terrain-guide-list');
    const status = document.getElementById('terrain-guide-status');
    const text = guideLabels(lang);
    document.getElementById('terrain-guide-title').textContent = text.title;
    document.getElementById('terrain-guide-note').textContent = text.note;
    document.getElementById('terrain-guide-caution').textContent = text.caution;
    open.textContent = text.open;
    open.title = text.title;
    open.setAttribute('aria-label', text.title);
    close.textContent = text.close;
    const buttons = [...dialog.querySelectorAll('[data-guide-section]')];
    for (const button of buttons)
        button.textContent = text[button.dataset.guideSection];
    const stop = (event) => event.stopPropagation();
    for (const kind of ['keydown', 'keyup', 'keypress']) dialog.addEventListener(kind, stop);
    let art = null, active = null, sequence = 0;
    const render = async (section) => {
        const ticket = ++sequence;
        active = section;
        for (const b of buttons) b.setAttribute('aria-selected',
            String(b.dataset.guideSection === section));
        area.replaceChildren();
        const rows = guideRows(section);
        for (const row of rows) {
            const card = document.createElement('section');
            card.className = 'terrain-guide-card';
            const heading = document.createElement('h3');
            const suffix = row.state ? ' — ' + text.state[row.state] : '';
            heading.textContent = (lang?.toLowerCase().startsWith('zh')
                ? row.name + ' / ' + row.english
                : row.english) + suffix;
            if (row.terrain) heading.textContent += ' (' + row.terrain + ')';
            const pair = document.createElement('div');
            pair.className = 'terrain-guide-pair';
            const canvases = {};
            for (const mode of ['classic', 'hd']) {
                const cell = document.createElement('div');
                const label = document.createElement('span');
                label.textContent = text[mode];
                const canvas = document.createElement('canvas');
                canvas.width = 256; canvas.height = 128;
                canvas.setAttribute('role', 'img');
                canvas.setAttribute('aria-label', heading.textContent + ' — ' + text[mode]);
                cell.append(label, canvas); pair.append(cell); canvases[mode] = canvas;
            }
            card.append(heading, pair); area.append(card);
            // Give the browser opportunities between expensive image decodes.
            if (ticket !== sequence || !dialog.open) return;
            if (art.classic.terrain1)
                await paint(canvases.classic, row.layers, 'classic', art);
            if (art.hd)
                await paint(canvases.hd, row.layers, 'hd', art);
        }
    };
    const dispose = () => {
        ++sequence;
        area.replaceChildren();
        for (const url of art?.urls || []) URL.revokeObjectURL(url);
        art = null;
        active = null;
        status.textContent = '';
        open.focus();
    };
    dialog.addEventListener('close', dispose);
    close.addEventListener('click', () => dialog.close());
    for (const b of buttons) b.addEventListener('click', () => {
        if (b.dataset.guideSection !== active && art)
            render(b.dataset.guideSection).catch((e) => {status.textContent = e.message;});
    });
    open.addEventListener('click', async () => {
        if (dialog.open) return;
        dialog.showModal();
        status.textContent = text.loading;
        const urls = [];
        try {
            const [classic, hd] = await Promise.all([
                classicSheets(store, urls),
                cachedHdReader(store).catch(() => null),
            ]);
            if (!dialog.open) { for (const url of urls) URL.revokeObjectURL(url); return; }
            art = {classic, hd, urls, images: new Map()};
            const missing = [];
            if (!classic.terrain1) missing.push(text.classicUnavailable);
            if (!hd) missing.push(text.hdUnavailable);
            status.textContent = missing.join(' ');
            await render('terrain');
        } catch (e) {
            status.textContent = e.message;
        }
    });
}
