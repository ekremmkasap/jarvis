import test from "node:test";
import assert from "node:assert/strict";

import { BridgeSkill } from "../src/runtime/skills/BridgeSkill";

test("BridgeSkill forwards args and data payloads", async (t) => {
  const originalFetch = globalThis.fetch;
  let capturedUrl = "";
  let capturedBody = "";

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedBody = String(init?.body ?? "");
    return new Response(JSON.stringify({ ok: true, result: { forwarded: true } }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  };

  const skill = new BridgeSkill("http://127.0.0.1:8081");
  const result = await skill.run({
    command: "stripe_webhook",
    args: { text: "hello" },
    data: { session: { id: "cs_test_1" } },
    chatId: "42"
  });

  assert.deepEqual(result, { forwarded: true });
  assert.equal(capturedUrl, "http://127.0.0.1:8081/command");
  assert.deepEqual(JSON.parse(capturedBody), {
    command: "stripe_webhook",
    args: { text: "hello" },
    data: { session: { id: "cs_test_1" } },
    chatId: "42"
  });
});

test("BridgeSkill uses BRIDGE_URL from env when no constructor override is provided", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalBridgeUrl = process.env.BRIDGE_URL;
  let capturedUrl = "";

  t.after(() => {
    globalThis.fetch = originalFetch;
    if (originalBridgeUrl === undefined) {
      delete process.env.BRIDGE_URL;
    } else {
      process.env.BRIDGE_URL = originalBridgeUrl;
    }
  });

  process.env.BRIDGE_URL = "http://localhost:9999";
  globalThis.fetch = async (input) => {
    capturedUrl = String(input);
    return new Response(JSON.stringify({ ok: true, result: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  };

  const skill = new BridgeSkill();
  const result = await skill.run({ command: "status" });

  assert.equal(result, "ok");
  assert.equal(capturedUrl, "http://localhost:9999/command");
});

test("BridgeSkill validates object input", async () => {
  const skill = new BridgeSkill("http://127.0.0.1:8081");
  await assert.rejects(() => skill.run("invalid"), /BRIDGE_COMMAND_INVALID: input must be an object/);
  await assert.rejects(
    () => skill.run({ command: "test", data: "bad" }),
    /BRIDGE_COMMAND_INVALID: data must be an object when provided/
  );
});

test("BridgeSkill surfaces HTTP failures", async (t) => {
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async () =>
    new Response(JSON.stringify({ error: "gateway down" }), {
      status: 502,
      headers: { "Content-Type": "application/json" }
    });

  const skill = new BridgeSkill("http://127.0.0.1:8081");
  await assert.rejects(
    () => skill.run({ command: "status" }),
    /BRIDGE_HTTP_502:gateway down/
  );
});

test("BridgeSkill surfaces timeout failures", async (t) => {
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (_input, init) =>
    new Promise<Response>((_resolve, reject) => {
      const signal = init?.signal;
      if (!signal) {
        reject(new Error("signal missing"));
        return;
      }
      signal.addEventListener(
        "abort",
        () => reject(new DOMException("aborted", "AbortError")),
        { once: true }
      );
    });

  const skill = new BridgeSkill("http://127.0.0.1:8081", 5);
  await assert.rejects(
    () => skill.run({ command: "status" }),
    /BRIDGE_TIMEOUT:5ms/
  );
});

test("BridgeSkill surfaces invalid JSON and bridge command failures", async (t) => {
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async () =>
    new Response(JSON.stringify({ ok: false, error: "command failed" }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });

  const skill = new BridgeSkill("http://127.0.0.1:8081");
  await assert.rejects(
    () => skill.run({ command: "status" }),
    /BRIDGE_COMMAND_FAILED:command failed/
  );

  globalThis.fetch = async () => new Response("not-json", { status: 200 });
  await assert.rejects(
    () => skill.run({ command: "status" }),
    /BRIDGE_INVALID_JSON:not-json/
  );
});
