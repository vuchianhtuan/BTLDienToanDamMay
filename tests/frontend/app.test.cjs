// Execute the real app.js with a small DOM/transport harness for merge regressions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

class Element {
  constructor() {
    this.children = [];
    this.value = '';
    this.files = [];
    this.hidden = false;
    this.disabled = false;
    this.attributes = {};
    this.listeners = {};
    this.classList = { add() {}, remove() {} };
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

const hash = 'a'.repeat(64);
const fixture = (index) => ({ id: String(index), filename: `file-${index}.txt`,
  sha256: hash, size: 10, created_at: '2026-10-28T00:00:00Z' });
const flush = () => new Promise((resolve) => setImmediate(resolve));

async function harness(rows = []) {
  const elements = new Map();
  const get = (id) => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const state = { rows, requests: [], copies: [], pendingLists: null, xhr: null };
  class Upload {
    constructor() { this.upload = {}; state.xhr = this; }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader() {}
    send(file) { this.file = file; }
    abort() { this.onabort(); }
  }
  const context = vm.createContext({
    document: { getElementById: get, createElement: () => new Element() },
    XMLHttpRequest: Upload,
    setTimeout,
    URL,
    IntegrityClient: {
      async copyHash(value) { state.copies.push(value); },
      request(url) {
        state.requests.push(url);
        if (url === '/health/ready') return Promise.resolve({ max_file_bytes: 100000, storage: 'local' });
        if (url.endsWith('/verify')) return Promise.resolve({ intact: true,
          expected_sha256: hash, actual_sha256: hash, expected_size: 10, actual_size: 10 });
        if (state.pendingLists) return new Promise((resolve) => state.pendingLists.push(resolve));
        return Promise.resolve(state.rows);
      },
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../frontend/app.js'), 'utf8'), context);
  await flush();
  return { get, state };
}

test('exactly 20 files does not enable an empty next page; verify/copy remain available', async () => {
  const { get, state } = await harness(Array.from({ length: 20 }, (_, i) => fixture(i)));
  assert.match(state.requests[1], /limit=21/);
  assert.equal(get('next').disabled, true);
  const actions = get('files').children[0].children[3].children[0].children;
  assert.equal(actions.length, 3);
  await actions[1].onclick();
  assert.equal(get('verification').hidden, false);
  assert.equal(get('expectedHash').textContent, hash);
  await get('copyExpected').onclick();
  assert.deepEqual(state.copies, [hash]);
});

test('progress 100% still waits for server; cancellation restores controls and warns of uncertain storage', async () => {
  const { get, state } = await harness();
  get('file').files = [{ name: 'demo.txt', size: 10 }];
  const sending = get('uploadForm').onsubmit({ preventDefault() {} });
  assert.equal(get('file').disabled, true);
  assert.equal(get('cancelUpload').hidden, false);
  state.xhr.upload.onprogress({ lengthComputable: true, loaded: 10, total: 10 });
  assert.match(get('progressText').textContent, /Đang chờ máy chủ/);
  assert.equal(get('upload').disabled, true);
  get('cancelUpload').onclick();
  await sending;
  assert.equal(get('upload').disabled, false);
  assert.equal(get('file').disabled, false);
  assert.equal(get('cancelUpload').hidden, true);
  assert.equal(get('uploadForm').attributes['aria-busy'], 'false');
  assert.match(get('message').textContent, /Máy chủ có thể đã nhận tệp/);
});

test('a stale list response cannot replace the newer API-key refresh result', async () => {
  const { get, state } = await harness();
  state.pendingLists = [];
  get('apiKey').onchange();
  get('apiKey').onchange();
  assert.equal(state.pendingLists.length, 2);
  state.pendingLists[1]([fixture('new')]);
  await flush();
  state.pendingLists[0]([fixture('old')]);
  await flush();
  assert.equal(get('files').children[0].children[0].children[0].textContent, 'file-new.txt');
});

test('dropping multiple files does not replace the selected file', async () => {
  const { get } = await harness();
  const selected = [{ name: 'keep.txt' }];
  get('file').files = selected;
  get('drop').listeners.drop({ preventDefault() {}, dataTransfer: { files: [{}, {}] } });
  assert.equal(get('file').files, selected);
  assert.match(get('message').textContent, /Mỗi lần tải lên một tệp/);
});
