import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const load = (path) => import(pathToFileURL(join(directory, path)));
const { fetchJson, requestJson, HttpTransportError } = await load(
  "shared/infrastructure/http.js",
);
const { createDtoReader } = await load("shared/infrastructure/dtoReader.js");

class StatusError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
const messages = {
  unreadable: "応答を読めません",
  unreadableFailure: "失敗しました（応答不明）",
  failed: "失敗しました",
};
const request = (signal) =>
  requestJson(
    "/api/x",
    { signal },
    (status, message) => new StatusError(status, message),
    messages,
  );

test("共通HTTPはCookie・キャッシュ・CSRFの送信方法を揃える", async (context) => {
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push(options);
    return Response.json({});
  });
  await fetchJson("/api/x");
  await fetchJson("/api/x", { method: "PUT", payload: { a: 1 }, csrf: "t" });
  await fetchJson("/api/x", { method: "POST", payload: {} });
  for (const options of calls) {
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
  }
  assert.equal(calls[0].method, "GET");
  assert.equal(calls[0].headers, undefined);
  assert.equal(calls[1].method, "PUT");
  assert.equal(calls[1].headers["X-CSRF-Token"], "t");
  assert.equal(calls[1].body, '{"a":1}');
  assert.ok(!("X-CSRF-Token" in calls[2].headers));
});

test("HTTPステータス・detail・不正応答・通信失敗を業務エラーへ変換する", async (context) => {
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "日本語のdetail" }, { status: 409 }),
  );
  const fails = (status, message) => (error) =>
    error instanceof StatusError &&
    error.status === status &&
    error.message === message;
  await assert.rejects(request(), fails(409, "日本語のdetail"));
  fetch.mock.mockImplementation(async () => Response.json({}, { status: 500 }));
  await assert.rejects(request(), fails(500, "失敗しました"));
  fetch.mock.mockImplementation(async () => new Response("not json"));
  await assert.rejects(request(), fails(502, "応答を読めません"));
  fetch.mock.mockImplementation(
    async () => new Response("down", { status: 503 }),
  );
  await assert.rejects(request(), fails(503, "失敗しました（応答不明）"));
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("network");
  });
  await assert.rejects(request(), (error) => error.status === 0);
  await assert.rejects(
    fetchJson("/api/x"),
    (error) => error instanceof HttpTransportError && error.kind === "network",
  );
});

test("キャンセルは業務エラーや通信失敗へ変換しない", async (context) => {
  const reason = new DOMException("Aborted", "AbortError");
  context.mock.method(globalThis, "fetch", async () => {
    throw reason;
  });
  // 中断信号がなくても、AbortErrorはキャンセルとして伝える。
  await assert.rejects(request(), (error) => error === reason);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(request(controller.signal), (error) => error === reason);
});

test("DTOの検証は不正な値を呼出し側のエラーにする", () => {
  const reader = createDtoReader(() => {
    throw new StatusError(502, "不正");
  });
  assert.deepEqual(reader.record({ a: 1 }), { a: 1 });
  assert.equal(reader.nullableText(null), null);
  assert.equal(reader.integer(0), 0);
  assert.equal(reader.nullableInteger(null), null);
  for (const read of [
    () => reader.record([]),
    () => reader.list({}),
    () => reader.text(" "),
    () => reader.integer(1.5),
    () => reader.integer(-1),
    () => reader.nullableInteger(0),
  ])
    assert.throws(read, (error) => error.status === 502);
});
