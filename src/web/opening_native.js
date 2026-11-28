// T025 optional local-only opening. No fetch or game-file writes; one explicit opt-in metadata record.
import {createOpeningTrial} from './opening_trial.js';
const MAX=128*1024*1024;
const sha=/^[a-f0-9]{64}$/;
const size=n=>Number.isSafeInteger(n)&&n>0&&n<=MAX;
export function chooseOpeningSource(entries){
    const matches=entries.filter(([name])=>/(?:^|\/)video\/opening\.avi$/i.test(name.replace(/\\/g,'/')));
    const bytes=matches.length===1?matches[0][1]?.data:null;
    return bytes instanceof Uint8Array&&size(bytes.byteLength)?bytes:null;
}
async function digest(bytes,subtle){
    return Array.from(new Uint8Array(await subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}
export async function verifyOpeningPair(source,derived,manifest,subtle=globalThis.crypto?.subtle){
    if(!subtle||!(source instanceof Uint8Array)||!(derived instanceof Uint8Array)||
       !size(source.byteLength)||!size(derived.byteLength)||!manifest||
       manifest.scope!=='OWNER_LOCAL_OPENING_ONLY'||manifest.schema!==1||
       !sha.test(manifest.source_sha256)||!sha.test(manifest.derived_sha256)||
       manifest.source_bytes!==source.byteLength||manifest.derived_bytes!==derived.byteLength||
       !Number.isFinite(manifest.duration_s)||manifest.duration_s<=0||manifest.duration_s>110)
        throw Error('OPENING_PAIR');
    if(await digest(source,subtle)!==manifest.source_sha256||await digest(derived,subtle)!==manifest.derived_sha256)
        throw Error('OPENING_DIGEST');
    return {blob:new Blob([derived],{type:'video/mp4'}),duration:manifest.duration_s};
}
const CACHE_KEY='t025.opening-local-v1',CACHE_LIMIT=16*1024*1024;
export async function readOpeningCache(store,source,subtle=globalThis.crypto?.subtle){
    try{
        const record=await store.getMeta(CACHE_KEY);
        if(!record)return {state:'MISS'};
        if(record.schema!==1||!(record.bytes instanceof Uint8Array)||record.bytes.byteLength>CACHE_LIMIT)
            return {state:'INVALID'};
        const pair=await verifyOpeningPair(source,record.bytes,record.manifest,subtle);
        return {state:'VERIFIED',pair};
    }catch{return {state:'UNAVAILABLE_OR_INVALID'};}
}
export async function rememberOpening(store,source,bytes,manifest,subtle=globalThis.crypto?.subtle){
    if(!(bytes instanceof Uint8Array)||bytes.byteLength>CACHE_LIMIT)throw Error('OPENING_CACHE_LIMIT');
    const copy=bytes.slice(), meta=structuredClone(manifest);
    await verifyOpeningPair(source,copy,meta,subtle);
    // Atomic one-record replacement; never store original AVI or touch files/HD.
    await store.setMeta(CACHE_KEY,{schema:1,bytes:copy,manifest:meta});
}
export async function forgetOpening(store){await store.removeMeta(CACHE_KEY);}
export function openingOutcome(result,observed,expected){
    if(!Number.isFinite(observed)||!Number.isFinite(expected)||Math.abs(observed-expected)>0.15)return 0;
    return result?.status==='ended'?1:result?.status==='user-skip'?2:0;
}
// Match the native AVI's doubled logical size, not canvas backing pixels (HD density).
export function openingRect(g,w=320,h=120){
    const r=g?.rect;
    if(!r||![r.left,r.top,r.width,r.height,g.width,g.height,w,h].every(Number.isFinite)||
       [r.width,r.height,g.width,g.height,w,h].some(n=>n<=0))return null;
    const scale=Math.min(r.width/g.width,r.height/g.height);
    const width=Math.min(w*2*scale,r.width,r.height*w/h),height=width*h/w;
    return {left:r.left+(r.width-width)/2,top:r.top+(r.height-height)/2,width,height};
}
export async function playNativeOpening({source,volume,lang,geometry,store}){
    const chinese=/^zh/i.test(lang||'');
    const words=chinese?['实验性开场动画','选择本地配对 JSON 和 MP4 文件','播放','跳过','使用原版 AVI','验证失败，选择原版或重试']:
        ['Experimental opening','Select local pairing JSON and MP4','Play','Skip','Use original AVI','Verification failed; retry or use original'];
    const cacheWords=chinese?['已验证本地缓存，可直接播放','记住此开场动画','清除已记住的动画','已保存到本浏览器','缓存操作失败，仍可使用本地文件','选择新的本地文件或使用原版 AVI']:
        ['Verified local cache: ready to play','Remember this opening','Forget remembered opening','Saved in this browser','Cache operation failed; local files remain usable','Select new local files or use original AVI'];
    let dialog,trial,unsubscribe=()=>{},timer,done=false,finish,observed=null,started=false,finished=false,resize=()=>{},observer;
    const result=new Promise(r=>{finish=r;});
    const close=(code)=>{if(!done){done=true;finish(code);}};
    const abandon=()=>{trial?.cancel();close(0);};
    try{
        if(!globalThis.crypto?.subtle||!document.createElement('dialog').showModal)return 0;
        dialog=document.createElement('dialog');
        dialog.style.cssText='color:white;background:black;border:0;padding:16px;max-width:95vw;max-height:95vh;text-align:center';
        const make=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;dialog.append(e);return e;};
        const heading=make('h2',words[0]);
        const status=make('p',words[1]);
        const meta=make('input'),media=make('input');
        for(const input of [meta,media]){input.type='file';input.style.display='block';input.style.margin='8px auto';}
        meta.accept='.json,application/json';media.accept='.mp4,video/mp4';
        const video=make('video');video.playsInline=true;video.style.cssText='display:none;background:black;object-fit:contain';video.setAttribute('aria-label',words[3]);
        const play=make('button',words[2]),skip=make('button',words[3]),legacy=make('button',words[4]);
        const remember=make('button',cacheWords[1]),forget=make('button',cacheWords[2]);
        play.disabled=true;skip.hidden=true;remember.disabled=true;forget.disabled=!store;
        resize=()=>{
            if(!started)return;
            const r=openingRect(geometry?.(),video.videoWidth||320,video.videoHeight||120);
            if(!r)return;
            Object.assign(video.style,{position:'fixed',left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'});
            globalThis.civ2OpeningGeometry={width:r.width,height:r.height,logicalWidth:geometry().width,logicalHeight:geometry().height};
        };
        video.addEventListener('loadedmetadata',resize);
        let pair=null,selected=null,revision=0,busy=false;
        const actions=()=>{play.disabled=busy||!pair;remember.disabled=busy||!store||!selected;forget.disabled=busy||!store;meta.disabled=media.disabled=busy;};
        const change=async()=>{
            const rev=++revision;pair=null;selected=null;actions();
            try{
                const m=meta.files[0],v=media.files[0];
                if(!m||!v||m.size>4096||!size(v.size))return;
                const bytes=new Uint8Array(await v.arrayBuffer()),manifest=JSON.parse(await m.text());
                const verified=await verifyOpeningPair(source,bytes,manifest);
                if(!done&&rev===revision){pair=verified;selected=bytes.length<=CACHE_LIMIT?{bytes,manifest}:null;actions();status.textContent=words[2];}
            }catch{if(!done&&rev===revision)status.textContent=words[5];}
        };
        meta.onchange=media.onchange=change;
        remember.onclick=async()=>{
            if(done||started||busy||!selected||!store)return;
            busy=true;actions();
            try{await rememberOpening(store,source,selected.bytes,selected.manifest);if(!done)status.textContent=cacheWords[3];}
            catch{if(!done)status.textContent=cacheWords[4];}
            finally{busy=false;if(!done&&!started)actions();}
        };
        forget.onclick=async()=>{
            if(done||started||busy||!store)return;
            ++revision;busy=true;actions();
            try{await forgetOpening(store);if(!done){pair=null;selected=null;meta.value=media.value='';status.textContent=cacheWords[5];}}
            catch{if(!done)status.textContent=cacheWords[4];}
            finally{busy=false;if(!done&&!started)actions();}
        };
        const gain=()=>{video.volume=Math.max(0,Math.min(1,(volume?.gain??1)*(volume?.effectsGain??1)));};
        gain();unsubscribe=volume?.subscribe(gain)||(()=>{});
        legacy.onclick=abandon;
        dialog.addEventListener('cancel',e=>{e.preventDefault();if(started)trial?.skipFromUser();else abandon();});
        dialog.addEventListener('click',e=>{if(started&&(e.target===dialog||e.target===video))trial?.skipFromUser();});
        video.addEventListener('playing',()=>{observed=video.duration;});
        play.onclick=()=>{
            if(done||started||busy||!pair)return;
            started=true;clearTimeout(timer);
            for(const e of [heading,status,meta,media,play,skip,legacy,remember,forget])e.hidden=true;
            dialog.style.cssText='position:fixed;inset:0;margin:0;padding:0;border:0;width:100vw;height:100vh;max-width:none;max-height:none;background:black;overflow:hidden';
            video.style.display='block';resize();
            dialog.focus();
            try{
                trial=createOpeningTrial({video,blob:pair.blob});
                trial.startFromGesture().then(r=>{
                    finished=true;
                    const code=openingOutcome(r,observed,pair.duration);
                    globalThis.civ2OpeningNative={scope:'EXPERIMENTAL_GAME_OPENING',status:r.status,reason:r.reason,code};
                    close(code);
                },abandon);
            }catch{abandon();}
        };
        skip.onclick=()=>trial?.skipFromUser();
        window.addEventListener('resize',resize);
        window.addEventListener('civ2-display-change',resize);
        document.addEventListener('fullscreenchange',resize);
        const canvas=document.getElementById('screen');
        if(canvas&&globalThis.ResizeObserver){observer=new ResizeObserver(resize);observer.observe(canvas);}
        document.body.append(dialog);dialog.showModal();legacy.focus();
        window.addEventListener('pagehide',abandon,{once:true});
        timer=setTimeout(abandon,180000);
        if(store){
            const rev=revision;
            readOpeningCache(store,source).then(c=>{
                if(done||started||busy||rev!==revision)return;
                if(c.state==='VERIFIED'){pair=c.pair;selected=null;status.textContent=cacheWords[0];actions();}
                globalThis.civ2OpeningCache={scope:'LOCAL_OPENING_ONLY',state:c.state};
            });
        }
        return await result;
    }catch{return 0;}
    finally{
        clearTimeout(timer);if(!finished)trial?.cancel();unsubscribe();
        window.removeEventListener('pagehide',abandon);
        window.removeEventListener('resize',resize);window.removeEventListener('civ2-display-change',resize);
        document.removeEventListener('fullscreenchange',resize);observer?.disconnect();dialog?.remove();
    }
}
