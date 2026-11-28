import assert from 'node:assert/strict';
import {createCouncilNativeTrial} from '../council_native_trial.js';
const data=new Uint8Array([1,2,3]), sha='0'.repeat(64);
const clip={scope:'COUNCIL0',shadowOnly:true,verified:true,sourceSha256:sha,derivedSha256:sha,
    payload:data,table:{nativeStart:0,samples:[{}, {}, {}]}};
function fixture(input=clip,digest=async()=>new Uint8Array(32).buffer){
    let opens=0,closes=0,starts=0,commits=0;
    const makeBridge=()=>({open(){opens++;return true;},dispose(){closes++;},
        startRange(){starts++;return true;},async prepare(){return {status:'ready',bytes:4};},
        commit(){commits++;return true;}});
    const trial=createCouncilNativeTrial(input,{makeBridge,digest});
    return {trial,stats:()=>({opens,closes,starts,commits})};
}
{
    const {trial,stats}=fixture(null);
    assert.equal(trial.available(),false);
    assert.equal(await trial.open(data),false);
    assert.equal(stats().opens,0);
}
{
    const {trial,stats}=fixture({...clip,sourceSha256:'f'.repeat(64)});
    assert.equal(await trial.open(data),false);
    assert.equal(stats().opens,0);
}
{
    const {trial,stats}=fixture();
    assert.equal(await trial.open(data),true);
    const t=await trial.prepare(0,2);
    assert.equal(trial.commit(t,null,0,4),true);
    await trial.prepare(1,2);
    assert.equal(stats().starts,1);
    const stale=await trial.prepare(2,2);
    trial.close();
    assert.equal(trial.commit(stale,null,0,4),false);
    assert.equal(stats().closes,1);
    trial.dispose();assert.equal(trial.available(),false);
}
{
    let resolve;
    const {trial,stats}=fixture(clip,()=>new Promise(r=>{resolve=r;}));
    const opening=trial.open(data);trial.dispose();resolve(new Uint8Array(32).buffer);
    assert.equal(await opening,false);assert.equal(stats().opens,0);
}
{
    const {trial,stats}=fixture();
    assert.equal(await trial.open(data),true);
    const t=await trial.prepare(0,2);
    assert.equal(trial.commit(t,null,0,8),false);
    assert.equal(trial.active(),false);
    assert.equal(stats().commits,0);assert.equal(stats().closes,1);
}
console.log('CIV2_T025_COUNCIL_NATIVE_TRIAL_SOURCE=PASS');
