// T025 source-only native-video lifecycle prototype; not wired to game.
// Caller supplies a verified owner-local sidecar Blob and an isolated video.
// No fetch, persistence, engine mutations, autoplay or fallback media loading.
export function createOpeningTrial({video,blob,urls=globalThis.URL,clock=globalThis,
    startupMs=8000,stallMs=8000,limitMs=120000}){
    if(!video||!(blob instanceof Blob)||blob.type!=='video/mp4'||!blob.size||blob.size>128*1024*1024||
       ![startupMs,stallMs,limitMs].every(n=>Number.isFinite(n)&&n>0&&n<=180000))
        throw new Error('INVALID_TRIAL');
    let resolve,done=false,started=false,playing=false,url=null,initial=null,stall=null,limit=null,lastTime=0;
    const result=new Promise(r=>{resolve=r;});
    const listeners=[];
    const clear=id=>{if(id!==null)clock.clearTimeout(id);};
    const arm=(ms,reason)=>clock.setTimeout(()=>finish('fallback',reason),ms);
    function listen(name,fn){video.addEventListener(name,fn);listeners.push([name,fn]);}
    function finish(status,reason){
        if(done)return;
        done=true;
        clear(initial);clear(stall);clear(limit);
        for(const [name,fn] of listeners)video.removeEventListener(name,fn);
        try{video.pause();}catch{}
        try{video.removeAttribute('src');video.load();}catch{}
        if(url!==null){try{urls.revokeObjectURL(url);}catch{}url=null;}
        resolve({status,reason,maySkipLegacy:status==='ended'||status==='user-skip'});
    }
    function progress(){
        if(!playing||done)return;
        const t=video.currentTime;
        if(Number.isFinite(t)&&t>lastTime){
            lastTime=t;clear(stall);stall=arm(stallMs,'NO_PROGRESS');
        }
    }
    function startFromGesture(){
        if(done||started)return result;
        started=true;
        try{
            listen('error',()=>finish('fallback','MEDIA_ERROR'));
            listen('playing',()=>{
                if(done||playing)return;
                playing=true;clear(initial);stall=arm(stallMs,'NO_PROGRESS');
            });
            listen('timeupdate',progress);
            listen('ended',()=>{
                // An ended event without real playback is not success.
                if(!playing||!Number.isFinite(video.duration)||video.duration<=0||
                   video.currentTime<video.duration-0.15)
                    finish('fallback','PREMATURE_END');
                else finish('ended','COMPLETE');
            });
            url=urls.createObjectURL(blob);
            video.preload='auto';video.loop=false;video.src=url;
            initial=arm(startupMs,'START_TIMEOUT');limit=arm(limitMs,'TOTAL_TIMEOUT');
            // No await before play: preserve real click activation.
            Promise.resolve(video.play()).catch(()=>finish('fallback','PLAY_REJECTED'));
        }catch{finish('fallback','START_ERROR');}
        return result;
    }
    function skipFromUser(){
        if(started&&playing&&!done)finish('user-skip','EXPLICIT_SKIP');
        return result;
    }
    function cancel(){finish('fallback','CANCELLED');return result;}
    return {startFromGesture,skipFromUser,cancel,result};
}
