// T025 isolated clock-driven range frame provider. Verified no-B AVC only.
// One decoder per range, flush at GOP boundaries (next batch begins with key).
// No actual audio, timer-driven playback, engine callback, or MP4 verification.
import {planCouncilSeek} from "./council_frame_provider.js";
const MAX_FRAMES=16, MAX_RGBA_ESTIMATE=16*1024*1024;
const int=(x,min,max)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
function require(ok,code){if(!ok)throw new Error(code);}

export function createCouncilRange({table,payload,config,first,last,api=globalThis,timeoutMs=5000}){
    require(payload instanceof Uint8Array && config &&
        /^avc1\.[0-9a-fA-F]{6}$/.test(config.codec) &&
        int(config.codedWidth,1,1024)&&int(config.codedHeight,1,768)&&
        config.description instanceof Uint8Array&&int(config.description.length,1,65536)&&
        int(timeoutMs,1,10000),"RANGE_INPUT");
    require(typeof api.VideoDecoder==="function"&&typeof api.EncodedVideoChunk==="function","WEBCODECS_UNAVAILABLE");
    const firstPlan=planCouncilSeek(table,first,payload.length);
    const lastPlan=planCouncilSeek(table,last,payload.length);
    require(firstPlan.index<=lastPlan.index,"RANGE_ORDER");
    // Snapshot bounded metadata, not media bytes. Caller must retain verified
    // immutable payload throughout range; no concurrent mutation permitted.
    const baseIndex=firstPlan.key;
    const samples=table.samples.slice(baseIndex,lastPlan.index+1).map(p=>({...p}));
    const sample=i=>samples[i-baseIndex];
    const offset=table.nativeStart,to=lastPlan.index;
    const width=config.codedWidth,height=config.codedHeight;
    table=null;
    const rgba=config.codedWidth*config.codedHeight*4;
    const gops=[];
    for(let start=firstPlan.key;start<=to;){
        let end=start+1;
        while(end<=to&&!sample(end).key)end++;
        const count=end-start;
        require(count<=MAX_FRAMES&&count*rgba<=MAX_RGBA_ESTIMATE,"GOP_FRAME_BUDGET");
        let bytes=0;
        for(let i=start;i<end;i++)bytes+=sample(i).size;
        require(bytes<=4*1024*1024&&sample(end-1).ptsUs-sample(start).ptsUs<=1000000,"GOP_PACKET_BUDGET");
        gops.push({start,end});start=end;
    }
    let decoder, batch=null, closed=false,busy=false,shown=-1, peakFrames=0, batches=0;
    let failure=null, completed=false;
    const maxEstimatedBatchRGBABytes=Math.max(...gops.map(g=>(g.end-g.start)*rgba));
    function release(){
        const previous=batch;batch=null;
        if(previous){
            for(const frame of previous.frames.values())frame.close();
            previous.frames.clear();previous.seen.clear();previous.timestamps.clear();
            previous.reject=null;
        }
    }
    function stop(code){
        if(closed)return;
        closed=true;
        if(batch?.reject)batch.reject(new Error(code));
        const previous=decoder;decoder=null;
        try{release();}
        finally{
            // An owner may retain the closed API object for diagnostics.
            // Never retain compressed bytes or frame metadata through it.
            payload=null;config=null;samples.length=0;gops.length=0;
            if(previous&&previous.state!=="closed")previous.close();
        }
    }
    try{
        decoder=new api.VideoDecoder({
            output(frame){
                if(closed||!batch){frame.close();return;}
                const i=batch.timestamps.get(frame.timestamp);
                if(i===undefined||batch.seen.has(i)||
                    frame.displayWidth!==width||frame.displayHeight!==height){
                    frame.close();failure="UNEXPECTED_FRAME";stop(failure);return;
                }
                batch.seen.add(i);
                if(i<batch.target){frame.close();return;}
                batch.frames.set(i,frame);
                peakFrames=Math.max(peakFrames,batch.frames.size);
            },
            error(){failure="DECODER_ERROR";stop(failure);}
        });
        decoder.configure({codec:config.codec,codedWidth:config.codedWidth,codedHeight:config.codedHeight,
            description:config.description.slice(),optimizeForLatency:true,hardwareAcceleration:"no-preference"});
        config=null;
    }catch(e){stop("CONFIGURE_FAILED");throw e;}
    async function load(gop,target){
        release();
        let reject;
        const interrupted=new Promise((_,r)=>{reject=r;});interrupted.catch(()=>{});
        const current={...gop,target,frames:new Map(),seen:new Set(),timestamps:new Map(),reject};
        batch=current;
        for(let i=gop.start;i<gop.end;i++)current.timestamps.set(sample(i).ptsUs,i);
        let timer;
        try{
            for(let i=gop.start;i<gop.end;i++){
                require(!closed,"RANGE_CLOSED");
                const p=sample(i);
                decoder.decode(new api.EncodedVideoChunk({type:p.key?"key":"delta",timestamp:p.ptsUs,
                    duration:p.durationUs,data:payload.subarray(p.offset,p.offset+p.size)}));
            }
            const deadline=new Promise((_,r)=>{timer=setTimeout(()=>r(new Error("DECODE_TIMEOUT")),timeoutMs);});
            await Promise.race([interrupted,deadline,decoder.flush()]);
            require(!closed&&batch===current,failure||"RANGE_CLOSED");
            require(current.seen.size===gop.end-gop.start&&current.frames.has(target),"MISSING_FRAME");
            current.reject=null;current.seen.clear();current.timestamps.clear();
            batches++;
        }finally{clearTimeout(timer);}
    }
    return {
        // Caller supplies desired native frame from legacy clock, not wall time.
        // Drawing is synchronous; the callback must not retain the VideoFrame.
        async present(nativeFrame,draw){
            if(completed&&nativeFrame===last)return {status:"unchanged",nativeFrame};
            require(!closed,"RANGE_CLOSED");
            require(!busy,"PRESENT_BUSY");
            require(typeof draw==="function"&&int(nativeFrame,first,last),"PRESENT_INPUT");
            const i=nativeFrame-offset;
            require(i>=shown,"CLOCK_REVERSED");
            if(i===shown)return {status:"unchanged",nativeFrame};
            busy=true;
            try{
                if(!batch||i<batch.start||i>=batch.end){
                    const gop=gops.find(g=>i>=g.start&&i<g.end);
                    require(gop,"GOP_MISSING");await load(gop,i);
                }
                require(!closed&&batch,"RANGE_CLOSED");
                for(const [j,frame] of batch.frames)if(j<i){frame.close();batch.frames.delete(j);}
                const frame=batch.frames.get(i);
                require(frame,"TARGET_MISSING");
                batch.frames.delete(i);
                try{draw(frame);}finally{frame.close();}
                require(!closed,"RANGE_CLOSED");
                shown=i;
                // Last video frame is not the legacy audio-end callback.
                // Release video resources now, without advancing the speech.
                if(i===to){completed=true;stop("RANGE_VIDEO_COMPLETE");}
                return {status:"presented",nativeFrame};
            }catch(e){stop("PRESENT_FAILED");throw e;}finally{busy=false;}
        },
        close(){stop("OWNER_CLOSED");},
        stats(){return {closed,batches,peakRetainedFrames:peakFrames,retainedFrames:batch?.frames.size??0,
            retainedPayloadBytes:payload?.byteLength??0,retainedSampleRows:samples.length,
            activeDecoder:decoder?1:0,completed,maxEstimatedBatchRGBABytes};}
    };
}
