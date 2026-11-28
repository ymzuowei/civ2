// T025 optional local-only opening. No fetch, file store, saved preferences or sidecar persistence.
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
export function openingOutcome(result,observed,expected){
    if(!Number.isFinite(observed)||!Number.isFinite(expected)||Math.abs(observed-expected)>0.15)return 0;
    return result?.status==='ended'?1:result?.status==='user-skip'?2:0;
}
export async function playNativeOpening({source,volume,lang}){
    const chinese=/^zh/i.test(lang||'');
    const words=chinese?['实验性开场动画','选择本地配对 JSON 和 MP4 文件','播放','跳过','使用原版 AVI','验证失败，选择原版或重试']:
        ['Experimental opening','Select local pairing JSON and MP4','Play','Skip','Use original AVI','Verification failed; retry or use original'];
    let dialog,trial,unsubscribe=()=>{},timer,done=false,finish,observed=null,started=false,finished=false;
    const result=new Promise(r=>{finish=r;});
    const close=(code)=>{if(!done){done=true;finish(code);}};
    const abandon=()=>{trial?.cancel();close(0);};
    try{
        if(!globalThis.crypto?.subtle||!document.createElement('dialog').showModal)return 0;
        dialog=document.createElement('dialog');
        dialog.style.cssText='color:white;background:black;border:0;padding:16px;max-width:95vw;max-height:95vh;text-align:center';
        const make=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;dialog.append(e);return e;};
        make('h2',words[0]);
        const status=make('p',words[1]);
        const meta=make('input'),media=make('input');
        for(const input of [meta,media]){input.type='file';input.style.display='block';input.style.margin='8px auto';}
        meta.accept='.json,application/json';media.accept='.mp4,video/mp4';
        const video=make('video');video.playsInline=true;video.style.cssText='display:block;width:640px;max-width:85vw;height:auto;background:black;margin:auto';
        const play=make('button',words[2]),skip=make('button',words[3]),legacy=make('button',words[4]);
        play.disabled=true;skip.disabled=true;
        let pair=null,revision=0;
        const change=async()=>{
            const rev=++revision;pair=null;play.disabled=true;
            try{
                const m=meta.files[0],v=media.files[0];
                if(!m||!v||m.size>4096||!size(v.size))return;
                const verified=await verifyOpeningPair(source,new Uint8Array(await v.arrayBuffer()),JSON.parse(await m.text()));
                if(!done&&rev===revision){pair=verified;play.disabled=false;status.textContent=words[2];}
            }catch{if(!done&&rev===revision)status.textContent=words[5];}
        };
        meta.onchange=media.onchange=change;
        const gain=()=>{video.volume=Math.max(0,Math.min(1,(volume?.gain??1)*(volume?.effectsGain??1)));};
        gain();unsubscribe=volume?.subscribe(gain)||(()=>{});
        legacy.onclick=abandon;
        dialog.addEventListener('cancel',e=>{e.preventDefault();abandon();});
        video.addEventListener('playing',()=>{observed=video.duration;});
        play.onclick=()=>{
            if(done||started||!pair)return;
            started=true;clearTimeout(timer);meta.disabled=media.disabled=play.disabled=true;skip.disabled=false;
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
        video.onclick=()=>trial?.skipFromUser();
        document.body.append(dialog);dialog.showModal();legacy.focus();
        window.addEventListener('pagehide',abandon,{once:true});
        timer=setTimeout(abandon,180000);
        return await result;
    }catch{return 0;}
    finally{
        clearTimeout(timer);if(!finished)trial?.cancel();unsubscribe();
        window.removeEventListener('pagehide',abandon);dialog?.remove();
    }
}
