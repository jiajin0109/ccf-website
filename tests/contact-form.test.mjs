import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("../site/assets/contact.js", import.meta.url), "utf8");

function setup(endpoint, fetch, lang = "zh-Hant") {
  let submit;
  let resets = 0;
  let focused = false;
  let scrolled = false;
  const status = {
    hidden: true, setAttribute() {},
    focus: () => { focused = true; },
    scrollIntoView: () => { scrolled = true; },
  };
  const button = { textContent: lang === "en" ? "Send a free inquiry" : "送出，免費諮詢", disabled: false };
  const values = new Map([["name", "測試"], ["contact", "@buyer"], ["need", "需求"], ["_gotcha", ""]]);
  const form = {
    dataset: { thanks: lang === "en" ? "We will get back to you soon." : "已收到" },
    querySelector: () => button,
    addEventListener: (_, handler) => { submit = handler; },
    reportValidity: () => true,
    setAttribute() {},
    reset: () => { resets++; },
  };
  vm.runInNewContext(source, {
    document: { documentElement: { lang }, getElementById: id => id === "contact-form" ? form : status },
    window: { CCF_CONFIG: { contactEndpoint: endpoint } },
    FormData: class { get(key) { return values.get(key); } },
    fetch, setTimeout, clearTimeout, AbortController, TypeError,
  });
  return { status, button, values, submit: () => submit({ preventDefault() {} }), resets: () => resets,
    focused: () => focused, scrolled: () => scrolled };
}

test("unconfigured form shows error and keeps customer input", async () => {
  const page = setup("", () => assert.fail("Should not send"));
  await page.submit();
  assert.match(page.status.textContent, /尚未開通/);
  assert.equal(page.status.className, "flash");
  assert.equal(page.resets(), 0);
});

test("successful confirmation resets fields and prevents duplicate in-flight sends", async () => {
  let finish;
  let calls = 0;
  const page = setup("https://formspree.io/f/testform", async (url, options) => {
    calls++;
    assert.equal(url, "https://formspree.io/f/testform");
    assert.equal(options.credentials, "omit");
    assert.equal(options.headers.Accept, "application/json");
    const payload = JSON.parse(options.body);
    assert.equal(payload.contact, "@buyer");
    assert.equal(payload._gotcha, "");
    assert.equal(payload.subject, "CCF 官網｜新客戶諮詢");
    assert.equal(payload.website, undefined);
    await new Promise(resolve => { finish = resolve; });
    return { ok: true, json: async () => ({ ok: true }) };
  });
  const first = page.submit();
  assert.equal(page.button.disabled, true);
  assert.equal(page.status.hidden, false);
  assert.equal(page.status.className, "pending");
  assert.match(page.status.textContent, /正在送出/);
  await page.submit();
  assert.equal(calls, 1);
  finish();
  await first;
  assert.equal(page.resets(), 1);
  assert.equal(page.status.className, "ok");
  assert.equal(page.status.textContent, "✓ 諮詢已成功送出！\n已收到");
  assert.equal(page.status.hidden, false);
  assert.equal(page.focused(), true);
  assert.equal(page.scrolled(), true);
  assert.equal(page.button.textContent, "已送出 ✓");
  assert.equal(page.button.disabled, false);
});

test("rejection and network failure preserve fields and restore submit button", async () => {
  for (const fetch of [
    async () => ({ ok: false, json: async () => ({ errors: [{ message: "服務忙碌" }] }) }),
    async () => ({ ok: false, status: 429, json: async () => ({ error: "quota" }) }),
    async () => { throw new TypeError("network"); },
    async () => { const error = new Error("timeout"); error.name = "AbortError"; throw error; },
  ]) {
    const page = setup("https://formspree.io/f/testform", fetch);
    await page.submit();
    assert.equal(page.resets(), 0);
    assert.equal(page.status.className, "flash");
    assert.equal(page.status.hidden, false);
    assert.equal(page.button.disabled, false);
    assert.equal(page.button.textContent, "送出，免費諮詢");
  }
});

test("misconfigured endpoint never receives customer information", async () => {
  for (const endpoint of ["https://worker.example/contact", "https://formspree.io.attacker.example/f/form", "http://formspree.io/f/form"]) {
    const page = setup(endpoint, () => assert.fail("Should not send"));
    await page.submit();
    assert.match(page.status.textContent, /設定有誤/);
    assert.equal(page.resets(), 0);
  }
});

test("Formspree validation errors are shown as text without clearing fields", async () => {
  const message = "<b>Validation error</b>";
  const page = setup("https://formspree.io/f/testform", async () => ({
    ok: false,
    json: async () => ({ errors: [{ message }] }),
  }));
  await page.submit();
  assert.equal(page.status.textContent, message);
  assert.equal(page.resets(), 0);
});

test("successful HTTP JSON response is accepted without requiring a custom worker response", async () => {
  const page = setup("https://formspree.io/f/testform", async () => ({ ok: true, json: async () => ({ next: "/thanks" }) }));
  await page.submit();
  assert.equal(page.resets(), 1);
  assert.equal(page.status.className, "ok");
});

test("English inquiries use translated feedback and identify their language", async () => {
  let finish;
  const page = setup("https://formspree.io/f/testform", async (_, options) => {
    const payload = JSON.parse(options.body);
    assert.equal(payload.subject, "CCF website | New inquiry");
    assert.equal(payload.language, "English");
    await new Promise(resolve => { finish = resolve; });
    return { ok: true, json: async () => ({ ok: true }) };
  }, "en");
  const submitted = page.submit();
  assert.equal(page.button.textContent, "Sending…");
  assert.match(page.status.textContent, /Sending your inquiry/);
  finish();
  await submitted;
  assert.match(page.status.textContent, /Your inquiry has been sent/);
  assert.equal(page.button.textContent, "Sent ✓");
  assert.equal(page.resets(), 1);
});

test("English network errors preserve the form and show English feedback", async () => {
  const page = setup("https://formspree.io/f/testform", async () => { throw new TypeError("network"); }, "en");
  await page.submit();
  assert.match(page.status.textContent, /Unable to connect/);
  assert.equal(page.button.textContent, "Send a free inquiry");
  assert.equal(page.resets(), 0);
});
