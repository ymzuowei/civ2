import assert from 'node:assert/strict';
import {chooseCouncilSource,verifyCouncilShadowPair,readLocalMediaPack} from '../council_local_pair.js';
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
{
    const header=new TextEncoder().encode(JSON.stringify({schema:1,opening:{
        scope:'OWNER_LOCAL_OPENING_ONLY',schema:1,source_bytes:2,derived_bytes:2,
        source_sha256:sha,derived_sha256:sha,duration_s:2},council:manifest}));
    const prefix=new Uint8Array(12);prefix.set(new TextEncoder().encode('CIV2M01\n'));
    new DataView(prefix.buffer).setUint32(8,header.length,true);
    const file=new Blob([prefix,header,payload,payload]);
    const p=await readLocalMediaPack(file,source,source,0,options);
    assert.equal(p.opening.duration,2);assert.equal(p.council.scope,'COUNCIL0');
    await assert.rejects(readLocalMediaPack(file,source,source,2,options),/PAIR_IDENTITY/);
    await assert.rejects(readLocalMediaPack(new Blob([file,payload]),source,source,0,options),/PACK_LAYOUT/);
}
console.log('CIV2_T025_COUNCIL_LOCAL_PAIR_SOURCE=PASS');
