/* پنل فروشنده — فید استعلام زنده، قیمت‌دهی سریع، موجودی و گزارش فروش */
(function () {
  let FEED = [];
  let salesChart = null;
  const quotedIds = new Set();

  function fmtCountdown(seconds) {
    if (seconds <= 0) return "00:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function renderFeed() {
    const wrap = document.getElementById("feedList");
    if (FEED.length === 0) {
      wrap.innerHTML = `<p class="faint" style="text-align:center;padding:30px 0">${window.I18N.t("supplier.no_feed")}</p>`;
      return;
    }
    wrap.innerHTML = FEED.map((item) => {
      const remaining = Math.max(0, Math.round(item.deadline_ts - Date.now() / 1000));
      const urgent = remaining < 300;
      const quoted = quotedIds.has(item.id);
      return `
      <div class="project-card" data-feed-card="${item.id}">
        <div class="project-card-head">
          <div>
            <h3>${window.I18N.pick(item.material)} — ${window.I18N.pick(item.project)}</h3>
            <div class="project-meta">
              <span>📍 ${window.I18N.pick(item.city)}</span>
              <span>${fmtNum(item.qty)} ${window.I18N.pick(item.unit)}</span>
              <span>${item.quote_count} ${window.I18N.t("dashboard.th_supplier")}</span>
            </div>
          </div>
          <span class="badge ${urgent ? "badge-danger" : "badge-primary"}">
            ${window.I18N.t("supplier.deadline_prefix")}
            <span class="countdown ${urgent ? "urgent" : ""}" data-countdown="${item.id}" data-deadline="${item.deadline_ts}">${fmtCountdown(remaining)}</span>
          </span>
        </div>

        ${quoted
          ? `<div style="margin-top:14px"><span class="badge badge-success">✓ ${window.I18N.t("supplier.quote_sent")}</span></div>`
          : `
          <div class="quick-quote-form" style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
            <div class="field" style="margin:0;flex:1;min-width:140px">
              <label>${window.I18N.t("supplier.quote_form_price")}</label>
              <input type="number" data-price="${item.id}" placeholder="0" />
            </div>
            <div class="field" style="margin:0;width:110px">
              <label>${window.I18N.t("supplier.quote_form_delivery")}</label>
              <input type="number" data-delivery="${item.id}" placeholder="5" />
            </div>
            <button class="btn btn-accent btn-sm" data-submit-quote="${item.id}">${window.I18N.t("supplier.submit_quote")}</button>
          </div>`
        }
      </div>`;
    }).join("");

    wrap.querySelectorAll("[data-submit-quote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.submitQuote);
        const price = document.querySelector(`[data-price="${id}"]`).value;
        const delivery = document.querySelector(`[data-delivery="${id}"]`).value || 5;
        if (!price) {
          toast(window.I18N.t("supplier.quote_form_price"), "error");
          return;
        }
        try {
          await fetchJSON("/api/supplier/quote", {
            method: "POST",
            body: JSON.stringify({ rfq_id: id, price, delivery_days: delivery }),
          });
          quotedIds.add(id);
          toast(window.I18N.t("supplier.toast_quote_sent"), "success");
          renderFeed();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  }

  function tickCountdowns() {
    document.querySelectorAll("[data-countdown]").forEach((el) => {
      const deadline = Number(el.dataset.deadline);
      const remaining = Math.max(0, Math.round(deadline - Date.now() / 1000));
      el.textContent = fmtCountdown(remaining);
      el.classList.toggle("urgent", remaining < 300);
      el.closest(".badge")?.classList.toggle("badge-danger", remaining < 300);
      el.closest(".badge")?.classList.toggle("badge-primary", remaining >= 300);
    });
  }

  async function loadFeed() {
    const city = document.getElementById("cityFilter").value;
    const url = city ? `/api/supplier/feed?city=${encodeURIComponent(city)}` : "/api/supplier/feed";
    let feed = await fetchJSON(url);
    const productFilter = document.getElementById("categoryFilter").value;
    if (productFilter) {
      feed = feed.filter((f) => window.I18N.pick(f.material) === productFilter);
    }
    FEED = feed;
    document.getElementById("statOpen").textContent = FEED.length;
    renderFeed();
  }

  async function loadCityFilter() {
    const cities = await fetchJSON("/api/cities");
    const sel = document.getElementById("cityFilter");
    sel.innerHTML = `<option value="">${window.I18N.t("supplier.filter_city")}</option>` + cities.map((c) => `<option value="${c.fa}">${window.I18N.pick(c)}</option>`).join("");
  }

  function loadProductFilterOptions() {
    const materials = [...new Set(FEED.map((f) => window.I18N.pick(f.material)))];
    const sel = document.getElementById("categoryFilter");
    const current = sel.value;
    sel.innerHTML = `<option value="">${window.I18N.t("supplier.filter_category")}</option>` + materials.map((m) => `<option value="${m}">${m}</option>`).join("");
    sel.value = materials.includes(current) ? current : "";
  }

  async function loadInventory() {
    const inv = await fetchJSON("/api/supplier/inventory");
    const tbody = document.getElementById("inventoryBody");
    tbody.innerHTML = inv
      .map(
        (item) => `
        <tr>
          <td>${window.I18N.pick(item.material)}</td>
          <td>${item.spec}</td>
          <td>${fmtNum(item.stock)} ${window.I18N.pick(item.unit)}</td>
          <td>${fmtNum(item.base_price)} ${window.I18N.t("common.toman")}</td>
        </tr>`
      )
      .join("");
  }

  async function loadSalesChart() {
    const data = await fetchJSON("/api/supplier/sales");
    const ctx = document.getElementById("salesChart").getContext("2d");
    if (salesChart) salesChart.destroy();
    salesChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.series.map((_, i) => i + 1),
        datasets: [{ data: data.series, backgroundColor: "#f0a324", borderRadius: 6, barThickness: 14 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } },
      },
    });
    document.getElementById("statSales").textContent = `${fmtNum(data.series[data.series.length - 1])}M`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await loadCityFilter();
    await loadFeed();
    loadProductFilterOptions();
    loadInventory();
    loadSalesChart();
    setInterval(tickCountdowns, 1000);

    document.getElementById("cityFilter").addEventListener("change", async () => {
      await loadFeed();
      loadProductFilterOptions();
    });
    document.getElementById("categoryFilter").addEventListener("change", loadFeed);
  });

  document.addEventListener("i18n:changed", async () => {
    await loadCityFilter();
    await loadFeed();
    loadProductFilterOptions();
    loadInventory();
  });
})();
