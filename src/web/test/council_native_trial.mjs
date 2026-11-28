import assert from 'node:assert/strict';
import {createCouncilNativeTrial} from '../council_native_trial.js';
const source=new Uint8Array([1,2,3]),payload=new Uint8Array([4,5,6]),sha='0'.repeat(64);
const clip={scope:'COUNCIL0',shadowOnly:true,verified:true,sourceSha256:sha,derivedSha256:sha,
    payload,config:{codedWidth:2,codedHeight:2},
    table:{nativeStart:0,samples:[{}, {}, {}]}};
const settle=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function fixture(input=clip,digest=async()=>new Uint8Array(32).buffer,prepare=null){
    let opens=0,closes=0,starts=0,discards=0;const frames=[];
    const makeBridge=()=>({open(){opens++;return true;},dispose(){closes++;},
        startRange(){starts++;return true;},
        async prepare(frame){frames.push(frame);return prepare?prepare(frame):{status:'ready',bytes:16};},
        discard(){discards++;return true;},stats(){return {closed:false};}});
    const trial=createCouncilNativeTrial(input,{makeBridge,digest});
    return {trial,stats:()=>({opens,closes,starts,discards,frames:[...frames]})};
}
{
    const {trial,stats}=fixture(null);
    assert.equal(trial.available(),false);
    assert.equal(await trial.open(source),false);
    assert.equal(stats().opens,0);
}
{
    const {trial,stats}=fixture({...clip,sourceSha256:'f'.repeat(64)});
    assert.equal(await trial.open(source),false);
    assert.equal(stats().opens,0);
}
{
    const {trial,stats}=fixture();
    assert.equal(await trial.open(source),true);
    assert.equal(trial.schedule(0,2,2,2),true);
    await settle();
    assert.deepEqual(stats().frames,[0]);
    assert.equal(stats().discards,1);
    assert.equal(trial.stats().frames,1);
    assert.equal(trial.schedule(1,2,2,2),true);
    await settle();
    assert.deepEqual(stats().frames,[0,1]);
    assert.equal(stats().starts,1);
    assert.equal(trial.schedule(2,2,3,2),false);
    trial.close();
    assert.equal(stats().closes,1);
    assert.equal(trial.stats().active,0);
    trial.dispose();assert.equal(trial.stats().sharedClipBytes,0);
}
{
    let resolve;
    const {trial,stats}=fixture(clip,async()=>new Uint8Array(32).buffer,
        frame=>frame===0?new Promise(r=>{resolve=r;}):{status:'ready',bytes:16});
    assert.equal(await trial.open(source),true);
    assert.equal(trial.schedule(0,2,2,2),true);
    assert.equal(trial.schedule(1,2,2,2),true);
    assert.equal(trial.schedule(2,2,2,2),true);
    assert.equal(trial.stats().dropped,1);
    resolve({status:'ready',bytes:16});
    await settle();
    assert.deepEqual(stats().frames,[0,2]);
    assert.equal(trial.stats().frames,2);
    trial.dispose();
}
{
    let resolve;
    const {trial}=fixture(clip,async()=>new Uint8Array(32).buffer,
        ()=>new Promise(r=>{resolve=r;}));
    assert.equal(await trial.open(source),true);
    trial.schedule(0,2,2,2);
    trial.close();
    resolve({status:'ready',bytes:16});
    await settle();
    assert.equal(trial.stats().active,0);
    assert.equal(trial.stats().sharedClipBytes,3);
    trial.dispose();
    assert.equal(trial.stats().sharedClipBytes,0);
}
// Native visible seek may precede assignment of the new speech end.
{
    const {trial,stats}=fixture();
    assert.equal(await trial.open(source),true);
    assert.equal(trial.schedule(2,0,2,2),true);
    await settle();
    assert.deepEqual(stats().frames,[2]);
    assert.equal(trial.stats().staleEndHints,1);
    assert.equal(trial.stats().failures,0);
    assert.equal(trial.schedule(1,99,2,2),true);
    await settle();
    assert.deepEqual(stats().frames,[2,1]);
    assert.equal(trial.stats().staleEndHints,2);
    assert.equal(trial.stats().lastFailure,null);
    assert.equal(trial.schedule(3,3,2,2),false);
    assert.equal(trial.stats().lastFailure,'FRAME_BOUNDS');
    trial.close();
    assert.equal(trial.schedule(0,2,2,2),false);
    assert.equal(trial.stats().failures,1);
    trial.dispose();
}
// Visible trial: exact next frame, no stale reuse, single retained slot.
{
    const bytes=new Uint8ClampedArray(16).fill(255);
    const owner={open:()=>true,dispose(){},startRange:()=>true,
        prepare:async()=>({status:'ready',bytes:16}),takePrepared:()=>bytes};
    const trial=createCouncilNativeTrial(clip,{makeBridge:()=>owner,render:true,digest:async()=>new Uint8Array(32).buffer});
    assert.equal(await trial.open(source),true);
    const dst=new Uint8Array(16);
    assert.equal(trial.take(0,dst),false);
    assert.equal(trial.schedule(0,2,2,2),true);
    await settle();
    assert.equal(trial.stats().readyFrame,1);
    assert.equal(trial.stats().readyBytes,16);
    assert.equal(trial.take(2,dst),false);
    assert.equal(trial.take(1,dst),true);
    assert.equal(dst[0],255);
    assert.equal(trial.take(1,dst),false);
    assert.equal(trial.stats().readyBytes,0);
    trial.schedule(1,2,2,2);await settle();
    trial.close();
    assert.equal(trial.stats().readyBytes,0);
    assert.equal(trial.stats().renderHits,1);
    assert.equal(trial.stats().renderMisses,3);
    trial.dispose();
}
console.log('CIV2_T025_COUNCIL_NATIVE_TRIAL_SOURCE=PASS');
