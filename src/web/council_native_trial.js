// Explicit loopback-only Council0 WebCodecs shadow owner; legacy DIB stays visible.
import {createCouncilHostBridge} from './council_host_bridge.js';
const shaOK=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,"0")).join("");
export function createCouncilNativeTrial(input,{makeBridge=createCouncilHostBridge,
    digest=x=>crypto.subtle.digest("SHA-256",x),onChange=()=>{}}={}){
    let clip=input,bridge=null,epoch=0,first=null,end=null,previous=null;
    let queued=null,pumping=false;
    input=null;
    const counters={opens:0,closes:0,scheduled:0,dropped:0,frames:0,unchanged:0,failures:0};
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
            counters.failures++;changed();return false;
        }
        try{
            const sourceHash=digest(source);source=null;
            if(hex(await sourceHash)!==clip?.sourceSha256||ticket!==epoch){
                if(ticket===epoch){counters.failures++;changed();}
                return false;
            }
            if(hex(await digest(clip.payload))!==clip?.derivedSha256||ticket!==epoch){
                if(ticket===epoch){counters.failures++;changed();}
                return false;
            }
            const owner=makeBridge();
            if(!owner.open(clip)){owner.dispose();counters.failures++;changed();return false;}
            bridge=owner;counters.opens++;changed();return true;
        }catch(_){if(ticket===epoch){counters.failures++;close();}return false;}
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
        }catch(_){if(ticket===epoch){counters.failures++;close();}return null;}
    }
    function discard(value){
        if(!value||value.ticket!==epoch||value.owner!==bridge)return false;
        if(value.ready.status==="unchanged"){counters.unchanged++;changed();return true;}
        if(!bridge.discard(value.ready)){counters.failures++;close();return false;}
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
        }catch(_){if(ticket===epoch){counters.failures++;close();}}
        finally{
            pumping=false;changed();
            if(queued&&bridge)void pump();
        }
    }
    function schedule(frame,last,width,height){
        const start=clip?.table?.nativeStart,max=start+clip?.table?.samples?.length-1;
        if(!bridge||!Number.isSafeInteger(frame)||!Number.isSafeInteger(last)||
            frame<start||frame>max||last<frame||last>max||
            width!==clip.config.codedWidth||height!==clip.config.codedHeight){
            counters.failures++;changed();return false;
        }
        if(queued)counters.dropped++;
        queued={frame,last};counters.scheduled++;changed();
        if(!pumping)void pump();
        return true;
    }
    return {
        available:valid,active:()=>!!bridge,
        open,schedule,close,
        stats(){return {...counters,active:bridge?1:0,pumping,queued:queued?1:0,
            sharedClipBytes:clip?.payload.byteLength??0,bridge:bridge?.stats?.()??null};},
        dispose(){close();clip=null;changed();}
    };
}
