const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { request, copyHash } = require("../../frontend/api-client.js");
let server, base;

before(async () => {
  server = http.createServer((req, res) => {
    if (req.url === "/slow") return;
    if (req.url === "/slow-body") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.flushHeaders();
      return;
    }
    if (req.url === "/invalid") return res.end("not json");
    if (req.url === "/binary") return res.end(Buffer.from([0, 255, 7]));
    if (req.url.startsWith("/status/")) {
      res.writeHead(Number(req.url.split("/").pop()));
      return res.end("internal error details must not leak");
    }
    if (req.url === "/upload") {
      let size = 0;
      req.on("data", (data) => {
        size += data.length;
      });
      req.on("end", () =>
        res.end(
          JSON.stringify({
            size,
            authorized: req.headers["x-api-key"] === "test-key",
          }),
        ),
      );
      return;
    }
    res.end(JSON.stringify({ status: "ok" }));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(async () => {
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
});

test("reads successful JSON through HTTP", async () => {
  assert.deepEqual(await request(base), { status: "ok" });
});
test("uploads unchanged bytes and forwards API key", async () => {
  const result = await request(base + "/upload", {
    method: "POST",
    headers: { "X-API-Key": "test-key" },
    body: new Uint8Array([0, 255, 7]),
  });
  assert.deepEqual(result, { size: 3, authorized: true });
});
for (const [status, message] of [
  [401, /API key/],
  [413, /dung lượng/],
  [404, /Không tìm thấy/],
  [503, /Dịch vụ/],
]) {
  test(`explains HTTP ${status} without exposing server internals`, async () => {
    await assert.rejects(
      request(base + "/status/" + status),
      (error) =>
        error.status === status &&
        message.test(error.message) &&
        !error.message.includes("internal error"),
    );
  });
}
test("times out before headers and marks upload outcome uncertain", async () => {
  await assert.rejects(
    request(base + "/slow", {}, { timeoutMs: 30 }),
    (error) => error.uncertain && /quá thời gian/.test(error.message),
  );
});
test("also bounds time spent reading the response body", async () => {
  await assert.rejects(
    request(base + "/slow-body", {}, { timeoutMs: 30 }),
    (error) => error.uncertain && /quá thời gian/.test(error.message),
  );
});
test("distinguishes malformed successful JSON", async () => {
  await assert.rejects(request(base + "/invalid"), /dữ liệu không hợp lệ/);
});
test("downloads binary bytes without JSON conversion", async () => {
  const blob = await request(base + "/binary", {}, { read: "blob" });
  assert.deepEqual(
    new Uint8Array(await blob.arrayBuffer()),
    new Uint8Array([0, 255, 7]),
  );
});
test("reports connection failures without retrying a write", async () => {
  let calls = 0;
  await assert.rejects(
    request(
      base,
      { method: "POST" },
      {
        fetcher: async () => {
          calls++;
          throw new TypeError("network down");
        },
      },
    ),
    (error) => error.uncertain && /Không kết nối/.test(error.message),
  );
  assert.equal(calls, 1);
});
test("copies exactly the hash and waits for clipboard confirmation", async () => {
  const hash = "ab".repeat(32);
  let copied;
  await copyHash(hash, {
    writeText: async (value) => {
      copied = value;
    },
  });
  assert.equal(copied, hash);
});
test("rejects invalid hashes and handles clipboard denial", async () => {
  await assert.rejects(copyHash("invalid", {}), /không hợp lệ/);
  await assert.rejects(
    copyHash("ab".repeat(32), {
      writeText: async () => {
        throw new Error("denied");
      },
    }),
    /thủ công/,
  );
  await assert.rejects(copyHash("ab".repeat(32), {}), /Trình duyệt/);
});
