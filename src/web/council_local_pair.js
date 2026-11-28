// Owner-local, one session only. No network, storage or object URLs.
import {planCouncilSeek} from './council_frame_provider.js';
import {verifyOpeningPair} from './opening_native.js';
const MAX=128*1024*1024, META=4*1024*1024;
const hex=x=>Array.from(new Uint8Array(x),b=>b.toString(16).padStart(2,'0')).join('');
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const validEra=era=>Number.isInteger(era)&&era>=0&&era<=2;
export function chooseCouncilSource(entries,era=0){
    if(!validEra(era))return null;
    const expected='council'+era+'.avi';
    const matches=entries.filter(([name])=>name.replace(/\\/g,'/').split('/').pop().toLowerCase()===expected);
    const bytes=matches.length===1?matches[0][1]?.data:null;
    return bytes instanceof Uint8Array&&bytes.byteLength>0&&bytes.byteLength<=MAX?bytes:null;
}
export async function verifyCouncilShadowPair(source,payload,m,{subtle=globalThis.crypto?.subtle,
    supported=c=>VideoDecoder.isConfigSupported(c),era=0}={}){
    if(!subtle||!(source instanceof Uint8Array)||!source.length||source.length>MAX||
       m?.sourceBytes!==source.length)throw Error('PAIR_IDENTITY');
    const sourceHash=hex(await subtle.digest('SHA-256',source));
    return verifyCouncilPayload(sourceHash,payload,m,{subtle,supported,era});
}
const extraId=id=>typeof id==='string'&&/^(?:WONDER(?:0[0-9]|1[0-9]|2[0-7])|ANARCHY[012]|LAUNCH|WINWIN)$/.test(id);
async function verifyCouncilPayload(sourceHash,payload,m,{subtle,supported,era,id='COUNCIL'+era}){
    if(!subtle||!(payload instanceof Uint8Array)||!payload.length||payload.length>MAX||
       (!(validEra(era)&&id==='COUNCIL'+era)&&!(extraId(id)&&m?.opacityProof==='IV41_PACKET_HEADER_OPAQUE_V1'))||
       m?.scope!==('OWNER_LOCAL_'+id+'_SHADOW_ONLY')||m.schema!==1||
       !Number.isSafeInteger(m.sourceBytes)||m.sourceBytes<1||m.sourceBytes>MAX||
       m.derivedBytes!==payload.length||!sha(m.sourceSha256)||!sha(m.derivedSha256))throw Error('PAIR_IDENTITY');
    if(sourceHash!==m.sourceSha256)throw Error('PAIR_DIGEST');
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
    if(hex(await subtle.digest('SHA-256',payload))!==m.derivedSha256)throw Error('PAIR_DIGEST');
    const config={codec:c.codec,codedWidth:c.codedWidth,codedHeight:c.codedHeight,
        description:new Uint8Array(c.description)};
    if(!(await supported(config)).supported)throw Error('DECODER_UNSUPPORTED');
    // No source alpha claim: shadow does not render into game DIB.
    return {scope:id,shadowOnly:true,verified:true,sourceSha256:m.sourceSha256,
        derivedSha256:m.derivedSha256,payload,table:t,config};
}
export async function chooseLocalCouncilShadow(source,lang='en',era=0,render=false){
    const zh=/^zh/i.test(lang||'');
    if(!validEra(era)||!source||!globalThis.crypto?.subtle||typeof VideoDecoder!=='function'||
       typeof document.createElement('dialog').showModal!=='function')return null;
    const dialog=document.createElement('dialog');
    const add=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;dialog.append(e);return e;};
    add('h2',(zh?'议会顾问动画 — 本地测试':'Council — local trial')+' (COUNCIL'+era+')');
    add('p',zh?(render?'选择对应时代的 JSON 和 MP4。精确帧命中时使用新画面，其他情况回退原版；不保存文件。':'选择对应时代的 JSON 和 MP4。原版画面保持不变；不保存文件。'):(render?'Choose the matching era JSON and MP4. Exact frames may replace legacy drawing; misses fall back. Files are not saved.':'Choose the matching era JSON and MP4. Original drawing stays visible; files are not saved.'));
    const meta=document.createElement('input'),media=document.createElement('input');
    for(const e of [meta,media])e.type='file';
    const metaLabel=add('label',zh?'配对清单 JSON':'Pair manifest JSON');
    const mediaLabel=add('label',zh?'转码 MP4':'Transcoded MP4');
    for(const label of [metaLabel,mediaLabel]){label.style.display='block';label.style.margin='10px 0';}
    for(const input of [meta,media]){input.style.display='block';input.style.margin='6px 0';}
    metaLabel.append(meta);mediaLabel.append(media);
    const status=add('p',''),go=add('button',zh?'验证并开始':'Verify and start'),skip=add('button',zh?'仅使用原版动画':'Use original only');
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
        if(!m||!v||m.size<1||m.size>META||v.size<1||v.size>MAX){status.textContent=zh?'请选择有效的 JSON 和 MP4 文件。':'Select a valid JSON and MP4 pair.';return;}
        busy=true;go.disabled=meta.disabled=media.disabled=true;
        try{
            const manifest=JSON.parse(await m.text());
            if(done)return;
            const payload=new Uint8Array(await v.arrayBuffer());
            if(done)return;
            const clip=await verifyCouncilShadowPair(source,payload,manifest,{era});
            if(!done)finish(clip);
        }catch{if(!done)status.textContent=zh?'验证失败。请重试，或使用原版动画。':'Verification failed. Retry or use the original animation.';}
        finally{busy=false;if(!done)go.disabled=meta.disabled=media.disabled=false;}
    };
    try{document.body.append(dialog);dialog.showModal();return await result;}
    catch{return null;}
    finally{done=true;source=null;meta.value=media.value='';go.onclick=skip.onclick=null;
        dialog.removeEventListener('cancel',cancel);window.removeEventListener('pagehide',cancel);dialog.remove();}
}

// One local file, two independent verified streams. Never read the whole
// package into an ArrayBuffer; each bounded payload is read exactly once.
export async function readLocalMediaPack(file,openingSource,councilSource,era,
    {subtle=globalThis.crypto?.subtle,supported=c=>VideoDecoder.isConfigSupported(c)}={}){
    if(!validEra(era)||!file||file.size<13||file.size>12+META+2*MAX)throw Error('PACK_SIZE');
    const prefix=new Uint8Array(await file.slice(0,12).arrayBuffer());
    if(new TextDecoder().decode(prefix.subarray(0,8))!=='CIV2M01\n')throw Error('PACK_MAGIC');
    const len=new DataView(prefix.buffer).getUint32(8,true);
    if(len<1||len>META||12+len>=file.size)throw Error('PACK_HEADER');
    const m=JSON.parse(await file.slice(12,12+len).text());
    const o=m?.opening,c=m?.council,os=o?.derived_bytes,cs=c?.derivedBytes;
    if(m?.schema!==1||!Number.isSafeInteger(os)||os<1||os>MAX||
       !Number.isSafeInteger(cs)||cs<1||cs>MAX||12+len+os+cs!==file.size)
        throw Error('PACK_LAYOUT');
    const start=12+len;
    const opening=await verifyOpeningPair(openingSource,new Uint8Array(await file.slice(start,start+os).arrayBuffer()),o,subtle);
    const council=await verifyCouncilShadowPair(councilSource,new Uint8Array(await file.slice(start+os).arrayBuffer()),c,{era,subtle,supported});
    return {opening,council};
}
// V2: retain only a File handle and bounded manifests; load one verified Council
// payload on demand by the hash of the original AVI just opened by native.
export async function readLazyMediaPack(file,openingSource,{subtle=globalThis.crypto?.subtle,
    supported=c=>VideoDecoder.isConfigSupported(c),extended=false}={}){
    const limit=(extended?8:4)*META;
    if(!subtle||!file||file.size<13||file.size>12+limit+(extended?1024*1024*1024:4*MAX))throw Error('PACK_SIZE');
    const prefix=new Uint8Array(await file.slice(0,12).arrayBuffer());
    if(new TextDecoder().decode(prefix.subarray(0,8))!==(extended?'CIV2M03\n':'CIV2M02\n'))throw Error('PACK_MAGIC');
    const len=new DataView(prefix.buffer).getUint32(8,true);
    if(len<1||len>limit||12+len>=file.size)throw Error('PACK_HEADER');
    const m=JSON.parse(await file.slice(12,12+len).text());
    if(m?.schema!==(extended?3:2)||!Array.isArray(m.councils)||m.councils.length!==3)throw Error('PACK_LAYOUT');
    const os=m.opening?.derived_bytes;
    if(!Number.isSafeInteger(os)||os<1||os>MAX)throw Error('PACK_LAYOUT');
    let offset=12+len+os;
    const directory=new Map();
    for(let era=0;era<3;era++){
        const meta=m.councils[era],n=meta?.derivedBytes;
        if(meta?.schema!==1||meta.scope!=='OWNER_LOCAL_COUNCIL'+era+'_SHADOW_ONLY'||
           !Number.isSafeInteger(n)||n<1||n>MAX||!sha(meta.sourceSha256)||!sha(meta.derivedSha256)||
           !Number.isSafeInteger(meta.sourceBytes)||meta.sourceBytes<1||meta.sourceBytes>MAX||
           directory.has(meta.sourceSha256))throw Error('PACK_LAYOUT');
        directory.set(meta.sourceSha256,{meta,era,id:'COUNCIL'+era,offset,n});offset+=n;
    }
    if(extended){
        if(!Array.isArray(m.extras)||m.extras.length>33)throw Error('PACK_LAYOUT');
        const ids=new Set();
        for(const meta of m.extras){
            const id=meta?.clipId,n=meta?.derivedBytes;
            if(!extraId(id)||ids.has(id)||meta.schema!==1||meta.scope!=='OWNER_LOCAL_'+id+'_SHADOW_ONLY'||
               meta.opacityProof!=='IV41_PACKET_HEADER_OPAQUE_V1'||!Number.isSafeInteger(n)||n<1||n>MAX||
               !sha(meta.sourceSha256)||!sha(meta.derivedSha256)||!Number.isSafeInteger(meta.sourceBytes)||
               meta.sourceBytes<1||meta.sourceBytes>MAX||directory.has(meta.sourceSha256))throw Error('PACK_LAYOUT');
            ids.add(id);directory.set(meta.sourceSha256,{meta,id,era:null,offset,n});offset+=n;
        }
    }
    if(offset!==file.size)throw Error('PACK_LAYOUT');
    const opening=await verifyOpeningPair(openingSource,new Uint8Array(await file.slice(12+len,12+len+os).arrayBuffer()),m.opening,subtle);
    const council={lazy:true,async load(hash,size){
        const row=directory.get(hash);
        if(!row||row.meta.sourceBytes!==size)return null;
        const bytes=new Uint8Array(await file.slice(row.offset,row.offset+row.n).arrayBuffer());
        return verifyCouncilPayload(hash,bytes,row.meta,{era:row.era,id:row.id,subtle,supported});
    },dispose(){file=null;directory.clear();}};
    return {opening,council};
}

export async function chooseLocalMediaPack(openingSource,councilSource,lang,era,auto=false,extended=false){
    if(!openingSource||(!auto&&!councilSource)||!globalThis.crypto?.subtle||
       typeof VideoDecoder!=='function'||typeof document.createElement('dialog').showModal!=='function')return null;
    const zh=/^zh/i.test(lang||'');
    const dialog=document.createElement('dialog');
    const add=(tag,words)=>{const e=document.createElement(tag);if(words)e.textContent=words;dialog.append(e);return e;};
    add('h2',zh?'游戏动画素材包':'Game animation pack');
    add('p',zh?(auto?(extended?'选择包含开场、议会及其他已验证动画的素材包。游戏按需加载，不上传或保存。':'选择包含开场和三个时代议会的素材包。游戏自动选择时代，不上传或保存。'):'一次选择开场及 COUNCIL'+era+' 议会动画素材包（.civ2media）。文件仅在本次游戏使用，不上传或保存。'):
        (auto?(extended?'Select the verified extended animation pack. Local on-demand playback only.':'Select an opening and three-era Council pack. Era selected automatically; no upload or storage.'):'Select one .civ2media pack containing opening and COUNCIL'+era+'. Local session only; no upload or storage.'));
    const file=add('input');file.type='file';file.accept='.civ2media';file.style.display='block';file.style.margin='12px 0';
    const status=add('p',''),go=add('button',zh?'验证并开始':'Verify and start'),skip=add('button',zh?'使用原版动画':'Use original animations');
    let done=false,busy=false,resolve;
    const result=new Promise(r=>{resolve=r;});
    const finish=v=>{if(!done){done=true;resolve(v);}};
    const cancel=e=>{e?.preventDefault();finish(null);};
    dialog.addEventListener('cancel',cancel);window.addEventListener('pagehide',cancel);
    skip.onclick=()=>finish(null);
    go.onclick=async()=>{
        if(done||busy)return;
        const selected=file.files[0];
        if(!selected){status.textContent=zh?'请选择素材包。':'Select a pack.';return;}
        busy=true;go.disabled=file.disabled=true;
        try{
            const pair=auto?await readLazyMediaPack(selected,openingSource,{extended}):await readLocalMediaPack(selected,openingSource,councilSource,era);
            if(!done)finish(pair);else pair.council?.dispose?.();
        }catch{if(!done)status.textContent=zh?'素材包不匹配或验证失败。请选择对应时代的完整素材包，或使用原版动画。':'Pack mismatch or verification failed. Choose the matching era pack or use originals.';}
        finally{busy=false;if(!done)go.disabled=file.disabled=false;}
    };
    try{document.body.append(dialog);dialog.showModal();return await result;}
    catch{return null;}
    finally{done=true;openingSource=councilSource=null;file.value='';go.onclick=skip.onclick=null;
        dialog.removeEventListener('cancel',cancel);window.removeEventListener('pagehide',cancel);dialog.remove();}
}
