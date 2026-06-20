/* پنل خریدار — مدیریت پروژه‌ها، RFQ هوشمند و مقایسه پیشنهادات */
(function () {
  let PROJECTS = [];
  let lastParsed = null;
  let chatLog = [];

  function statBlock(projects) {
    const openRfqs = projects.reduce((s, p) => s + p.rfqs.filter((r) => r.status === "open").length, 0);
    const newQuotes = projects.reduce((s, p) => s + p.rfqs.reduce((sq, r) => sq + r.quotes.length, 0), 0);
    const saved = Math.round(newQuotes * 4.2);
    window.Motion.animateValue(document.getElementById("statActiveProjects"), projects.length);
    window.Motion.animateValue(document.getElementById("statOpenRfqs"), openRfqs);
    window.Motion.animateValue(document.getElementById("statQuotes"), newQuotes);
    window.Motion.animateValue(document.getElementById("statSaved"), saved, { format: (v) => `${fmtNum(Math.round(v))}M` });
  }

  function renderBomMini(bom) {
    const rows = bom
      .map(
        (item) => `
        <tr>
          <td>${window.I18N.pick(item.material)}</td>
          <td>${typeof item.spec === "object" ? window.I18N.pick(item.spec) : item.spec}</td>
          <td>${fmtNum(item.qty)} ${window.I18N.pick(item.unit)}</td>
        </tr>`
      )
      .join("");
    return `<table class="bom-mini-table"><tbody>${rows}</tbody></table>`;
  }

  function renderRfqRows(project) {
    return project.rfqs
      .map((rfq) => {
        const isOpen = rfq.status === "open";
        const badge = isOpen
          ? `<span class="badge badge-primary">${window.I18N.t("dashboard.rfq_status_open")}</span>`
          : `<span class="badge badge-success">${window.I18N.t("dashboard.rfq_status_closed")}</span>`;
        return `
        <div class="rfq-row">
          <div class="rfq-row-info">
            ${badge}
            <strong>${window.I18N.pick(rfq.title)}</strong>
            <span class="faint">(${rfq.quotes.length} ${window.I18N.t("dashboard.th_supplier")})</span>
          </div>
          <button class="btn btn-outline btn-sm" data-view-quotes="${project.id}:${rfq.id}">
            ${window.I18N.t("dashboard.view_quotes")}
          </button>
        </div>`;
      })
      .join("");
  }

  function renderProjects() {
    const wrap = document.getElementById("projectsList");
    wrap.innerHTML = PROJECTS.map(
      (p) => `
      <div class="project-card spot-card" data-reveal>
        <div class="project-card-head">
          <div>
            <h3>${window.I18N.pick(p.name)}</h3>
            <div class="project-meta">
              <span>📍 ${window.I18N.pick(p.city)}</span>
              <span>${p.bom.length} ${window.I18N.t("dashboard.bom_title")}</span>
            </div>
          </div>
          <span class="badge badge-amber">${p.progress}%</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:${p.progress}%"></div></div>
        <p class="muted" style="font-size:12.5px;margin-top:6px">${window.I18N.t("dashboard.progress_label")}</p>
        ${renderBomMini(p.bom)}
        ${renderRfqRows(p)}
      </div>`
    ).join("");

    wrap.querySelectorAll("[data-view-quotes]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const [pid, rid] = btn.dataset.viewQuotes.split(":").map(Number);
        openQuotesModal(pid, rid);
      });
    });
    window.Motion.refresh(wrap);
  }

  function openQuotesModal(pid, rid) {
    const project = PROJECTS.find((p) => p.id === pid);
    const rfq = project.rfqs.find((r) => r.id === rid);
    document.getElementById("quotesModalTitle").textContent = `${window.I18N.t("dashboard.quotes_modal_title")} — ${window.I18N.pick(rfq.title)}`;
    const tbody = document.getElementById("quotesBody");
    tbody.innerHTML = rfq.quotes
      .map(
        (q) => `
        <tr class="${q.selected ? "row-selected" : ""}">
          <td><div class="avatar-chip"><span class="dot">${window.I18N.pick(q.supplier).slice(0, 1)}</span>${window.I18N.pick(q.supplier)}</div></td>
          <td><strong>${fmtNum(q.price)}</strong> ${window.I18N.t("common.toman")}</td>
          <td>${window.I18N.pick(q.payment_terms)}</td>
          <td>${q.delivery_days} ${window.I18N.t("dashboard.day_unit")}</td>
          <td class="stars">★ ${q.rating}</td>
          <td>${
            q.selected
              ? `<span class="badge badge-success">${window.I18N.t("dashboard.selected_badge")}</span>`
              : `<button class="btn btn-primary btn-sm" data-select-quote="${q.id}">${window.I18N.t("dashboard.select_quote")}</button>`
          }</td>
        </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-select-quote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await fetchJSON(`/api/projects/${pid}/rfqs/${rid}/select`, {
            method: "POST",
            body: JSON.stringify({ quote_id: Number(btn.dataset.selectQuote) }),
          });
          toast(window.I18N.t("dashboard.toast_quote_selected"), "success");
          closeModal("quotesModal");
          await loadProjects();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });

    openModal("quotesModal");
  }

  async function loadProjects() {
    PROJECTS = await fetchJSON("/api/projects");
    statBlock(PROJECTS);
    renderProjects();
  }

  function renderBomPreview(parsed) {
    lastParsed = parsed;
    document.getElementById("newRfqPreview").classList.remove("hidden");
    document.getElementById("newRfqCity").textContent = parsed.city ? window.I18N.pick(parsed.city) : "—";
    const tbody = document.getElementById("newRfqBomBody");
    tbody.innerHTML = parsed.bom
      .map(
        (item) => `
        <tr>
          <td>${window.I18N.pick(item.material)}</td>
          <td>${typeof item.spec === "object" ? window.I18N.pick(item.spec) : item.spec}</td>
          <td><input type="number" step="0.1" value="${item.qty}" data-id="${item.id}" /></td>
          <td>${window.I18N.pick(item.unit)}</td>
        </tr>`
      )
      .join("");
  }

  async function analyzeNewRfq() {
    const text = document.getElementById("newRfqText").value.trim();
    if (!text) return;
    const parsed = await fetchJSON("/api/rfq/parse", { method: "POST", body: JSON.stringify({ text }) });
    renderBomPreview(parsed);
  }

  async function createNewRfq() {
    if (!lastParsed) {
      await analyzeNewRfq();
      if (!lastParsed) return;
    }
    const inputs = document.querySelectorAll("#newRfqBomBody input[data-id]");
    const bom = lastParsed.bom.map((item, idx) => ({ ...item, qty: parseFloat(inputs[idx]?.value) || item.qty }));
    try {
      await fetchJSON("/api/rfq", {
        method: "POST",
        body: JSON.stringify({ text: document.getElementById("newRfqText").value, bom, city: lastParsed.city }),
      });
      toast(window.I18N.t("dashboard.toast_rfq_created"), "success");
      closeModal("newRfqModal");
      document.getElementById("newRfqText").value = "";
      document.getElementById("newRfqPreview").classList.add("hidden");
      lastParsed = null;
      await loadProjects();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function renderChat() {
    const thread = document.getElementById("chatThread");
    if (chatLog.length === 0) {
      thread.innerHTML = `<p class="faint" style="text-align:center;padding:20px 0">${window.I18N.t("dashboard.no_messages")}</p>`;
      return;
    }
    thread.innerHTML = chatLog
      .map((m) => `<div class="chat-bubble ${m.me ? "me" : ""}">${m.text}</div>`)
      .join("");
    thread.scrollTop = thread.scrollHeight;
  }

  function sendChat() {
    const input = document.getElementById("chatInput");
    const text = input.value.trim();
    if (!text) return;
    chatLog.push({ me: true, text });
    input.value = "";
    renderChat();
    setTimeout(() => {
      chatLog.push({ me: false, text: "ممنون، در حال بررسی موجودی هستیم و به‌زودی پاسخ می‌دهیم." });
      renderChat();
    }, 900);
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadProjects();
    renderChat();
    document.getElementById("newRfqBtn").addEventListener("click", () => openModal("newRfqModal"));
    document.getElementById("analyzeNewRfqBtn").addEventListener("click", analyzeNewRfq);
    document.getElementById("submitNewRfqBtn").addEventListener("click", createNewRfq);
    document.getElementById("chatSendBtn").addEventListener("click", sendChat);
    document.getElementById("chatInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendChat();
    });
  });

  document.addEventListener("i18n:changed", () => {
    if (PROJECTS.length) {
      statBlock(PROJECTS);
      renderProjects();
    }
    renderChat();
  });
})();
