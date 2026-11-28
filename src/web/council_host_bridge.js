// Browser side of the Native Council0 shadow callback.
// Exact source/derivative identity and decoder support are verified by the local pair loader.
// Shadow-only: legacy visible composition remains authoritative; no alpha/opacity claim.
import {createCouncilRange} from "./council_range_provider.js";

export function createCouncilHostBridge({makeRange=createCouncilRange,makeCanvas=()=>document.createElement("canvas")}={}){
    let clip=null,range=null,canvas=null,context=null,pending=null,prepared=null;
    let generation=0,serial=0,disposed=false;
    const invalidate=()=>{
        generation++;
        prepared=null;
        const old=range;range=null;
        old?.close();
    };
    function releaseClip(){
        invalidate();clip=null;context=null;
        if(canvas){canvas.width=0;canvas.height=0;canvas=null;}
    }
    function rejectToLegacy(){
        releaseClip();
        return null;
    }
    return {
        // Borrow one verified clip for a window, never duplicate its payload.
        // These attestations are gates, not a substitute for media validation.
        open(value){
            if(disposed||pending)return false;
            releaseClip();
            const c=value?.config;
            if(value?.scope!=="COUNCIL0"||value.verified!==true||(value.opaque!==true&&value.shadowOnly!==true)||
                !(value.payload instanceof Uint8Array)||!value.payload.byteLength||
                value.payload.byteLength>128*1024*1024||!value.table||
                !Number.isInteger(c?.codedWidth)||!Number.isInteger(c?.codedHeight)||
                c.codedWidth<1||c.codedWidth>1024||c.codedHeight<1||c.codedHeight>768)return false;
            try{
                canvas=makeCanvas();canvas.width=c.codedWidth;canvas.height=c.codedHeight;
                context=canvas.getContext("2d",{willReadFrequently:true});
                if(!context)throw Error("CANVAS_UNAVAILABLE");
                clip={payload:value.payload,table:value.table,config:c};
                return true;
            }catch(_){releaseClip();return false;}
        },
        startRange(first,last){
            if(disposed||!clip||pending)return false;
            invalidate();
            try{range=makeRange({...clip,first,last});return true;}
            catch(_){rejectToLegacy();return false;}
        },
        async prepare(nativeFrame){
            if(disposed||!range||pending||prepared)return null;
            const owner=range,epoch=generation,token=++serial;
            const job={epoch};pending=job;
            try{
                let image=null;
                const result=await owner.present(nativeFrame,frame=>{
                    if(epoch!==generation||owner!==range||disposed)throw Error("STALE_FRAME");
                    context.drawImage(frame,0,0);
                    image=context.getImageData(0,0,canvas.width,canvas.height);
                });
                if(epoch!==generation||owner!==range||disposed)return null;
                if(result.status==="unchanged")return {status:"unchanged",epoch,token};
                if(!image||image.data.byteLength!==canvas.width*canvas.height*4)return rejectToLegacy();
                prepared={epoch,token,bytes:image.data};
                return {status:"ready",epoch,token,bytes:prepared.bytes.byteLength};
            }catch(_){
                if(epoch===generation&&owner===range)rejectToLegacy();
                return null;
            }finally{if(pending===job)pending=null;}
        },
        // Drop the host-side RGBA readback after the shadow decode; no WASM copy.
        discard(ticket){
            if(!prepared||ticket?.epoch!==generation||ticket?.token!==prepared.token||ticket.status!=="ready")return false;
            prepared=null;
            return true;
        },
        // Transfer ownership of one exact prepared RGBA array to the trial.
        // No WASM view is retained; caller can hold at most one frame.
        takePrepared(ticket){
            if(!prepared||ticket?.epoch!==generation||ticket?.token!==prepared.token||ticket.status!=="ready")return null;
            const bytes=prepared.bytes;prepared=null;return bytes;
        },
        close(){releaseClip();},
        dispose(){disposed=true;releaseClip();},
        stats(){const r=range?.stats?.()??null;return {activeRange:range&&!r?.closed?1:0,pending:pending?1:0,
            preparedBytes:prepared?.bytes.byteLength??0,clipBytes:clip?.payload.byteLength??0,
            canvasPixels:canvas?canvas.width*canvas.height:0,range:r,disposed};}
    };
}
