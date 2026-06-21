/* منطق صفحه اصلی سازه‌مارکت: تحلیل هوشمند RFQ + ویجت قیمت */
(function () {
  let priceChart = null;
  let lastParsed = null;

  async function loadPriceChart(material) {
    const data = await fetchJSON(`/api/price-history?material=${material}`);
    const ctx = document.getElementById("priceChart").getContext("2d");

    document.getElementById("priceNow").textContent = `${fmtNum(data.today)} ${window.I18N.pick(data.unit)}`;
    if (material === "rebar") {
      const hvChipPrice = document.getElementById("hvChipPrice");
      if (hvChipPrice) hvChipPrice.textContent = `${fmtNum(data.today)} ${window.I18N.pick(data.unit)}`;
    }
    const changeEl = document.getElementById("priceChange");
    const up = data.change_pct >= 0;
    changeEl.textContent = `${up ? "▲" : "▼"} ${Math.abs(data.change_pct)}%`;
    changeEl.className = up ? "text-success" : "text-danger";

    const labels = data.series.map((_, i) => i + 1);
    const gradient = ctx.createLinearGradient(0, 0, 0, 220);
    gradient.addColorStop(0, "rgba(36,84,232,.28)");
    gradient.addColorStop(1, "rgba(36,84,232,0)");

    if (priceChart) priceChart.destroy();
    priceChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data: data.series,
            borderColor: "#2454e8",
            backgroundColor: gradient,
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            borderWidth: 2.5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { displayColors: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
      },
    });
  }

  let lastPricing = null;

  function renderPricing(settings) {
    lastPricing = settings;
    const tiers = [
      { key: "tier1", price: settings.tier1_monthly, featured: false },
      { key: "tier2", price: settings.tier2_monthly, featured: true },
      { key: "tier3", price: settings.tier3_monthly, featured: false },
    ];
    document.getElementById("pricingGrid").innerHTML = tiers
      .map(
        (tier) => `
        <div class="pricing-card spot-card${tier.featured ? " featured" : ""}" data-reveal>
          ${tier.featured ? `<span class="badge badge-primary">${window.I18N.t("home.pricing_tier2_badge")}</span>` : ""}
          <h3>${window.I18N.t(`home.pricing_${tier.key}_name`)}</h3>
          <p class="pricing-desc">${window.I18N.t(`home.pricing_${tier.key}_desc`)}</p>
          <div class="pricing-price">
            <b>${fmtNum(tier.price)}</b>
            <span>${window.I18N.t("home.pricing_per_month")}</span>
          </div>
        </div>`
      )
      .join("");
    document.getElementById("pricingFeeNote").innerHTML =
      `${window.I18N.t("home.pricing_fee_note")} <b>${settings.fee_percent}٪</b> ${window.I18N.t("home.pricing_fee_note_suffix")}`;
    if (window.Motion) window.Motion.refresh(document.getElementById("pricingGrid"));
  }

  async function loadPricing() {
    const settings = await fetchJSON("/api/pricing");
    renderPricing(settings);
  }

  function wirePriceTabs() {
    document.querySelectorAll(".price-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".price-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        loadPriceChart(tab.dataset.material);
      });
    });
  }

  function renderBom(parsed) {
    lastParsed = parsed;
    const wrap = document.getElementById("bomResult");
    wrap.classList.remove("hidden");

    document.getElementById("bomCity").textContent = parsed.city ? window.I18N.pick(parsed.city) : "—";
    document.getElementById("bomArea").textContent = parsed.area_sqm ? `${fmtNum(parsed.area_sqm)} m²` : "—";

    const tbody = document.getElementById("bomBody");
    tbody.innerHTML = "";
    parsed.bom.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${window.I18N.pick(item.material)}</td>
        <td>${typeof item.spec === "object" ? window.I18N.pick(item.spec) : item.spec}</td>
        <td><input type="number" step="0.1" value="${item.qty}" data-id="${item.id}" /></td>
        <td>${window.I18N.pick(item.unit)}</td>
      `;
      tbody.appendChild(tr);
    });
    wrap.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function analyzeRequest() {
    const text = document.getElementById("rfqText").value.trim();
    if (!text) {
      toast(window.I18N.t("home.hero_placeholder"), "error");
      return;
    }
    const btn = document.getElementById("analyzeBtn");
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span><span>${window.I18N.t("home.hero_analyzing")}</span>`;
    try {
      const parsed = await fetchJSON("/api/rfq/parse", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      renderBom(parsed);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = original;
    }
  }

  async function submitRfq() {
    if (!lastParsed) return;
    const tbody = document.getElementById("bomBody");
    const inputs = tbody.querySelectorAll("input[data-id]");
    const bom = lastParsed.bom.map((item, idx) => ({ ...item, qty: parseFloat(inputs[idx].value) || item.qty }));
    try {
      await fetchJSON("/api/rfq", {
        method: "POST",
        body: JSON.stringify({ text: document.getElementById("rfqText").value, bom, city: lastParsed.city }),
      });
      toast(window.I18N.t("dashboard.toast_rfq_created"), "success");
      setTimeout(() => (window.location.href = "/dashboard"), 900);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    wirePriceTabs();
    loadPriceChart("rebar");
    loadPricing();
    document.getElementById("analyzeBtn").addEventListener("click", analyzeRequest);
    document.getElementById("submitRfqBtn").addEventListener("click", submitRfq);
    document.getElementById("rfqText").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) analyzeRequest();
    });
  });

  document.addEventListener("i18n:changed", () => {
    loadPriceChart(document.querySelector(".price-tab.active")?.dataset.material || "rebar");
    if (lastParsed) renderBom(lastParsed);
    if (lastPricing) renderPricing(lastPricing);
  });
})();
