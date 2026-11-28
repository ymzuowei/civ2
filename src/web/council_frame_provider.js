// T025 isolated Council random-access decoder seam. No game integration.
// Input MUST come from a separately verified no-B-frame AVC MP4 demuxer,
// with exact original frame mapping, codec config and source/derived identity.
// This module does not authenticate a manifest, demux MP4 or change audio.
const MAX_FRAMES = 100000, MAX_PREROLL_US = 1000000;
const MAX_PACKETS = 120, MAX_BYTES = 4 * 1024 * 1024;
const integer = (v,min,max) => Number.isSafeInteger(v) && v >= min && v <= max;
function check(ok, reason) { if (!ok) throw new RangeError(reason); }

export function planCouncilSeek(table, nativeFrame, payloadLength) {
    check(table && integer(table.nativeStart,0,0x7fffffff) &&
        Array.isArray(table.samples) && integer(table.samples.length,1,MAX_FRAMES) &&
        integer(payloadLength,1,128*1024*1024), "TABLE_SHAPE");
    const index = nativeFrame - table.nativeStart;
    check(integer(nativeFrame,0,0x7fffffff) && integer(index,0,table.samples.length-1), "FRAME_RANGE");
    let key = -1, prevEnd = 0, prevByteEnd = 0;
    for (let i=0;i<table.samples.length;i++) {
        const p=table.samples[i];
        check(p && integer(p.ptsUs,0,3600000000) && integer(p.durationUs,1,1000000) &&
            integer(p.offset,0,payloadLength-1) && integer(p.size,1,payloadLength-p.offset) &&
            typeof p.key==="boolean", "SAMPLE_SHAPE");
        // This narrow candidate accepts ordered, non-overlapping no-B samples.
        // Source parity and original stream start remain separate verification.
        check((i===0 ? p.key && p.ptsUs===0 : Math.abs(p.ptsUs-prevEnd)<=1000 &&
            p.ptsUs>table.samples[i-1].ptsUs) && p.offset>=prevByteEnd, "SAMPLE_ORDER");
        prevEnd=p.ptsUs+p.durationUs; prevByteEnd=p.offset+p.size;
        if (i<=index && p.key) key=i;
    }
    check(key>=0 && index-key+1<=MAX_PACKETS &&
        table.samples[index].ptsUs-table.samples[key].ptsUs<=MAX_PREROLL_US,"SEEK_PREROLL");
    const packets=table.samples.slice(key,index+1);
    check(packets.reduce((n,p)=>n+p.size,0)<=MAX_BYTES,"SEEK_BYTES");
    return {index,key,targetUs:table.samples[index].ptsUs,packets};
}

export async function decodeCouncilFrame({table, nativeFrame, payload, config, api=globalThis,
    timeoutMs=5000}) {
    check(payload instanceof Uint8Array && config &&
        /^avc1\.[0-9a-fA-F]{6}$/.test(config.codec) &&
        integer(config.codedWidth,1,1024) && integer(config.codedHeight,1,768) &&
        config.description instanceof Uint8Array && integer(config.description.byteLength,1,65536) &&
        integer(timeoutMs,1,10000), "DECODER_INPUT");
    const plan=planCouncilSeek(table,nativeFrame,payload.byteLength);
    if (typeof api.VideoDecoder!=="function" || typeof api.EncodedVideoChunk!=="function")
        throw new Error("WEBCODECS_UNAVAILABLE");
    let decoder, timer, selected=null, finished=false, rejectFailure;
    const failure=new Promise((_,reject)=>{rejectFailure=reject;});
    // Install rejection handling before configure/decode, including synchronous errors.
    failure.catch(()=>{});
    try {
        decoder=new api.VideoDecoder({
            output(frame) {
                if (finished || frame.timestamp!==plan.targetUs) { frame.close(); return; }
                if (selected) {
                    frame.close(); rejectFailure(new Error("DUPLICATE_TARGET_FRAME")); return;
                }
                selected=frame;
            },
            error() { rejectFailure(new Error("DECODER_ERROR")); }
        });
        decoder.configure({codec:config.codec,codedWidth:config.codedWidth,
            codedHeight:config.codedHeight,description:config.description,
            optimizeForLatency:true,hardwareAcceleration:"no-preference"});
        for (const p of plan.packets) {
            decoder.decode(new api.EncodedVideoChunk({type:p.key?"key":"delta",
                timestamp:p.ptsUs,duration:p.durationUs,
                data:payload.subarray(p.offset,p.offset+p.size)}));
        }
        const deadline=new Promise((_,reject)=>{
            timer=setTimeout(()=>reject(new Error("DECODE_TIMEOUT")),timeoutMs);
        });
        await Promise.race([failure,deadline,decoder.flush()]);
        // A decoder may have reported an error before a resolved flush.
        check(selected && selected.timestamp===plan.targetUs,"TARGET_FRAME_MISSING");
        const result=selected; selected=null;
        return result; // caller owns exactly one VideoFrame and MUST close it
    } finally {
        finished=true; clearTimeout(timer);
        if (selected) selected.close();
        if (decoder && decoder.state!=="closed") decoder.close();
    }
}
