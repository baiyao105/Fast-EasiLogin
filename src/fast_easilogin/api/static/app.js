const $ = (sel) => document.querySelector(sel);

function setStatus(msg, isErr) {
  const el = $("#status");
  el.textContent = msg;
  el.className = isErr ? "err" : "";
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const err = new Error(res.statusText || "请求失败");
    err.status = res.status;
    err.body = data;
    throw err;
  }
  return data;
}

function renderList(rows) {
  const ul = $("#account-list");
  const empty = $("#list-empty");
  ul.innerHTML = "";
  if (!rows.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  for (const r of rows) {
    const li = document.createElement("li");
    li.className = "account-item";
    const img = document.createElement("img");
    img.src = r.pt_photourl || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E";
    img.alt = "";
    img.referrerPolicy = "no-referrer";
    const meta = document.createElement("div");
    meta.className = "account-meta";
    meta.innerHTML = `<strong>${escapeHtml(r.pt_nickname || r.pt_userid)}</strong><span>${escapeHtml(
      r.pt_userid,
    )}</span>`;
    const uid = encodeURIComponent(r.pt_userid);
    const loginBtn = document.createElement("a");
    loginBtn.className = "btn small primary";
    loginBtn.href = `/getData/SSOLOGIN/${uid}`;
    loginBtn.target = "_blank";
    loginBtn.rel = "noopener noreferrer";
    loginBtn.textContent = "SSO 登录";
    li.append(img, meta, loginBtn);
    ul.appendChild(li);
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

async function loadAccounts() {
  setStatus("加载列表…");
  try {
    const j = await api("/getData/SSOLOGIN");
    const rows = j.data || [];
    renderList(rows);
    setStatus(`已加载 ${rows.length} 个账号`);
  } catch (e) {
    setStatus(`列表失败: ${e.message}`, true);
  }
}

$("#btn-refresh").addEventListener("click", loadAccounts);

$("#form-save").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const body = {
    userid: String(fd.get("userid") || "").trim(),
    password: String(fd.get("password") || ""),
  };
  const out = $("#save-out");
  out.hidden = false;
  out.textContent = "提交中…";
  try {
    const j = await api("/savedata", { method: "POST", body: JSON.stringify(body) });
    out.textContent = JSON.stringify(j, null, 2);
    setStatus("账号已保存");
    await loadAccounts();
  } catch (e) {
    out.textContent = JSON.stringify(e.body || { error: e.message }, null, 2);
    setStatus(`保存失败: ${e.message}`, true);
  }
});

$("#form-info").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const fieldsRaw = String(fd.get("fields") || "").trim();
  const fields = fieldsRaw
    ? fieldsRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : null;
  const body = {
    user_id: String(fd.get("user_id") || "").trim(),
    password: String(fd.get("password") || ""),
    fields,
  };
  const out = $("#info-out");
  out.hidden = false;
  out.textContent = "查询中…";
  try {
    const j = await api("/user/info", { method: "POST", body: JSON.stringify(body) });
    out.textContent = JSON.stringify(j.data ?? j, null, 2);
    setStatus("查询完成");
  } catch (e) {
    out.textContent = JSON.stringify(e.body || { error: e.message }, null, 2);
    setStatus(`查询失败: ${e.message}`, true);
  }
});

loadAccounts();
