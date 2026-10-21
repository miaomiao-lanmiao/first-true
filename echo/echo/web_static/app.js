"use strict";

const API = "";
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

let state = {
  sessions: [],
  skills: [],
  mcp: [],
  tasks: [],
  activeSession: null,
  stream: null,
  editingSkill: null,
  editingMcp: null,
};

const THEMES = ["groknight", "tokyonight", "rosepine", "oscura"];
const THEME_NAMES = { groknight: "GrokNight", tokyonight: "TokyoNight", rosepine: "RosePine", oscura: "Oscura" };
const voiceState = { enabled: false, voice: "", rate: 1, lang: "zh-CN",
  ttsEngine: "browser", ttsEndpoint: "", ttsKey: "",
  sttEngine: "browser", sttEndpoint: "", sttKey: "" };
const appState = { avatar: "" };
let PROVIDERS = [];

/* ---------------- init ---------------- */
async function init() {
  const t = localStorage.getItem("echo-theme");
  if (t) document.body.dataset.theme = t;

  await loadConfig();
  await loadSessions();
  await loadSkills();
  await loadMcp();

  bindEvents();
  $("#chatScroll").addEventListener("scroll", () => {});
}

async function loadConfig() {
  const cfg = await fetchJSON("/api/config");
  if (cfg && cfg.theme && THEMES.includes(cfg.theme)) document.body.dataset.theme = cfg.theme;
  const ms = $("#modelSelect");
  ms.innerHTML = "";
  (cfg.models || []).forEach((m) => {
    const o = document.createElement("option");
    o.value = typeof m === "string" ? m : m.id; o.textContent = typeof m === "string" ? m : m.name; ms.appendChild(o);
  });
  if (cfg.model && [...ms.options].some((o) => o.value === cfg.model)) ms.value = cfg.model;
  PROVIDERS = cfg.providers || [];
  await loadProvidersForSettings(PROVIDERS);
  voiceState.enabled = !!(cfg.tts_enabled);
  voiceState.voice = cfg.tts_voice || "";
  voiceState.rate = cfg.tts_rate || 1;
  voiceState.lang = cfg.stt_lang || "zh-CN";
  voiceState.ttsEngine = cfg.tts_engine || "browser";
  voiceState.ttsEndpoint = cfg.tts_endpoint || "";
  voiceState.sttEngine = cfg.stt_engine || "browser";
  voiceState.sttEndpoint = cfg.stt_endpoint || "";
  appState.avatar = cfg.avatar || "";
  applyAvatar();
  document.body.dataset.tts = voiceState.ttsEngine;
  document.body.dataset.stt = voiceState.sttEngine;
  updateVoiceToggle();
  initVoice();
  await loadTasks();
}
function applyAvatar() {
  document.querySelectorAll(".msg.assistant .avatar").forEach((el) => {
    if (appState.avatar) { el.style.backgroundImage = `url("${appState.avatar}")`; el.classList.add("has-img"); }
    else { el.style.backgroundImage = ""; el.classList.remove("has-img"); }
  });
}

async function loadProvidersForSettings(providers) {
  const psel = $("#setProvider");
  psel.innerHTML = "";
  providers.forEach((p) => {
    const o = document.createElement("option"); o.value = p.id; o.textContent = p.name; psel.appendChild(o);
  });
  const msel = $("#setModel");
  msel.innerHTML = "";
  const allModels = (providers.flatMap((p) => p.models || []) || []);
  allModels.forEach((m) => {
    const o = document.createElement("option"); o.value = typeof m === "string" ? m : m.id; o.textContent = typeof m === "string" ? m : m.name; msel.appendChild(o);
  });
}

async function loadSessions() {
  state.sessions = (await fetchJSON("/api/sessions")) || [];
  renderSessions();
}

async function loadSkills() {
  state.skills = (await fetchJSON("/api/skills")) || [];
  renderSkills();
  $("#skillCount").textContent = `${state.skills.filter((s) => s.enabled).length} 个技能`;
}

async function loadMcp() {
  state.mcp = (await fetchJSON("/api/mcp")) || [];
  renderMcp();
  $("#mcpCount").textContent = `${state.mcp.filter((m) => m.enabled).length} 个 MCP`;
}

/* ---------------- render ---------------- */
function renderSessions() {
  const list = $("#sessionList");
  list.innerHTML = "";
  if (!state.sessions.length) {
    list.innerHTML = `<div class="empty-hint">还没有会话，点 ＋ 新建</div>`;
    return;
  }
  state.sessions.forEach((s) => {
    const el = document.createElement("div");
    el.className = "session-item" + (s.id === state.activeSession ? " active" : "");
    el.innerHTML = `<span class="session-title">${esc(s.title || "新会话")}</span>
      <button class="session-del" title="删除">🗑</button>`;
    el.querySelector(".session-title").onclick = () => openSession(s.id);
    el.querySelector(".session-del").onclick = (e) => { e.stopPropagation(); delSession(s.id); };
    list.appendChild(el);
  });
}

function renderSkills() {
  const list = $("#skillList");
  list.innerHTML = "";
  $("#skillsTotal").textContent = `技能库 (${state.skills.length})`;
  if (!state.skills.length) {
    list.innerHTML = `<div class="empty-hint">暂无技能，点 ＋ 创建</div>`;
    return;
  }
  state.skills.forEach((s) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-top">
        <span class="card-name">${esc(s.name)} ${s.enabled ? '<span class="card-badge">启用</span>' : ""}</span>
        <label class="switch"><input type="checkbox" ${s.enabled ? "checked" : ""}><span class="slider"></span></label>
      </div>
      <p class="card-desc">${esc(s.description || "")}</p>
      <div class="card-actions">
        <button class="card-btn edit">编辑</button>
        <button class="card-btn danger del">删除</button>
      </div>`;
    card.querySelector("input").onchange = (e) => toggleSkill(s.id, e.target.checked);
    card.querySelector(".edit").onclick = () => openSkillModal(s);
    card.querySelector(".del").onclick = () => delSkill(s.id);
    list.appendChild(card);
  });
}

function renderMcp() {
  const list = $("#mcpList");
  list.innerHTML = "";
  $("#mcpTotal").textContent = `MCP 服务器 (${state.mcp.length})`;
  if (!state.mcp.length) {
    list.innerHTML = `<div class="empty-hint">暂无 MCP 服务器，点 ＋ 添加</div>`;
    return;
  }
  state.mcp.forEach((m) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-top">
        <span class="card-name"><span class="status-dot ${m.enabled ? "on" : ""}"></span>${esc(m.name)}</span>
        <label class="switch"><input type="checkbox" ${m.enabled ? "checked" : ""}><span class="slider"></span></label>
      </div>
      <p class="mcp-url">${esc(m.url || "")}</p>
      <div class="card-actions">
        <button class="card-btn edit">编辑</button>
        <button class="card-btn danger del">删除</button>
      </div>`;
    card.querySelector("input").onchange = (e) => toggleMcp(m.id, e.target.checked);
    card.querySelector(".edit").onclick = () => openMcpModal(m);
    card.querySelector(".del").onclick = () => delMcp(m.id);
    list.appendChild(card);
  });
}

/* ---------------- chat ---------------- */
function addMessage(role, html) {
  $("#emptyState").style.display = "none";
  const wrap = $("#messages");
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = `<div class="avatar">${role === "user" ? "你" : "E"}</div>
    <div class="msg-body"><div class="msg-role">${role === "user" ? "You" : "Echo"}</div>
    <div class="msg-text">${html}</div></div>`;
  if (role === "assistant" && appState.avatar) {
    const av = el.querySelector(".avatar");
    av.style.backgroundImage = `url("${appState.avatar}")`;
    av.classList.add("has-img");
  }
  wrap.appendChild(el);
  return el.querySelector(".msg-text");
}
function addSpeakBtn(container) {
  if (container.querySelector(".msg-speak")) return;
  const btn = document.createElement("button");
  btn.className = "msg-speak";
  btn.textContent = "🔊 朗读";
  btn.onclick = () => {
    if (window.speechSynthesis && window.speechSynthesis.speaking) { stopSpeak(); return; }
    speak(container.innerText.replace("🔊 朗读", ""));
  };
  container.parentElement.appendChild(btn);
}

function showTyping() {
  $("#emptyState").style.display = "none";
  const wrap = $("#messages");
  const el = document.createElement("div");
  el.className = "msg assistant";
  el.id = "typingMsg";
  el.innerHTML = `<div class="avatar">E</div><div class="msg-body">
    <div class="msg-role">Echo</div><div class="typing"><span></span><span></span><span></span></div></div>`;
  wrap.appendChild(el);
  scrollChat();
}
function hideTyping() { const t = $("#typingMsg"); if (t) t.remove(); }

async function send() {
  const input = $("#input");
  const text = input.value.trim();
  if (!text || state.stream) return;
  input.value = ""; autoResize();
  stopSpeak();

  if (!state.activeSession) await newSession();

  const hist = currentHistory();
  hist.push({ role: "user", content: text });
  addMessage("user", esc(text).replace(/\n/g, "<br>"));
  showTyping();

  const btn = $("#sendBtn");
  btn.classList.add("stop"); btn.innerHTML = "■";
  setStatus("思考中…");

  const ctrl = new AbortController();
  state.stream = ctrl;
  document.body.classList.add("ai-active");
  let acc = "";
  try {
    const res = await fetch(API + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.activeSession, messages: hist, model: $("#modelSelect").value }),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (!data) continue;
        try {
          const j = JSON.parse(data);
          if (j.error) { acc += `\n\n⚠ ${j.error}`; }
          else acc += j.delta || "";
        } catch {}
        hideTyping();
        const target = ensureAssistant();
        target.innerHTML = renderMarkdown(acc);
        attachCopyButtons(target);
        highlightAll(target);
        scrollChat();
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      ensureAssistant().innerHTML = `<span style="color:var(--danger)">请求出错：${esc(e.message)}</span>`;
    }
  } finally {
    state.stream = null;
    btn.classList.remove("stop"); btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    hideTyping();
    setStatus("就绪");
    if (assistantEl) addSpeakBtn(assistantEl);
    await persistMessages(hist.concat({ role: "assistant", content: acc }));
    if (voiceState.enabled && acc && !acc.startsWith("⚠")) speak(acc);
    else document.body.classList.remove("ai-active");
  }
}

let assistantEl = null;
function ensureAssistant() {
  if (assistantEl && assistantEl.isConnected) return assistantEl;
  assistantEl = addMessage("assistant", "");
  return assistantEl;
}

function currentHistory() {
  const s = state.sessions.find((x) => x.id === state.activeSession);
  return s && s.messages ? s.messages.map((m) => ({ role: m.role, content: m.content })) : [];
}

async function persistMessages(messages) {
  await fetchJSON(`/api/sessions/${state.activeSession}/messages`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  const s = state.sessions.find((x) => x.id === state.activeSession);
  if (s) s.messages = messages;
}

function scrollChat() { const c = $("#chatScroll"); c.scrollTop = c.scrollHeight; }
function setStatus(t) { $("#statusText").textContent = t; }

/* ---------------- sessions ---------------- */
async function newSession() {
  const s = await fetchJSON("/api/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: "新会话" }) });
  state.sessions.unshift(s);
  state.activeSession = s.id;
  renderSessions();
  return s;
}
async function openSession(id) {
  if (state.stream) return;
  state.activeSession = id;
  assistantEl = null;
  const s = state.sessions.find((x) => x.id === id) || await fetchJSON(`/api/sessions/${id}`);
  $("#messages").innerHTML = "";
  $("#emptyState").style.display = s.messages && s.messages.length ? "none" : "flex";
  (s.messages || []).forEach((m) => {
    const el = addMessage(m.role, renderMarkdown(m.content));
    attachCopyButtons(el);
    highlightAll(el);
  });
  renderSessions();
}
async function delSession(id) {
  await fetch(`/api/sessions/${id}`, { method: "DELETE" });
  state.sessions = state.sessions.filter((s) => s.id !== id);
  if (state.activeSession === id) { state.activeSession = null; $("#messages").innerHTML = ""; $("#emptyState").style.display = "flex"; }
  renderSessions();
}

/* ---------------- skills ---------------- */
async function openSkillModal(skill) {
  state.editingSkill = skill ? skill.id : null;
  $("#skillModalTitle").textContent = skill ? "编辑技能" : "新建技能";
  $("#skillName").value = skill ? skill.name : "";
  $("#skillDesc").value = skill ? skill.description : "";
  $("#skillContent").value = skill ? skill.content : "";
  $("#deleteSkill").hidden = !skill;
  $("#skillModal").hidden = false;
}
async function saveSkill() {
  const name = $("#skillName").value.trim();
  if (!name) return alert("请填写名称");
  const body = { name, description: $("#skillDesc").value.trim(), content: $("#skillContent").value };
  let s;
  if (state.editingSkill) {
    s = await fetchJSON(`/api/skills/${state.editingSkill}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } else {
    s = await fetchJSON("/api/skills", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  await loadSkills();
  $("#skillModal").hidden = true;
}
async function delSkill(id) {
  if (!confirm("确定删除该技能？")) return;
  await fetch(`/api/skills/${id}`, { method: "DELETE" });
  if (state.editingSkill === id) $("#skillModal").hidden = true;
  await loadSkills();
}
async function toggleSkill(id, enabled) {
  await fetchJSON(`/api/skills/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
  await loadSkills();
}

/* ---------------- mcp ---------------- */
async function openMcpModal(m) {
  state.editingMcp = m ? m.id : null;
  $("#mcpModalTitle").textContent = m ? "编辑 MCP 服务器" : "新建 MCP 服务器";
  $("#mcpName").value = m ? m.name : "";
  $("#mcpUrl").value = m ? m.url : "";
  $("#mcpToken").value = "";
  $("#mcpToken").placeholder = m && m.token_set ? "已保存；留空保留，输入 clear 清除" : "可选令牌";
  $("#mcpEnabled").checked = m ? !!m.enabled : true;
  $("#deleteMcp").hidden = !m;
  $("#mcpModal").hidden = false;
}
async function saveMcp() {
  const name = $("#mcpName").value.trim();
  const url = $("#mcpUrl").value.trim();
  if (!name || !url) return alert("请填写名称和 URL");
  const body = { name, url, enabled: $("#mcpEnabled").checked };
  if ($("#mcpToken").value) body.token = $("#mcpToken").value;
  if (state.editingMcp) {
    await fetchJSON(`/api/mcp/${state.editingMcp}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } else {
    await fetchJSON("/api/mcp", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  await loadMcp();
  $("#mcpModal").hidden = true;
}
async function delMcp(id) {
  if (!confirm("确定删除该 MCP 服务器？")) return;
  await fetch(`/api/mcp/${id}`, { method: "DELETE" });
  if (state.editingMcp === id) $("#mcpModal").hidden = true;
  await loadMcp();
}
async function toggleMcp(id, enabled) {
  await fetchJSON(`/api/mcp/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
  await loadMcp();
}

/* ---------------- tasks ---------------- */
let editingTask = null;
async function loadTasks() {
  state.tasks = (await fetchJSON("/api/tasks")) || [];
  renderTasks();
}
function taskSchedText(t) {
  if (t.mode === "daily") return `每天 ${t.time || "09:00"}`;
  return `每 ${t.interval || 60} 分钟`;
}
function renderTasks() {
  const list = $("#taskList");
  list.innerHTML = "";
  $("#tasksTotal").textContent = `定时任务 (${state.tasks.length})`;
  if (!state.tasks.length) { list.innerHTML = `<div class="empty-hint">暂无任务，点 ＋ 新建</div>`; return; }
  state.tasks.forEach((t) => {
    const card = document.createElement("div");
    card.className = "task-card";
    const last = t.history && t.history[0];
    const lastTxt = t.last_run
      ? `上次：${new Date(t.last_run).toLocaleString()} ${last ? (last.ok ? "· <b>成功</b>" : "· 失败") : ""}${last ? " · " + esc(last.preview) : ""}` : "尚未运行";
    card.innerHTML = `
      <div class="tc-top">
        <span class="task-name">${esc(t.name)}</span>
        <label class="switch"><input type="checkbox" ${t.enabled ? "checked" : ""}><span class="slider"></span></label>
      </div>
      <div class="task-sched">⏰ ${taskSchedText(t)}</div>
      <div class="task-last">${lastTxt}</div>
      <div class="task-actions">
        <button class="tc-btn run">立即运行</button>
        <button class="tc-btn edit">编辑</button>
        <button class="tc-btn danger del">删除</button>
      </div>`;
    card.querySelector("input").onchange = (e) => toggleTask(t.id, e.target.checked);
    card.querySelector(".run").onclick = () => runTask(t.id);
    card.querySelector(".edit").onclick = () => openTaskModal(t);
    card.querySelector(".del").onclick = () => delTask(t.id);
    list.appendChild(card);
  });
}
function openTaskModal(t) {
  editingTask = t ? t.id : null;
  $("#taskModalTitle").textContent = t ? "编辑定时任务" : "新建定时任务";
  $("#taskName").value = t ? t.name : "";
  $("#taskPrompt").value = t ? t.prompt : "";
  $("#taskMode").value = t ? (t.mode || "interval") : "interval";
  $("#taskInterval").value = t ? (t.interval || 60) : 60;
  $("#taskTime").value = t ? (t.time || "09:00") : "09:00";
  $("#taskEnabled").checked = t ? !!t.enabled : true;
  document.body.dataset.taskmode = $("#taskMode").value;
  $("#deleteTask").hidden = !t;
  $("#taskModal").hidden = false;
}
async function saveTask() {
  const name = $("#taskName").value.trim();
  const prompt = $("#taskPrompt").value.trim();
  if (!name || !prompt) return alert("请填写名称和提示词");
  const body = {
    name, prompt,
    mode: $("#taskMode").value,
    interval: parseInt($("#taskInterval").value) || 60,
    time: $("#taskTime").value || "09:00",
    enabled: $("#taskEnabled").checked,
  };
  if (editingTask) await fetchJSON(`/api/tasks/${editingTask}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  else await fetchJSON("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  await loadTasks();
  $("#taskModal").hidden = true;
}
async function delTask(id) {
  if (!confirm("确定删除该任务？")) return;
  await fetch(`/api/tasks/${id}`, { method: "DELETE" });
  if (editingTask === id) $("#taskModal").hidden = true;
  await loadTasks();
}
async function toggleTask(id, enabled) {
  await fetchJSON(`/api/tasks/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
  await loadTasks();
}
async function runTask(id) {
  setStatus("任务运行中…");
  const t = await fetchJSON(`/api/tasks/${id}/run`, { method: "POST" });
  setStatus("就绪");
  if (t) await loadTasks();
}

/* ---------------- settings ---------------- */
async function openSettings() {
  const cfg = await fetchJSON("/api/config");
  PROVIDERS = cfg.providers || [];
  if (cfg.provider) $("#setProvider").value = cfg.provider;
  fillModelsForProvider(cfg.provider, cfg.model);
  $("#setKey").value = "";
  $("#setTts").checked = !!cfg.tts_enabled;
  $("#setTtsEngine").value = cfg.tts_engine || "browser";
  $("#setTtsEndpoint").value = cfg.tts_endpoint || "";
  $("#setTtsKey").value = "";
  $("#setTtsKey").placeholder = cfg.tts_api_key_set ? "已保存；本页直连语音需重新输入" : "语音服务密钥";
  $("#setTtsVoice").value = cfg.tts_voice || "";
  $("#setRate").value = cfg.tts_rate || 1;
  $("#setSttEngine").value = cfg.stt_engine || "browser";
  $("#setSttEndpoint").value = cfg.stt_endpoint || "";
  $("#setSttKey").value = "";
  $("#setSttKey").placeholder = cfg.stt_api_key_set ? "已保存；本页直连语音需重新输入" : "识别服务密钥";
  $("#setSttLang").value = cfg.stt_lang || "zh-CN";
  document.body.dataset.tts = cfg.tts_engine || "browser";
  document.body.dataset.stt = cfg.stt_engine || "browser";
  const vs = $("#setVoice");
  if (window.speechSynthesis && vs.options.length && cfg.tts_voice) {
    if ([...vs.options].some((o) => o.value === cfg.tts_voice)) vs.value = cfg.tts_voice;
  }
  $("#setAvatar").value = appState.avatar || "";
  renderAvatarPreview();
  $("#modalNote").textContent = "";
  $("#settingsModal").hidden = false;
}
function renderAvatarPreview() {
  const p = $("#avatarPreview");
  p.replaceChildren();
  if (appState.avatar) {
    const image = document.createElement("img");
    image.src = appState.avatar;
    image.alt = "avatar";
    p.appendChild(image);
  }
}
function fillModelsForProvider(providerId, selectedModel) {
  const sel = $("#setModel");
  sel.innerHTML = "";
  const p = PROVIDERS.find((x) => x.id === providerId) || PROVIDERS[0];
  (p ? p.models : []).forEach((m) => {
    const o = document.createElement("option"); o.value = m; o.textContent = m; sel.appendChild(o);
  });
  if (selectedModel && [...sel.options].some((o) => o.value === selectedModel)) sel.value = selectedModel;
}
async function saveSettings() {
  const body = { provider: $("#setProvider").value, model: $("#setModel").value };
  const key = $("#setKey").value.trim();
  if (key) body.api_key = key;
  body.tts_enabled = $("#setTts").checked;
  body.tts_voice = $("#setVoice").value;
  body.tts_rate = parseFloat($("#setRate").value) || 1;
  body.stt_lang = $("#setSttLang").value;
  body.tts_engine = $("#setTtsEngine").value;
  body.tts_endpoint = $("#setTtsEndpoint").value.trim();
  const ttsKey = $("#setTtsKey").value.trim();
  if (ttsKey) { body.tts_api_key = ttsKey; voiceState.ttsKey = ttsKey.toLowerCase() === "clear" ? "" : ttsKey; }
  body.tts_voice = $("#setTtsVoice").value.trim();
  body.stt_engine = $("#setSttEngine").value;
  body.stt_endpoint = $("#setSttEndpoint").value.trim();
  const sttKey = $("#setSttKey").value.trim();
  if (sttKey) { body.stt_api_key = sttKey; voiceState.sttKey = sttKey.toLowerCase() === "clear" ? "" : sttKey; }
  body.avatar = $("#setAvatar").value.trim();
  const r = await fetchJSON("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (r && r.status === "saved") $("#modalNote").textContent = "已保存 ✓";
  await loadConfig();
  setTimeout(() => { $("#settingsModal").hidden = true; }, 650);
}

/* ---------------- helpers ---------------- */
async function fetchJSON(url, opts) {
  try { const r = await fetch(API + url, opts); return await r.json(); }
  catch (e) { console.error(e); return null; }
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function autoResize() {
  const t = $("#input"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 180) + "px";
}
function renderMarkdown(md) {
  if (window.marked && window.DOMPurify) {
    try { return window.DOMPurify.sanitize(window.marked.parse(md || ""), { USE_PROFILES: { html: true } }); } catch {}
  }
  return esc(md).replace(/\n/g, "<br>");
}
function attachCopyButtons(scope) {
  scope.querySelectorAll("pre").forEach((pre) => {
    if (pre.dataset.copy) return;
    pre.dataset.copy = "1";
    const code = pre.querySelector("code");
    const lang = (code && code.className.match(/language-(\w+)/) || [, "code"])[1];
    const head = document.createElement("div");
    head.className = "code-head";
    head.innerHTML = `<span>${esc(lang)}</span>`;
    const btn = document.createElement("button");
    btn.className = "copy-btn"; btn.innerHTML = "复制";
    btn.onclick = () => {
      navigator.clipboard.writeText(code.textContent).then(() => {
        btn.textContent = "已复制 ✓"; setTimeout(() => (btn.textContent = "复制"), 1400);
      });
    };
    head.appendChild(btn);
    pre.insertBefore(head, pre.firstChild);
  });
}
function highlightAll(scope) {
  if (!window.hljs) return;
  scope.querySelectorAll("pre code").forEach((c) => {
    if (!c.dataset.hl) { try { window.hljs.highlightElement(c); c.dataset.hl = "1"; } catch {} }
  });
}

/* ---------------- voice (TTS + STT) ---------------- */
function stripMd(text) {
  return String(text || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`]*`/g, " ")
    .replace(/[#>*_~|-]/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}
function updateVoiceToggle() {
  const b = $("#voiceToggle");
  if (!b) return;
  b.classList.toggle("muted", !voiceState.enabled);
  b.textContent = voiceState.enabled ? "🔊" : "🔇";
}
function pickVoice() {
  if (!window.speechSynthesis) return null;
  const vs = window.speechSynthesis.getVoices();
  if (!vs.length) return null;
  if (voiceState.voice) {
    const v = vs.find((x) => x.name === voiceState.voice) || vs.find((x) => x.name.includes(voiceState.voice));
    if (v) return v;
  }
  const pref = voiceState.lang || "zh-CN";
  return vs.find((x) => x.lang === pref) || vs.find((x) => x.lang && x.lang.startsWith(pref.slice(0, 2))) || vs[0];
}
function speak(text) {
  if (!voiceState.enabled) return;
  stopSpeak();
  if (voiceState.ttsEngine === "custom") { speakCustom(stripMd(text)); return; }
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(stripMd(text));
  const v = pickVoice();
  if (v) u.voice = v;
  u.lang = voiceState.lang || "zh-CN";
  u.rate = voiceState.rate || 1;
  u.onstart = () => document.body.classList.add("ai-active");
  u.onend = () => document.body.classList.remove("ai-active");
  u.onerror = () => document.body.classList.remove("ai-active");
  window.speechSynthesis.speak(u);
}
async function speakCustom(text) {
  if (!voiceState.ttsEndpoint) { alert("请先在设置里填写自定义 TTS 的 API 地址"); return; }
  document.body.classList.add("ai-active");
  try {
    const headers = { "Content-Type": "application/json" };
    if (voiceState.ttsKey) headers["Authorization"] = `Bearer ${voiceState.ttsKey}`;
    const r = await fetch(voiceState.ttsEndpoint, {
      method: "POST", headers,
      body: JSON.stringify({ text, voice: voiceState.voice, lang: voiceState.lang, rate: voiceState.rate }),
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const ct = r.headers.get("content-type") || "";
    if (ct.includes("audio")) {
      const url = URL.createObjectURL(await r.blob());
      const a = new Audio(url);
      a.onended = () => { document.body.classList.remove("ai-active"); URL.revokeObjectURL(url); };
      await a.play();
    } else {
      const j = await r.json();
      const src = j.audio || j.url || j.data;
      if (!src) throw new Error("返回中未找到 audio/url 字段");
      const a = new Audio(src.startsWith("data:") ? src : (src.startsWith("http") ? src : (location.origin + src)));
      a.onended = () => document.body.classList.remove("ai-active");
      await a.play();
    }
  } catch (e) {
    document.body.classList.remove("ai-active");
    alert("自定义 TTS 调用失败：" + e.message);
  }
}
function stopSpeak() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  document.body.classList.remove("ai-active");
}
function toggleVoice() {
  voiceState.enabled = !voiceState.enabled;
  updateVoiceToggle();
  if (!voiceState.enabled) stopSpeak();
  saveVoiceSettings();
}
function saveVoiceSettings() {
  fetchJSON("/api/config", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tts_enabled: voiceState.enabled, tts_voice: voiceState.voice, tts_rate: voiceState.rate, stt_lang: voiceState.lang }),
  });
}
function initVoice() {
  if (!window.speechSynthesis) { const b = $("#voiceToggle"); if (b) b.style.display = "none"; }
  const fill = () => {
    const sel = $("#setVoice");
    if (!sel) return;
    const vs = window.speechSynthesis.getVoices();
    sel.innerHTML = "";
    vs.forEach((v, i) => {
      const o = document.createElement("option");
      o.value = v.name; o.textContent = `${v.name} · ${v.lang}`; sel.appendChild(o);
    });
    if (voiceState.voice && [...sel.options].some((o) => o.value === voiceState.voice)) sel.value = voiceState.voice;
  };
  if (window.speechSynthesis) {
    fill();
    window.speechSynthesis.onvoiceschanged = fill;
  }
  setupSTT();
}
function setupSTT() {
  const mb = $("#micBtn");
  if (!mb) return;
  if (voiceState.sttEngine === "custom") { setupCustomStt(mb); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { mb.style.display = "none"; return; }
  const rec = new SR();
  rec.lang = voiceState.lang || "zh-CN";
  rec.interimResults = true;
  rec.continuous = false;
  rec.onresult = (e) => {
    let interim = "", final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t; else interim += t;
    }
    const inp = $("#input");
    inp.value = final || interim;
    autoResize();
    if (final) {
      inp.value = final;
      mb.classList.remove("listening");
      document.body.classList.remove("listening");
      stopListen(rec);
      send();
    }
  };
  rec.onerror = (e) => {
    mb.classList.remove("listening"); document.body.classList.remove("listening");
    if (e.error === "not-allowed") alert("麦克风权限被拒绝");
  };
  rec.onend = () => { mb.classList.remove("listening"); document.body.classList.remove("listening"); };
  mb.onclick = () => {
    if (state.stream) return;
    if (mb.classList.contains("listening")) { stopListen(rec); return; }
    try {
      rec.lang = voiceState.lang || "zh-CN";
      rec.start();
      mb.classList.add("listening");
      document.body.classList.add("listening");
      setStatus("聆听中…说完自动发送");
    } catch {}
  };
}
function setupCustomStt(mb) {
  let media, recorder, chunks = [];
  const start = async () => {
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorder = new MediaRecorder(media);
      chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        media.stream.getTracks().forEach((t) => t.stop());
        sendAudioToStt(blob);
      };
      recorder.start();
      mb.classList.add("listening");
      document.body.classList.add("listening");
      setStatus("录音中…再点 🎤 结束并识别");
    } catch (e) { alert("无法访问麦克风：" + e.message); }
  };
  const stop = () => { try { recorder && recorder.state !== "inactive" && recorder.stop(); } catch {} };
  mb.onclick = () => {
    if (state.stream) return;
    if (mb.classList.contains("listening")) stop();
    else start();
  };
}
async function sendAudioToStt(blob) {
  if (!voiceState.sttEndpoint) { alert("请先在设置里填写自定义 STT 的 API 地址"); return; }
  setStatus("识别中…");
  try {
    const form = new FormData();
    form.append("file", blob, "speech.webm");
    form.append("lang", voiceState.lang || "zh-CN");
    const headers = {};
    if (voiceState.sttKey) headers["Authorization"] = `Bearer ${voiceState.sttKey}`;
    const r = await fetch(voiceState.sttEndpoint, { method: "POST", headers, body: form });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    const text = j.text || j.transcript || j.result || "";
    const inp = $("#input");
    inp.value = text;
    autoResize();
    if (text.trim()) send();
  } catch (e) {
    setStatus("就绪");
    alert("自定义 STT 调用失败：" + e.message);
  }
}
function stopListen(rec) { try { rec.stop(); } catch {} }

function bindEvents() {
  $("#sendBtn").onclick = () => { if (state.stream) { state.stream.abort(); setStatus("已停止"); } else send(); };
  $("#input").addEventListener("input", autoResize);
  $("#input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  $("#newChatBtn").onclick = newSession;
  $("#themeBtn").onclick = cycleTheme;
  $("#settingsBtn").onclick = openSettings;
  $("#voiceToggle").onclick = toggleVoice;
  $("#setTtsEngine").onchange = (e) => (document.body.dataset.tts = e.target.value);
  $("#setSttEngine").onchange = (e) => (document.body.dataset.stt = e.target.value);
  $("#setProvider").onchange = (e) => fillModelsForProvider(e.target.value, null);
  $("#toggleSidebar").onclick = () => $("#sidebar").classList.toggle("collapsed");
  $("#closeSettings").onclick = () => ($("#settingsModal").hidden = true);
  $("#cancelSettings").onclick = () => ($("#settingsModal").hidden = true);
  $("#saveSettings").onclick = saveSettings;
  $("#newSkillBtn").onclick = () => openSkillModal(null);
  $("#closeSkill").onclick = () => ($("#skillModal").hidden = true);
  $("#cancelSkill").onclick = () => ($("#skillModal").hidden = true);
  $("#saveSkill").onclick = saveSkill;
  $("#deleteSkill").onclick = () => delSkill(state.editingSkill);
  $("#newMcpBtn").onclick = () => openMcpModal(null);
  $("#closeMcp").onclick = () => ($("#mcpModal").hidden = true);
  $("#cancelMcp").onclick = () => ($("#mcpModal").hidden = true);
  $("#saveMcp").onclick = saveMcp;
  $("#deleteMcp").onclick = () => delMcp(state.editingMcp);
  $("#newTaskBtn").onclick = () => openTaskModal(null);
  $("#closeTask").onclick = () => ($("#taskModal").hidden = true);
  $("#cancelTask").onclick = () => ($("#taskModal").hidden = true);
  $("#saveTask").onclick = saveTask;
  $("#deleteTask").onclick = () => delTask(editingTask);
  $("#taskMode").onchange = (e) => (document.body.dataset.taskmode = e.target.value);
  $("#avatarUploadBtn").onclick = () => $("#avatarFile").click();
  $("#avatarFile").onchange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { appState.avatar = rd.result; $("#setAvatar").value = rd.result; renderAvatarPreview(); applyAvatar(); };
    rd.readAsDataURL(f);
  };
  $("#setAvatar").addEventListener("input", () => { appState.avatar = $("#setAvatar").value.trim(); renderAvatarPreview(); applyAvatar(); });
  $$(".tab").forEach((t) => t.onclick = () => {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    const tab = t.dataset.tab;
    $("#tabSkills").classList.toggle("hidden", tab !== "skills");
    $("#tabMcp").classList.toggle("hidden", tab !== "mcp");
    $("#tabTasks").classList.toggle("hidden", tab !== "tasks");
  });
  $$(".chip").forEach((c) => c.onclick = () => { $("#input").value = c.textContent; autoResize(); send(); });
  document.querySelectorAll(".modal-backdrop").forEach((b) => b.addEventListener("click", (e) => { if (e.target === b) b.hidden = true; }));
  $("#modelSelect").onchange = () => {
    fetchJSON("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model: $("#modelSelect").value }) });
  };
}
function cycleTheme() {
  const cur = document.body.dataset.theme;
  const next = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
  document.body.dataset.theme = next;
  localStorage.setItem("echo-theme", next);
  fetchJSON("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ theme: next }) });
}

init();
