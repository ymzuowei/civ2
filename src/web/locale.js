// Browser language aliases. Independent of generated texts.js, so this is
// safe to unit-test with Node without rebuilding the web page.
export function match(code, list) {
    let c = (code || '').replace('_', '-').toLowerCase();
    // Taiwan, Hong Kong, Macau and explicit Hant retain the original
    // Traditional Chinese translation.
    if (/^zh-(tw|hk|mo|hant)(-|$)/.test(c))
        c = 'zh-hant';
    // Mainland China, Singapore and explicit Hans prefer Simplified Chinese.
    else if (/^zh-(cn|sg|hans)(-|$)/.test(c))
        c = 'zh-hans';
    const codes = list.map((l) => l.code);
    return codes.find((k) => k.toLowerCase() === c) ||
           codes.find((k) => k.toLowerCase() === c.split('-')[0]) || 'en';
}
