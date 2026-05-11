// Sickle Cell RAG — frontend
const READY_KEY = "scrag.indexReady";

const $ = (id) => document.getElementById(id);

const els = {
  modelBadge: $("model-badge"),
  sourceBadge: $("source-badge"),
  welcomeRange: $("welcome-range"),
  initScreen: $("init-screen"),
  initBtn: $("init-btn"),
  initLog: $("init-log"),
  chatScreen: $("chat-screen"),
  chat: $("chat"),
  empty: $("empty"),
  composer: $("composer"),
  input: $("input"),
  send: $("send"),
};

let isStreaming = false;

// ---------- screen switching ----------
function showInit() {
  els.initScreen.hidden = false;
  els.chatScreen.hidden = true;
}

function showChat() {
  els.initScreen.hidden = true;
  els.chatScreen.hidden = false;
  setTimeout(() => els.input.focus(), 50);
}

// ---------- init log ----------
function appendInitLog(message) {
  els.initLog.hidden = false;
  // Mark previous active item as done
  const prev = els.initLog.querySelector("li.active");
  if (prev) {
    prev.classList.remove("active");
    prev.classList.add("done");
  }
  const li = document.createElement("li");
  li.className = "active";
  li.textContent = message;
  els.initLog.appendChild(li);
  els.initLog.scrollTop = els.initLog.scrollHeight;
  return li;
}

function markLastDone() {
  const last = els.initLog.querySelector("li.active");
  if (last) {
    last.classList.remove("active");
    last.classList.add("done");
  }
}

function markLastError(message) {
  const last = els.initLog.querySelector("li.active");
  if (last) {
    last.classList.remove("active");
    last.classList.add("error");
    last.textContent = message;
  } else {
    const li = document.createElement("li");
    li.className = "error";
    li.textContent = message;
    els.initLog.appendChild(li);
  }
}

// ---------- chat helpers ----------
function linkifyCitations(text) {
  return text.replace(/\[(PMC\d+)\]/g, (_, id) =>
    `<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/${id}/" target="_blank" rel="noopener">[${id}]</a>`
  );
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function leaveEmptyState() {
  if (els.chatScreen.dataset.empty === "true") {
    els.chatScreen.dataset.empty = "false";
    if (els.empty) {
      els.empty.remove();
      els.empty = null;
    }
  }
}

function addMessage(role, text) {
  leaveEmptyState();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  els.chat.appendChild(wrap);
  scrollToBottom();
  return bubble;
}

function addErrorMessage(text) {
  const el = document.createElement("div");
  el.className = "error-msg";
  el.textContent = text;
  els.chat.appendChild(el);
  scrollToBottom();
}

function scrollToBottom() {
  els.chat.scrollTop = els.chat.scrollHeight;
}

function autoresize() {
  els.input.style.height = "auto";
  els.input.style.height = Math.min(els.input.scrollHeight, 200) + "px";
}

// ---------- SSE parsing ----------
async function* sseStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const data = line.slice(6);
      if (data === "[DONE]") return;
      try {
        yield JSON.parse(data);
      } catch (e) {
        console.warn("SSE parse error:", data);
      }
    }
  }
}

// ---------- status / init ----------
async function checkStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("status failed");
    return await res.json();
  } catch (e) {
    return { ready: false, model: "?", has_api_key: false, indexing: false };
  }
}

async function runInit() {
  els.initBtn.disabled = true;
  els.initBtn.textContent = "Inicializando…";
  els.initLog.innerHTML = "";
  els.initLog.hidden = false;

  try {
    const res = await fetch("/api/init", { method: "POST" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    let sawDone = false;
    for await (const ev of sseStream(res)) {
      if (ev.stage === "error") {
        markLastError(ev.message);
        throw new Error(ev.message);
      }
      appendInitLog(`[${ev.stage}] ${ev.message}`);
      if (ev.stage === "done") {
        markLastDone();
        sawDone = true;
        localStorage.setItem(READY_KEY, "1");
        els.initBtn.textContent = "Listo";
        setTimeout(showChat, 700);
        return;
      }
    }
    if (!sawDone) {
      markLastDone();
      localStorage.setItem(READY_KEY, "1");
      setTimeout(showChat, 400);
    }
  } catch (e) {
    if (!els.initLog.querySelector("li.error")) markLastError(`Error: ${e.message}`);
    els.initBtn.disabled = false;
    els.initBtn.textContent = "Reintentar";
  }
}

// ---------- chat ----------
async function sendMessage(text) {
  if (isStreaming || !text.trim()) return;
  isStreaming = true;
  els.send.disabled = true;
  els.input.disabled = true;

  addMessage("user", text);
  const bubble = addMessage("assistant", "");
  const cursor = document.createElement("span");
  cursor.className = "cursor";
  bubble.appendChild(cursor);

  let buffer = "";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    for await (const ev of sseStream(res)) {
      if (ev.error) throw new Error(ev.error);
      if (ev.token) {
        buffer += ev.token;
        bubble.innerHTML = linkifyCitations(escapeHtml(buffer));
        bubble.appendChild(cursor);
        scrollToBottom();
      }
    }
    cursor.remove();
    bubble.innerHTML = linkifyCitations(escapeHtml(buffer));
  } catch (e) {
    cursor.remove();
    if (!buffer) bubble.parentElement.remove();
    addErrorMessage(`Error: ${e.message}`);
    if (/index not ready/i.test(e.message)) {
      localStorage.removeItem(READY_KEY);
      showInit();
    }
  } finally {
    isStreaming = false;
    els.send.disabled = false;
    els.input.disabled = false;
    els.input.value = "";
    autoresize();
    els.input.focus();
  }
}

// ---------- wire up ----------
function wireUp() {
  els.composer.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(els.input.value);
  });

  els.input.addEventListener("input", autoresize);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(els.input.value);
    }
  });

  document.querySelectorAll(".suggestion").forEach((btn) => {
    btn.addEventListener("click", () => sendMessage(btn.textContent));
  });

  els.initBtn.addEventListener("click", runInit);
}

async function boot() {
  wireUp();
  const status = await checkStatus();
  els.modelBadge.textContent = status.model || "?";
  if (status.date_min && status.date_max) {
    const range = `${status.date_min}–${status.date_max}`;
    els.sourceBadge.textContent = `PMC · ${range}`;
    if (els.welcomeRange) els.welcomeRange.textContent = range;
  }

  if (status.ready) {
    localStorage.setItem(READY_KEY, "1");
    showChat();
  } else {
    localStorage.removeItem(READY_KEY);
    showInit();
    if (status.indexing) {
      els.initBtn.disabled = true;
      els.initBtn.textContent = "Indexando en otra sesión…";
    }
  }
}

boot();
