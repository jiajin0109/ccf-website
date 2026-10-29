(() => {
  "use strict";
  const form = document.getElementById("contact-form");
  if (!form) return;
  const status = document.getElementById("contact-status");
  const button = form.querySelector('button[type="submit"]');
  const buttonLabel = button.textContent;
  let sending = false;
  const show = (message, success = false) => {
    status.textContent = message;
    status.className = success ? "ok" : "flash";
    status.hidden = false;
    status.setAttribute("role", success ? "status" : "alert");
    status.focus({ preventScroll: true });
    status.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending || !form.reportValidity()) return;
    const endpoint = window.CCF_CONFIG?.contactEndpoint;
    if (!endpoint) {
      show("諮詢表單尚未開通，請先透過 LINE 聯絡我們。");
      return;
    }
    if (!/^https:\/\/formspree\.io\/f\/[a-zA-Z0-9]+$/.test(endpoint)) {
      show("諮詢表單設定有誤，請先透過 LINE 聯絡我們。");
      return;
    }
    const values = new FormData(form);
    const payload = Object.fromEntries(["name", "contact", "need", "_gotcha"].map(
      (name) => [name, String(values.get(name) || "").trim()]
    ));
    payload.subject = "CCF 官網｜新客戶諮詢";
    if (!payload.contact) {
      show("請留下電話或 LINE ID，我們才能聯繫你。");
      return;
    }
    sending = true;
    let delivered = false;
    button.disabled = true;
    button.textContent = "傳送中…";
    form.setAttribute("aria-busy", "true");
    status.textContent = "正在送出你的諮詢，請稍候…";
    status.className = "pending";
    status.setAttribute("role", "status");
    status.hidden = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload),
        credentials: "omit",
        signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok || result.ok === false || result.errors?.length) {
        if (response.status === 429) {
          throw new Error("表單目前無法受理，請稍後再試，或直接加 LINE 聯絡我們。");
        }
        const errors = Array.isArray(result.errors)
          ? result.errors.map(error => error.message).filter(message => typeof message === "string").join("；")
          : "";
        throw new Error(errors || "傳送失敗，請稍後再試，或直接加 LINE 聯絡我們。");
      }
      form.reset();
      delivered = true;
      show("✓ 諮詢已成功送出！\n" + (form.dataset.thanks || "我們已收到你的需求，會盡快與你聯繫。"), true);
    } catch (error) {
      show(error.name === "AbortError"
        ? "連線逾時，無法確認是否送達。請透過 LINE 確認，避免重複送出。"
        : error instanceof TypeError
          ? "目前無法連線，請稍後再試，或直接加 LINE 聯絡我們。"
          : error.message);
    } finally {
      clearTimeout(timeout);
      button.disabled = false;
      button.textContent = delivered ? "已送出 ✓" : buttonLabel;
      form.setAttribute("aria-busy", "false");
      sending = false;
    }
  });
})();
