import assert from 'node:assert/strict';
import {chooseCouncilSource,verifyCouncilShadowPair} from '../council_local_pair.js';
const source=new Uint8Array([1,2]),payload=new Uint8Array([3,4]),sha='0'.repeat(64);
const manifest={scope:'OWNER_LOCAL_COUNCIL0_SHADOW_ONLY',schema:1,sourceBytes:2,derivedBytes:2,
    sourceSha256:sha,derivedSha256:sha,table:{nativeStart:0,samples:[{ptsUs:0,durationUs:66667,offset:0,size:2,key:true}]},
    config:{codec:'avc1.42001e',codedWidth:2,codedHeight:2,description:[1,66,0,30,255,225,0]}};
const options={subtle:{digest:async()=>new Uint8Array(32).buffer},supported:async()=>({supported:true})};
assert.equal(chooseCouncilSource([['VIDEO/COUNCIL0.AVI',{data:source}]]),source);
assert.equal(chooseCouncilSource([['COUNCIL0.AVI',{data:source}]]),source);
assert.equal(chooseCouncilSource([['VIDEO/COUNCIL0.AVI',{data:source}],['video/council0.avi',{data:source}]]),null);
const clip=await verifyCouncilShadowPair(source,payload,manifest,options);
assert.equal(clip.shadowOnly,true);assert.equal(clip.opaque,undefined);assert.equal(clip.payload,payload);
await assert.rejects(verifyCouncilShadowPair(source,payload,{...manifest,sourceBytes:1},options),/PAIR_IDENTITY/);
await assert.rejects(verifyCouncilShadowPair(source,payload,{...manifest,derivedSha256:'f'.repeat(64)},options),/PAIR_DIGEST/);
await assert.rejects(verifyCouncilShadowPair(source,payload,manifest,{...options,supported:async()=>({supported:false})}),/DECODER_UNSUPPORTED/);
for(const era of [1,2]){
    const matching={...manifest,scope:'OWNER_LOCAL_COUNCIL'+era+'_SHADOW_ONLY'};
    assert.equal(chooseCouncilSource([['video/council0.avi',{data:payload}],['VIDEO/COUNCIL'+era+'.AVI',{data:source}]],era),source);
    assert.equal(chooseCouncilSource([['COUNCIL0.AVI',{data:source}]],era),null);
    const c=await verifyCouncilShadowPair(source,payload,matching,{...options,era});
    assert.equal(c.scope,'COUNCIL'+era);
    await assert.rejects(verifyCouncilShadowPair(source,payload,manifest,{...options,era}),/PAIR_IDENTITY/);
}
assert.equal(chooseCouncilSource([['ANARCHY0.AVI',{data:source}]],0),null);
assert.equal(chooseCouncilSource([['COUNCIL3.AVI',{data:source}]],3),null);
console.log('CIV2_T025_COUNCIL_LOCAL_PAIR_SOURCE=PASS');
