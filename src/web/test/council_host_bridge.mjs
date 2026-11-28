import assert from 'node:assert/strict';
import {createCouncilHostBridge} from '../council_host_bridge.js';
const payload=new Uint8Array([1,2,3]);
let closed=0,drawn=0;
function makeCanvas(){
    return {width:0,height:0,getContext(){return {
        drawImage(){drawn++;},
        getImageData(){return {data:new Uint8ClampedArray(2*2*4)};}
    };}};
}
function makeRange(){
    return {async present(frame,draw){draw({});return {status:'presented'};},
        close(){closed++;},stats(){return {closed:false,retainedFrames:0};}};
}
{
    const canvas=makeCanvas();
    const bridge=createCouncilHostBridge({makeRange,makeCanvas:()=>canvas});
    const clip={scope:'COUNCIL0',shadowOnly:true,verified:true,payload,
        table:{nativeStart:0,samples:[{}]},config:{codedWidth:2,codedHeight:2}};
    assert.equal(bridge.open(clip),true);
    assert.equal(bridge.startRange(0,0),true);
    const prepared=await bridge.prepare(0);
    assert.equal(prepared.status,'ready');
    assert.equal(prepared.bytes,16);
    assert.equal(bridge.stats().preparedBytes,16);
    assert.equal(bridge.discard(prepared),true);
    assert.equal(bridge.stats().preparedBytes,0);
    assert.equal(drawn,1);
    bridge.close();
    assert.equal(closed,1);
    assert.equal(canvas.width,0);
    assert.equal(canvas.height,0);
    assert.equal(bridge.stats().activeRange,0);
    assert.equal(bridge.stats().clipBytes,0);
    assert.equal(bridge.stats().canvasPixels,0);
    bridge.dispose();
    assert.equal(bridge.stats().disposed,true);
}
{
    let resolve;
    const canvas=makeCanvas();
    const bridge=createCouncilHostBridge({makeCanvas:()=>canvas,makeRange:()=>({
        present(){return new Promise(r=>{resolve=r;});},close(){closed++;},
        stats(){return {closed:false};}
    })});
    const clip={scope:'COUNCIL0',shadowOnly:true,verified:true,payload,
        table:{nativeStart:0,samples:[{}]},config:{codedWidth:2,codedHeight:2}};
    assert.equal(bridge.open(clip),true);
    assert.equal(bridge.startRange(0,0),true);
    const pending=bridge.prepare(0);
    bridge.close();
    resolve({status:'presented'});
    assert.equal(await pending,null);
    assert.equal(bridge.stats().pending,0);
    assert.equal(bridge.stats().preparedBytes,0);
    assert.equal(bridge.stats().clipBytes,0);
    assert.equal(bridge.stats().canvasPixels,0);
    bridge.dispose();
}
console.log('CIV2_T025_COUNCIL_HOST_BRIDGE_LIFECYCLE=PASS');
