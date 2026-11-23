// WASM32 pointers are i32 values at the JS import boundary. Above 2 GiB
// JavaScript receives the same address as a negative signed integer.
// Treat *addresses* as unsigned u32, but reject invalid spans before access.
// This module does not allocate game memory and never modifies saved files.

export function wasm32Offset(pointer, length, byteLength) {
    if (!Number.isInteger(pointer) || pointer < -0x80000000 || pointer > 0xffffffff)
        throw new RangeError('Invalid WASM32 pointer');
    if (!Number.isSafeInteger(length) || length < 0)
        throw new RangeError('Invalid WASM32 span length');
    if (!Number.isSafeInteger(byteLength) || byteLength < 0)
        throw new RangeError('Invalid WASM linear-memory length');
    const offset = pointer >>> 0;
    if (offset > byteLength || length > byteLength - offset)
        throw new RangeError('WASM32 memory access is outside linear memory');
    return offset;
}

export function wasm32Bytes(memory, pointer, length) {
    const buffer = memory.buffer;
    return new Uint8Array(buffer, wasm32Offset(pointer, length, buffer.byteLength), length);
}

export function wasm32Words(memory, pointer, count) {
    if (!Number.isSafeInteger(count) || count < 0 || count > Math.floor(0xffffffff / 4))
        throw new RangeError('Invalid WASM32 word count');
    const buffer = memory.buffer;
    const offset = wasm32Offset(pointer, count * 4, buffer.byteLength);
    if (offset % 4 !== 0)
        throw new RangeError('Unaligned WASM32 word pointer');
    return new Uint32Array(buffer, offset, count);
}

// Cache a DataView until WebAssembly.Memory.grow replaces its buffer.
// Each accessor checks its own byte width, avoiding accidental wraparound
// when callers pass p + fieldOffset through the signed i32 boundary.
export function makeWasm32DataView(getMemory) {
    let buffer = null, view = null;
    const current = () => {
        const next = getMemory().buffer;
        if (next !== buffer) {
            buffer = next;
            view = new DataView(buffer);
        }
        return view;
    };
    const offset = (v, p, n) => wasm32Offset(p, n, v.byteLength);
    return {
        getUint8(p) { const v = current(); return v.getUint8(offset(v, p, 1)); },
        setUint8(p, x) { const v = current(); v.setUint8(offset(v, p, 1), x); },
        getUint32(p, le) { const v = current(); return v.getUint32(offset(v, p, 4), le); },
        setUint32(p, x, le) { const v = current(); v.setUint32(offset(v, p, 4), x, le); },
        getInt32(p, le) { const v = current(); return v.getInt32(offset(v, p, 4), le); },
        setInt32(p, x, le) { const v = current(); v.setInt32(offset(v, p, 4), x, le); },
        getBigUint64(p, le) { const v = current(); return v.getBigUint64(offset(v, p, 8), le); },
        setBigUint64(p, x, le) { const v = current(); v.setBigUint64(offset(v, p, 8), x, le); },
    };
}
