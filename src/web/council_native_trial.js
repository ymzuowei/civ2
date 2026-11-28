// Explicit loopback-only Council0 WebCodecs shadow owner; legacy DIB stays visible.
import {createCouncilHostBridge} from './council_host_bridge.js';
const shaOK=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,"0")).join("");
export function createCouncilNativeTrial(input,{makeBridge=createCouncilHostBridge,
    digest=x=>crypto.subtle.digest("SHA-256",x),onChange=()=>{},render=false}={}){
    let provider=input?.lazy===true&&typeof input.load==='function'?input:null;
    let clip=provider?null:input,bridge=null,epoch=0,first=null,end=null,previous=null;
    let loading=false,lastEra=null;
    const lazy=!!provider;
    let queued=null,pumping=false,slot=null;
    input=null;
    const counters={opens:0,closes:0,scheduled:0,dropped:0,frames:0,unchanged:0,failures:0,staleEndHints:0,cancelled:0,renderHits:0,renderMisses:0,renderRejected:0,lazyLoads:0,lazyFallbacks:0};
    let lastFailure=null;
    function fail(code){counters.failures++;lastFailure=code;changed();}
    const changed=()=>{try{onChange();}catch(_){}};
    function close(){
        epoch++;if(queued)counters.cancelled++;queued=null;slot=null;
        if(bridge){bridge.dispose();counters.closes++;}
        bridge=null;first=end=previous=null;
        if(lazy)clip=null;
        changed();
    }
    function valid(){
        return /^COUNCIL[012]$/.test(clip?.scope||"")&&clip.shadowOnly===true&&clip.verified===true&&
            shaOK(clip.sourceSha256)&&shaOK(clip.derivedSha256)&&clip.payload instanceof Uint8Array&&
            clip.payload.byteLength>0&&clip.payload.byteLength<=128*1024*1024&&
            Number.isInteger(clip.config?.codedWidth)&&Number.isInteger(clip.config?.codedHeight)&&
            Number.isSafeInteger(clip.table?.nativeStart)&&clip.table.nativeStart>=0&&
            Array.isArray(clip.table.samples)&&clip.table.samples.length>0&&clip.table.samples.length<=36000;
    }
    async function open(source){
        close();const ticket=epoch;
        if(lazy&&(loading||pumping||!provider)){counters.lazyFallbacks++;changed();return false;}
        if((!lazy&&!valid())||!(source instanceof Uint8Array)||source.byteLength===0||source.byteLength>128*1024*1024){
            fail("OPEN_INPUT");return false;
        }
        try{
            const size=source.byteLength;
            if(lazy){loading=true;changed();}
            const sourceHash=digest(source);source=null;
            const hash=hex(await sourceHash);
            if(ticket!==epoch)return false;
            if(lazy){
                const loaded=await provider.load(hash,size);
                if(ticket!==epoch)return false;
                if(!loaded){counters.lazyFallbacks++;changed();return false;}
                clip=loaded;
                if(!valid()||clip.sourceSha256!==hash){fail("OPEN_INPUT");close();return false;}
                counters.lazyLoads++;
            }else{
                if(hash!==clip?.sourceSha256){fail("SOURCE_HASH");return false;}
                if(hex(await digest(clip.payload))!==clip?.derivedSha256||ticket!==epoch){
                    if(ticket===epoch)fail("DERIVED_HASH");
                    return false;
                }
            }
            const owner=makeBridge();
            if(!owner.open(clip)){owner.dispose();fail("BRIDGE_OPEN");close();return false;}
            bridge=owner;lastEra=clip.scope;counters.opens++;changed();return true;
        }catch(_){if(ticket===epoch){fail("OPEN_EXCEPTION");close();}return false;}
        finally{if(lazy){loading=false;changed();}}
    }
    async function prepare(frame,last,ticket,owner){
        try{
            const start=clip.table.nativeStart,max=start+clip.table.samples.length-1;
            if(!Number.isSafeInteger(frame)||frame<start||frame>max)throw Error("FRAME_BOUNDS");
            const limit=Number.isSafeInteger(last)&&last>=frame&&last<=max?last:frame;
            if(first===null||end!==limit||frame<previous){
                if(!owner.startRange(frame,limit))throw Error("RANGE_START");
                first=frame;end=limit;
            }
            const ready=await owner.prepare(frame);
            if(ticket!==epoch||owner!==bridge)return null;
            if(!ready)throw Error("FRAME_PREPARE");
            previous=frame;return {owner,ticket,ready};
        }catch(e){if(ticket===epoch){fail(["FRAME_BOUNDS","RANGE_START","FRAME_PREPARE"].includes(e?.message)?e.message:"PREPARE_EXCEPTION");close();}return null;}
    }
    function discard(value,job){
        if(!value||value.ticket!==epoch||value.owner!==bridge)return false;
        if(value.ready.status==="unchanged"){counters.unchanged++;changed();return true;}
        if(render){
            const bytes=bridge.takePrepared(value.ready);
            if(!(bytes instanceof Uint8ClampedArray)||bytes.byteLength!==clip.config.codedWidth*clip.config.codedHeight*4){
                fail("RENDER_READBACK");close();return false;
            }
            slot={frame:job.frame,bytes};
        }else if(!bridge.discard(value.ready)){fail("DISCARD");close();return false;}
        counters.frames++;changed();return true;
    }
    async function pump(){
        if(pumping)return;
        pumping=true;const ticket=epoch;changed();
        try{
            while(queued&&ticket===epoch&&bridge){
                const job=queued;queued=null;
                const value=await prepare(job.frame,job.last,ticket,bridge);
                if(ticket!==epoch||!bridge){counters.cancelled++;break;}
                if(!value||!discard(value,job))break;
            }
        }catch(_){if(ticket===epoch){fail("PUMP_EXCEPTION");close();}}
        finally{
            pumping=false;changed();
            if(queued&&bridge)void pump();
        }
    }
    function schedule(frame,last,width,height){
        const start=clip?.table?.nativeStart,max=start+clip?.table?.samples?.length-1;
        // Legacy show_frame/seek can run before play_range sets its new end.
        // A successful visible frame is authoritative; the old end is a hint.
        // Do not reject a valid frame or expand past verified media bounds.
        if(!bridge)return false;
        if(!Number.isSafeInteger(frame)||frame<start||frame>max){
            fail("FRAME_BOUNDS");return false;
        }
        if(width!==clip.config.codedWidth||height!==clip.config.codedHeight){
            fail("FRAME_GEOMETRY");return false;
        }
        if(!Number.isSafeInteger(last)||last<frame||last>max){
            last=frame;counters.staleEndHints++;
        }
        if(render){
            // Look one frame ahead. A seek or late native tick can miss;
            // never display an older or future frame in its place.
            frame=frame<last?frame+1:frame;
            if(slot&&slot.frame!==frame)slot=null;
        }
        if(queued)counters.dropped++;
        queued={frame,last};counters.scheduled++;changed();
        if(!pumping)void pump();
        return true;
    }
    function take(frame,width,height,destination){
        if(!render||!bridge)return false;
        if(!slot||slot.frame!==frame){counters.renderMisses++;changed();return false;}
        const bytes=slot.bytes;slot=null;
        if(width!==clip.config.codedWidth||height!==clip.config.codedHeight||
            !(destination instanceof Uint8Array)||destination.byteLength!==bytes.byteLength){
            counters.renderRejected++;changed();return false;
        }
        // All alpha must be opaque; native additionally checks original Indeo mask.
        for(let i=3;i<bytes.length;i+=4)if(bytes[i]!==255){counters.renderRejected++;changed();return false;}
        destination.set(bytes);counters.renderHits++;changed();return true;
    }
    return {
        available:()=>lazy?!!provider:valid(),active:()=>!!bridge,
        open,schedule,take,close,
        stats(){return {...counters,lastFailure,active:bridge?1:0,pumping,queued:queued?1:0,
            render,era:clip?.scope??lastEra,lazy,loading,readyFrame:slot?.frame??null,readyBytes:slot?.bytes.byteLength??0,
            sharedClipBytes:clip?.payload.byteLength??0,bridge:bridge?.stats?.()??null};},
        dispose(){close();clip=null;provider?.dispose?.();provider=null;changed();}
    };
}
