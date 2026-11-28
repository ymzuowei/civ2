// Experimental host owner; legacy rendering remains authoritative.
// Explicit loopback main.js opt-in only. No fetch or persistence.
import {createCouncilHostBridge} from './council_host_bridge.js';
const shaOK=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,"0")).join("");
export function createCouncilNativeTrial(input,{makeBridge=createCouncilHostBridge,digest=x=>crypto.subtle.digest("SHA-256",x)}={}){
    let clip=input,bridge=null,epoch=0,first=null,end=null,previous=null;
    input=null;
    const counters={opens:0,closes:0,frames:0,unchanged:0,failures:0};
    function close(){
        epoch++;if(bridge){bridge.dispose();counters.closes++;}bridge=null;first=end=previous=null;
    }
    function valid(){
        return clip?.scope==="COUNCIL0"&&clip.shadowOnly===true&&clip.verified===true&&
            shaOK(clip.sourceSha256)&&shaOK(clip.derivedSha256)&&clip.payload instanceof Uint8Array&&
            clip.payload.byteLength>0&&clip.payload.byteLength<=128*1024*1024;
    }
    return {
        available:valid,active:()=>!!bridge,
        async open(source){
            close();const ticket=epoch;
            if(!valid()||!(source instanceof Uint8Array)||source.byteLength===0||source.byteLength>128*1024*1024)return false;
            try{
                const sourceHash=digest(source);source=null;
                if(hex(await sourceHash)!==clip?.sourceSha256||ticket!==epoch)return false;
                if(hex(await digest(clip.payload))!==clip?.derivedSha256||ticket!==epoch)return false;
                const owner=makeBridge();
                if(!owner.open(clip)){owner.dispose();return false;}
                bridge=owner;counters.opens++;return true;
            }catch(_){if(ticket===epoch)close();return false;}
        },
        async prepare(frame,last){
            const owner=bridge, ticket=epoch;
            if(!owner)return null;
            try{
                const start=clip.table.nativeStart, max=start+clip.table.samples.length-1;
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
        },
        commit(value,memory,ptr,capacity){
            if(!value||value.ticket!==epoch||value.owner!==bridge)return false;
            if(value.ready.status==="unchanged"){counters.unchanged++;return true;}
            if(value.ready.bytes!==capacity){close();return false;}
            const ok=bridge.commit(value.ready,memory,ptr,capacity);
            if(!ok){counters.failures++;close();}else counters.frames++;
            return ok;
        },
        stats(){return {...counters,active:bridge?1:0,sharedClipBytes:clip?.payload.byteLength??0,
            bridge:bridge?.stats?.()??null};},
        close,
        dispose(){close();clip=null;}
    };
}
