/*
 * Run the FastAPI golden set against an isolated SQLite fixture.
 *
 * Offline validation:
 *   node eval/run-golden-set-v2.js --dry-run
 *
 * Live run (starts an isolated backend):
 *   ANTHROPIC_API_KEY=... node eval/run-golden-set-v2.js --run-id 2026-07-31
 *
 * Existing pre-seeded backend:
 *   node eval/run-golden-set-v2.js --server-url http://localhost:8020 --run-id local
 */
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const {
  GOLDEN_SET,
  PAGES,
  DOC1,
  DOC2,
  DOC_DEFAULT,
  DOC_MERGED,
} = require('./golden-set-v2');

const REPO_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(REPO_ROOT, 'codebase', 'prototype', 'backend');
const TERMINAL_DIMENSIONS = new Set(['D1', 'D2', 'D3', 'D4', 'D5', 'D6']);

function parseArgs(argv) {
  const options = {
    dryRun: false,
    overwrite: false,
    keepDb: false,
    runId: null,
    serverUrl: null,
    python: process.env.PYTHON || null,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--overwrite') options.overwrite = true;
    else if (arg === '--keep-db') options.keepDb = true;
    else if (arg === '--run-id') options.runId = argv[++i];
    else if (arg === '--server-url') options.serverUrl = argv[++i];
    else if (arg === '--python') options.python = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!options.dryRun && !options.runId) {
    throw new Error('--run-id is required for a live run');
  }
  if (options.runId && !/^[A-Za-z0-9._-]+$/.test(options.runId)) {
    throw new Error('--run-id may contain only letters, numbers, dot, underscore, and dash');
  }
  return options;
}

function validateGoldenSet() {
  const errors = [];
  const ids = new Set();
  const features = {};
  const classes = {};
  const dimensions = {};
  let chatlogCases = 0;

  for (const testCase of GOLDEN_SET) {
    if (ids.has(testCase.id)) errors.push(`duplicate id ${testCase.id}`);
    ids.add(testCase.id);
    features[testCase.feature] = (features[testCase.feature] || 0) + 1;
    classes[testCase.lop] = (classes[testCase.lop] || 0) + 1;
    if (String(testCase.nguon).includes('Chatlog')) chatlogCases += 1;
    for (const dimension of testCase.dimensions || []) {
      if (!TERMINAL_DIMENSIONS.has(dimension)) errors.push(`${testCase.id}: unknown ${dimension}`);
      dimensions[dimension] = (dimensions[dimension] || 0) + 1;
    }
    if (!['onboarding', 'summary', 'explain', 'exercise'].includes(testCase.feature)) {
      errors.push(`${testCase.id}: unknown feature ${testCase.feature}`);
    }
    if (testCase.feature === 'onboarding' && testCase.payload && testCase.payload.answers) {
      errors.push(`${testCase.id}: legacy onboarding payload`);
    }
    if (testCase.feature === 'explain' && testCase.payload?.source) {
      errors.push(`${testCase.id}: unsupported explain field source`);
    }
    if (testCase.persona && !testCase.persona.session && (testCase.expectStatus || 200) === 200) {
      errors.push(`${testCase.id}: persona has no FastAPI session payload`);
    }
  }
  if (GOLDEN_SET.length !== 59) errors.push(`expected 59 cases, found ${GOLDEN_SET.length}`);
  if (chatlogCases !== 12) errors.push(`expected 12 chatlog cases, found ${chatlogCases}`);
  return { errors, stats: { cases: GOLDEN_SET.length, chatlogCases, features, classes, dimensions } };
}

function buildFixture(tempDir) {
  const docs = [DOC1, DOC2, DOC_DEFAULT, DOC_MERGED];
  const pageMap = {};
  for (const doc of docs) {
    pageMap[doc.id] = Object.values(PAGES[doc.id] || {}).map(page => ({
      page_number: page.page_number,
      content_text: [page.heading, page.content_text].filter(Boolean).join('\n'),
    }));
  }
  for (const testCase of GOLDEN_SET) {
    if (!testCase.extraPages) continue;
    for (const page of Object.values(testCase.extraPages)) {
      const documentId = testCase.payload.document_id;
      const existing = pageMap[documentId].find(item => item.page_number === page.page_number);
      const normalized = {
        page_number: page.page_number,
        content_text: [page.heading, page.content_text].filter(Boolean).join('\n'),
      };
      if (existing) Object.assign(existing, normalized);
      else pageMap[documentId].push(normalized);
    }
  }
  const documents = docs.map(doc => ({
    document_id: doc.id,
    source_pdf_path: path.join(tempDir, doc.filename),
    total_pages: doc.totalPages,
    validated: true,
    pages: pageMap[doc.id].sort((a, b) => a.page_number - b.page_number),
  }));
  documents.push({
    document_id: 'doc_empty_ingest',
    source_pdf_path: path.join(tempDir, 'empty.pdf'),
    total_pages: 1,
    validated: false,
    pages: [],
  });
  return { documents };
}

function choosePython(explicit) {
  if (explicit) return explicit;
  const windowsVenv = path.resolve(REPO_ROOT, '..', '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(windowsVenv)) return windowsVenv;
  return process.platform === 'win32' ? 'python' : 'python3';
}

function gitCommit() {
  const result = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' });
  return result.status === 0 ? result.stdout.trim() : 'unknown';
}

function fileSha256(filename) {
  return crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
}

function hasAnthropicKey() {
  if (process.env.ANTHROPIC_API_KEY) return true;
  const envPath = path.join(BACKEND_DIR, '.env');
  if (!fs.existsSync(envPath)) return false;
  return fs.readFileSync(envPath, 'utf8')
    .split(/\r?\n/)
    .some(line => /^\s*ANTHROPIC_API_KEY\s*=\s*\S+/.test(line) && !/=\s*(your_|replace|$)/i.test(line));
}

async function waitForServer(serverUrl, child) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Backend exited with code ${child.exitCode}`);
    try {
      const response = await fetch(`${serverUrl}/`);
      if (response.ok) return;
    } catch {
      // Backend is still starting.
    }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for the isolated FastAPI backend');
}

async function requestJson(serverUrl, method, route, body) {
  const startedAt = Date.now();
  try {
    const response = await fetch(`${serverUrl}${route}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const raw = await response.text();
    let data = raw;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      // Preserve non-JSON error bodies for the audit trail.
    }
    return { status: response.status, data, latencyMs: Date.now() - startedAt };
  } catch (error) {
    return { status: 0, data: null, error: String(error.message || error), latencyMs: Date.now() - startedAt };
  }
}

function extractCitedPages(value) {
  const found = new Set();
  function visit(item) {
    if (typeof item === 'string') {
      for (const match of item.matchAll(/(?:\[?(?:Page|Trang)\s+)(\d+)\]?/gi)) found.add(Number(match[1]));
    } else if (Array.isArray(item)) {
      item.forEach(visit);
    } else if (item && typeof item === 'object') {
      if (Array.isArray(item.page_refs)) item.page_refs.forEach(page => found.add(Number(page)));
      if (Number.isInteger(item.page_number)) found.add(item.page_number);
      Object.values(item).forEach(visit);
    }
  }
  visit(value);
  return [...found].filter(Number.isInteger).sort((a, b) => a - b);
}

function allowedPages(documentId, fixture) {
  const document = fixture.documents.find(item => item.document_id === documentId);
  return new Set((document?.pages || []).map(page => page.page_number));
}

async function ensureSession(serverUrl, persona, sessionCache) {
  if (!persona?.session) return null;
  if (sessionCache.has(persona.label)) return sessionCache.get(persona.label);
  const response = await requestJson(serverUrl, 'POST', '/session', persona.session);
  if (response.status !== 200 || !response.data?.session_id) {
    throw new Error(`Could not create session for ${persona.label}: HTTP ${response.status}`);
  }
  sessionCache.set(persona.label, response.data.session_id);
  return response.data.session_id;
}

async function executeOnce(testCase, serverUrl, sessionCache) {
  if (testCase.feature === 'onboarding') {
    return requestJson(serverUrl, 'POST', '/session', testCase.payload);
  }
  const sessionId = await ensureSession(serverUrl, testCase.persona, sessionCache);
  if (testCase.feature === 'summary') {
    return requestJson(serverUrl, 'GET', `/summary/${encodeURIComponent(testCase.payload.document_id)}`);
  }
  const payload = { ...testCase.payload };
  if (payload.session_id === '__ACTIVE__') payload.session_id = sessionId;
  if (testCase.feature === 'explain') {
    payload.mode = payload.mode || 'highlight';
    return requestJson(serverUrl, 'POST', '/explain', payload);
  }
  return requestJson(serverUrl, 'POST', '/exercise', payload);
}

async function runCase(testCase, serverUrl, fixture, sessionCache) {
  let previousSessionResponse = null;
  if (testCase.previousSession) {
    previousSessionResponse = await requestJson(serverUrl, 'POST', '/session', testCase.previousSession);
  }
  let responses;
  if (testCase.isConcurrent) {
    const concurrent = { ...testCase, payload: testCase.concurrentPayload, isConcurrent: false };
    responses = await Promise.all([
      executeOnce(testCase, serverUrl, sessionCache),
      executeOnce(concurrent, serverUrl, sessionCache),
    ]);
  } else if (testCase.isCacheTest || testCase.isNoCacheTest || testCase.id === 'E12') {
    responses = [
      await executeOnce(testCase, serverUrl, sessionCache),
      await executeOnce(testCase, serverUrl, sessionCache),
    ];
  } else {
    responses = [await executeOnce(testCase, serverUrl, sessionCache)];
  }

  const expectedStatus = testCase.expectStatus || 200;
  const specialChecks = [];
  if (testCase.id === 'E12') {
    specialChecks.push({
      name: 'double-submit creates distinct sessions',
      pass: Boolean(
        responses[0].data?.session_id
        && responses[1].data?.session_id
        && responses[0].data.session_id !== responses[1].data.session_id
      ),
    });
  }
  if (testCase.isCacheTest) {
    specialChecks.push({
      name: 'cached response is stable',
      pass: JSON.stringify(responses[0].data) === JSON.stringify(responses[1].data),
    });
  }
  if (testCase.previousSession) {
    specialChecks.push({
      name: 'profile update creates a distinct session',
      pass: Boolean(
        previousSessionResponse?.data?.session_id
        && responses[0].data?.session_id
        && previousSessionResponse.data.session_id !== responses[0].data.session_id
      ),
    });
  }
  const structuralPass = responses.every(response => response.status === expectedStatus)
    && specialChecks.every(check => check.pass);
  const documentId = testCase.payload?.document_id;
  const allowed = allowedPages(documentId, fixture);
  const citedPages = extractCitedPages(responses.map(response => response.data));
  const invalidCites = citedPages.filter(page => !allowed.has(page));
  const d1Auto = (testCase.dimensions || []).includes('D1')
    ? structuralPass && invalidCites.length === 0
    : null;

  return {
    id: testCase.id,
    class: testCase.lop,
    feature: testCase.feature,
    expected: testCase.expect,
    expectedStatus,
    structuralPass,
    d1Auto,
    allowedPages: [...allowed].sort((a, b) => a - b),
    citedPages,
    invalidCites,
    specialChecks,
    previousSessionResponse,
    responses,
  };
}

function markdownReport(metadata, results) {
  const structural = results.filter(result => result.structuralPass).length;
  const d1Scored = results.filter(result => result.d1Auto !== null);
  const d1Passed = d1Scored.filter(result => result.d1Auto).length;
  const rows = results.map(result => {
    const status = result.responses.map(item => item.status).join('/');
    const d1 = result.d1Auto === null ? 'N/A' : result.d1Auto ? 'PASS' : 'FAIL';
    return `| ${result.id} | ${result.feature} | ${status} | ${result.structuralPass ? 'PASS' : 'FAIL'} | ${d1} |  |  |  |  |  |`;
  });
  return [
    `# Golden set v2 - ${metadata.runId}`,
    '',
    `- Ran at: ${metadata.ranAt}`,
    `- Git commit: \`${metadata.gitCommit}\``,
    `- Golden SHA-256: \`${metadata.goldenSha256}\``,
    `- Cases: ${results.length}`,
    `- Structural pass: ${structural}/${results.length}`,
    `- D1 automatic pass: ${d1Passed}/${d1Scored.length}`,
    '',
    '> D2-D6 are intentionally blank. Two reviewers must score them independently using `review-v2-rubric.md`.',
    '',
    '| ID | Feature | HTTP | Structure | D1 auto | D2 | D3 | D4 | D5 | D6 | Reviewer notes |',
    '|---|---|---:|---|---|---|---|---|---|---|---|',
    ...rows,
    '',
  ].join('\n');
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const validation = validateGoldenSet();
  console.log(JSON.stringify(validation.stats, null, 2));
  if (validation.errors.length) throw new Error(validation.errors.join('\n'));
  if (options.dryRun) {
    console.log('Golden set v2 validation passed.');
    return;
  }
  if (!options.serverUrl && !hasAnthropicKey()) {
    throw new Error('ANTHROPIC_API_KEY is required for an isolated live run; no synthetic results were written');
  }

  const jsonPath = path.join(__dirname, `results-v2-${options.runId}.json`);
  const mdPath = path.join(__dirname, `results-v2-${options.runId}.md`);
  if (!options.overwrite && (fs.existsSync(jsonPath) || fs.existsSync(mdPath))) {
    throw new Error('Result file already exists; choose another --run-id or pass --overwrite');
  }

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vlearn-eval-v2-'));
  const fixture = buildFixture(tempDir);
  let child = null;
  let serverUrl = options.serverUrl;
  try {
    if (!serverUrl) {
      const fixturePath = path.join(tempDir, 'fixture.json');
      const dbPath = path.join(tempDir, 'golden-v2.db');
      fs.writeFileSync(fixturePath, JSON.stringify(fixture, null, 2));
      const python = choosePython(options.python);
      const seed = spawnSync(python, [path.join(__dirname, 'seed-golden-v2.py'), fixturePath], {
        cwd: REPO_ROOT,
        env: { ...process.env, VLEARN_DB_PATH: dbPath },
        encoding: 'utf8',
      });
      if (seed.status !== 0) throw new Error(`Fixture seed failed:\n${seed.stderr || seed.stdout}`);
      serverUrl = 'http://127.0.0.1:8021';
      child = spawn(python, ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8021'], {
        cwd: BACKEND_DIR,
        env: { ...process.env, VLEARN_DB_PATH: dbPath },
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      child.stdout.on('data', data => process.stdout.write(`[backend] ${data}`));
      child.stderr.on('data', data => process.stderr.write(`[backend] ${data}`));
      await waitForServer(serverUrl, child);
    }

    const sessionCache = new Map();
    const results = [];
    for (const testCase of GOLDEN_SET) {
      process.stdout.write(`Run ${testCase.id}... `);
      const result = await runCase(testCase, serverUrl, fixture, sessionCache);
      results.push(result);
      console.log(result.structuralPass ? 'PASS' : 'FAIL');
    }
    const metadata = {
      schemaVersion: 2,
      runId: options.runId,
      ranAt: new Date().toISOString(),
      gitCommit: gitCommit(),
      goldenSha256: fileSha256(path.join(__dirname, 'golden-set-v2.js')),
      serverUrl,
      model: process.env.ANTHROPIC_MODEL || 'backend-default',
      isolatedDatabase: !options.serverUrl,
    };
    fs.writeFileSync(jsonPath, JSON.stringify({ metadata, results }, null, 2));
    fs.writeFileSync(mdPath, markdownReport(metadata, results));
    console.log(`Saved ${path.relative(REPO_ROOT, jsonPath)} and ${path.relative(REPO_ROOT, mdPath)}`);
  } finally {
    if (child && child.exitCode === null) child.kill();
    if (!options.keepDb) fs.rmSync(tempDir, { recursive: true, force: true });
    else console.log(`Kept fixture directory: ${tempDir}`);
  }
}

main().catch(error => {
  console.error(error.message || error);
  process.exitCode = 1;
});
