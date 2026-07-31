/*
 * Chạy toàn bộ golden-set.js qua backend thật (POST /api/summarize) và tự chấm
 * dimension D1 "Có căn cứ" (mọi số trang được trích phải nằm trong sections đã gửi).
 * D2/D3/D4 (không bịa nội dung / an toàn phạm vi / đúng tầm persona) cần đọc output
 * bằng mắt — script chỉ in ra để người chấm điền, không tự suy đoán các dimension này.
 *
 * Chạy: SERVER_URL=http://localhost:3000 RUN_ID=legacy-local node eval/run-golden-set.js
 * Yêu cầu server (codebase/server) đang chạy và đã có OPENAI_API_KEY trong .env.
 */
const { GOLDEN_SET } = require('./golden-set');

const SERVER_URL = process.env.SERVER_URL || 'http://localhost:3000';
const RUN_ID = process.env.RUN_ID || 'legacy-local';
if (!/^[A-Za-z0-9._-]+$/.test(RUN_ID)) {
  throw new Error('RUN_ID may contain only letters, numbers, dot, underscore, and dash');
}

function extractCitedPages(text) {
  const matches = [...text.matchAll(/trang\s+(\d+)/gi)];
  return [...new Set(matches.map(m => Number(m[1])))];
}

async function runCase(c) {
  const t0 = Date.now();
  try {
    const res = await fetch(SERVER_URL + '/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docTitle: c.doc.title, sections: c.sections, personaTags: c.personaTags }),
    });
    const data = await res.json();
    const latencyMs = Date.now() - t0;
    if (!res.ok || !data.ok) {
      return { id: c.id, lop: c.lop, ok: false, error: data.error || ('HTTP ' + res.status), latencyMs };
    }
    const validPages = new Set(c.sections.map(s => s.page));
    const citedPages = extractCitedPages(data.text);
    const invalidCites = citedPages.filter(p => !validPages.has(p));
    const d1_grounded = c.sections.length === 0
      ? (citedPages.length === 0) // không có gì để trích -> không nên tự bịa trang
      : (citedPages.length > 0 && invalidCites.length === 0);
    return {
      id: c.id, lop: c.lop, nguon: c.nguon, expect: c.expect, ok: true,
      model: data.model, latencyMs, text: data.text,
      validPages: [...validPages], citedPages, invalidCites, d1_grounded,
    };
  } catch (err) {
    return { id: c.id, lop: c.lop, ok: false, error: String(err.message || err), latencyMs: Date.now() - t0 };
  }
}

(async () => {
  const results = [];
  for (const c of GOLDEN_SET) {
    process.stdout.write('Chạy ' + c.id + ' (' + c.lop + ')... ');
    const r = await runCase(c);
    results.push(r);
    console.log(r.ok ? (r.d1_grounded ? 'OK, D1=pass' : 'OK, D1=FAIL') : 'LỖI: ' + r.error);
  }
  const fs = require('fs');
  const path = require('path');
  const outPath = path.join(__dirname, `results-${RUN_ID}.json`);
  if (fs.existsSync(outPath) && process.env.OVERWRITE_RESULTS !== '1') {
    throw new Error(`Refusing to overwrite ${outPath}; choose another RUN_ID or set OVERWRITE_RESULTS=1`);
  }
  fs.writeFileSync(outPath, JSON.stringify({ ranAt: new Date().toISOString(), results }, null, 2));
  const total = results.length;
  const okCount = results.filter(r => r.ok).length;
  const d1Pass = results.filter(r => r.ok && r.d1_grounded).length;
  console.log('\n=== Tổng kết ===');
  console.log('Tổng case:', total, '| Gọi API thành công:', okCount, '| D1 (có căn cứ) pass:', d1Pass + '/' + okCount);
  console.log('Đã lưu kết quả thô vào', outPath);
})();
