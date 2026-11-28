// Explicit loopback-only Council0 WebCodecs shadow owner; legacy DIB stays visible.
import {createCouncilHostBridge} from './council_host_bridge.js';
const shaOK=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,"0")).join("");
export function createCouncilNativeTrial(input,{makeBridge=createCouncilHostBridge,
    digest=x=>crypto.subtle.digest("SHA-256",x),onChange=()=>{}}={}){
    let clip=input,bridge=null,epoch=0,first=null,end=null,previous=null;
    let queued=null,pumping=false;
    input=null;
    const counters={opens:0,closes:0,scheduled:0,dropped:0,frames:0,unchanged:0,failures:0,staleEndHints:0};
    let lastFailure=null;
    function fail(code){counters.failures++;lastFailure=code;changed();}
    const changed=()=>{try{onChange();}catch(_){}};
    function close(){
        epoch++;queued=null;
        if(bridge){bridge.dispose();counters.closes++;}
        bridge=null;first=end=previous=null;
        changed();
    }
    function valid(){
        return clip?.scope==="COUNCIL0"&&clip.shadowOnly===true&&clip.verified===true&&
            shaOK(clip.sourceSha256)&&shaOK(clip.derivedSha256)&&clip.payload instanceof Uint8Array&&
            clip.payload.byteLength>0&&clip.payload.byteLength<=128*1024*1024&&
            Number.isInteger(clip.config?.codedWidth)&&Number.isInteger(clip.config?.codedHeight)&&
            Number.isSafeInteger(clip.table?.nativeStart)&&clip.table.nativeStart>=0&&
            Array.isArray(clip.table.samples)&&clip.table.samples.length>0&&clip.table.samples.length<=36000;
    }
    async function open(source){
        close();const ticket=epoch;
        if(!valid()||!(source instanceof Uint8Array)||source.byteLength===0||source.byteLength>128*1024*1024){
            fail("OPEN_INPUT");return false;
        }
        try{
            const sourceHash=digest(source);source=null;
            if(hex(await sourceHash)!==clip?.sourceSha256||ticket!==epoch){
                if(ticket===epoch)fail("SOURCE_HASH");
                return false;
            }
            if(hex(await digest(clip.payload))!==clip?.derivedSha256||ticket!==epoch){
                if(ticket===epoch)fail("DERIVED_HASH");
                return false;
            }
            const owner=makeBridge();
            if(!owner.open(clip)){owner.dispose();fail("BRIDGE_OPEN");return false;}
            bridge=owner;counters.opens++;changed();return true;
        }catch(_){if(ticket===epoch){fail("OPEN_EXCEPTION");close();}return false;}
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
    function discard(value){
        if(!value||value.ticket!==epoch||value.owner!==bridge)return false;
        if(value.ready.status==="unchanged"){counters.unchanged++;changed();return true;}
        if(!bridge.discard(value.ready)){fail("DISCARD");close();return false;}
        counters.frames++;changed();return true;
    }
    async function pump(){
        if(pumping)return;
        pumping=true;const ticket=epoch;changed();
        try{
            while(queued&&ticket===epoch&&bridge){
                const job=queued;queued=null;
                const value=await prepare(job.frame,job.last,ticket,bridge);
                if(ticket!==epoch||!bridge)break;
                if(!value||!discard(value))break;
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
        if(queued)counters.dropped++;
        queued={frame,last};counters.scheduled++;changed();
        if(!pumping)void pump();
        return true;
    }
    return {
        available:valid,active:()=>!!bridge,
        open,schedule,close,
        stats(){return {...counters,lastFailure,active:bridge?1:0,pumping,queued:queued?1:0,
            sharedClipBytes:clip?.payload.byteLength??0,bridge:bridge?.stats?.()??null};},
        dispose(){close();clip=null;changed();}
    };
}
