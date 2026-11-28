// Owner-local, one session only. No network, storage or object URLs.
import {planCouncilSeek} from './council_frame_provider.js';
const MAX=128*1024*1024, META=4*1024*1024;
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,'0')).join('');
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
export function chooseCouncilSource(entries){
    const matches=entries.filter(([name])=>/(?:^|\/)video\/council0\.avi$/i.test(name.replace(/\\/g,'/')));
    const bytes=matches.length===1?matches[0][1]?.data:null;
    return bytes instanceof Uint8Array&&bytes.byteLength>0&&bytes.byteLength<=MAX?bytes:null;
}
export async function verifyCouncilShadowPair(source,payload,m,{subtle=globalThis.crypto?.subtle,
    supported=c=>VideoDecoder.isConfigSupported(c)}={}){
    if(!subtle||!(source instanceof Uint8Array)||!(payload instanceof Uint8Array)||
       !source.length||source.length>MAX||!payload.length||payload.length>MAX||
       m?.scope!=='OWNER_LOCAL_COUNCIL0_SHADOW_ONLY'||m.schema!==1||
       m.sourceBytes!==source.length||m.derivedBytes!==payload.length||
       !sha(m.sourceSha256)||!sha(m.derivedSha256))throw Error('PAIR_IDENTITY');
    const c=m.config,t=m.table;
    if(!/^avc1\.[0-9a-fA-F]{6}$/.test(c?.codec)||
       !Number.isInteger(c.codedWidth)||c.codedWidth<1||c.codedWidth>1024||
       !Number.isInteger(c.codedHeight)||c.codedHeight<1||c.codedHeight>768||
       !Array.isArray(c.description)||c.description.length<7||c.description.length>65536||
       c.description.some(x=>!Number.isInteger(x)||x<0||x>255)||
       !Array.isArray(t?.samples)||t.samples.length>36000||!t.samples.length)
        throw Error('PAIR_CONFIG');
    planCouncilSeek(t,t.nativeStart,payload.length);
    planCouncilSeek(t,t.nativeStart+t.samples.length-1,payload.length);
    if(hex(await subtle.digest('SHA-256',source))!==m.sourceSha256||
       hex(await subtle.digest('SHA-256',payload))!==m.derivedSha256)throw Error('PAIR_DIGEST');
    const config={codec:c.codec,codedWidth:c.codedWidth,codedHeight:c.codedHeight,
        description:new Uint8Array(c.description)};
    if(!(await supported(config)).supported)throw Error('DECODER_UNSUPPORTED');
    // No source alpha claim: shadow does not render into game DIB.
    return {scope:'COUNCIL0',shadowOnly:true,verified:true,sourceSha256:m.sourceSha256,
        derivedSha256:m.derivedSha256,payload,table:t,config};
}
export async function chooseLocalCouncilShadow(source){
    if(!source||!globalThis.crypto?.subtle||typeof VideoDecoder!=='function'||
       typeof document.createElement('dialog').showModal!=='function')return null;
    const dialog=document.createElement('dialog');
    const add=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;dialog.append(e);return e;};
    add('h2','Council0 — local shadow test');
    add('p','Select the local JSON and MP4. The original animation remains visible. No files are remembered.');
    const meta=add('input'),media=add('input'),status=add('p',''),go=add('button','Verify and start'),skip=add('button','Use original only');
    for(const e of [meta,media])e.type='file';
    meta.accept='.json,application/json';media.accept='.mp4,video/mp4';
    let done=false,busy=false,resolve;
    const result=new Promise(r=>{resolve=r;});
    const finish=v=>{if(!done){done=true;resolve(v);}};
    const cancel=e=>{e?.preventDefault();finish(null);};
    dialog.addEventListener('cancel',cancel);
    window.addEventListener('pagehide',cancel);
    skip.onclick=()=>finish(null);
    go.onclick=async()=>{
        if(done||busy)return;
        const m=meta.files[0],v=media.files[0];
        if(!m||!v||m.size<1||m.size>META||v.size<1||v.size>MAX){status.textContent='Select a valid pair.';return;}
        busy=true;go.disabled=meta.disabled=media.disabled=true;
        try{
            const manifest=JSON.parse(await m.text());
            if(done)return;
            const payload=new Uint8Array(await v.arrayBuffer());
            if(done)return;
            const clip=await verifyCouncilShadowPair(source,payload,manifest);
            if(!done)finish(clip);
        }catch{if(!done)status.textContent='Verification failed. Retry or use original.';}
        finally{busy=false;if(!done)go.disabled=meta.disabled=media.disabled=false;}
    };
    try{document.body.append(dialog);dialog.showModal();return await result;}
    catch{return null;}
    finally{done=true;source=null;meta.value=media.value='';go.onclick=skip.onclick=null;
        dialog.removeEventListener('cancel',cancel);window.removeEventListener('pagehide',cancel);dialog.remove();}
}
