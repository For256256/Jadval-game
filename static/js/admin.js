/* پنل مدیریت سیستم — کاربران، دسته‌بندی‌ها، کمیسیون و گزارش مالی */
(function () {
  let STATS = null;
  let revenueChart = null;

  function statusBadge(status) {
    const map = {
      active: ["badge-success", "admin.status_active"],
      pending: ["badge-amber", "admin.status_pending"],
      suspended: ["badge-danger", "admin.status_suspended"],
    };
    const [cls, key] = map[status] || map.active;
    return `<span class="badge ${cls}">${window.I18N.t(key)}</span>`;
  }

  function renderStats() {
    window.Motion.animateValue(document.getElementById("statUsers"), STATS.total_users, { format: (v) => fmtNum(Math.round(v)) });
    window.Motion.animateValue(document.getElementById("statSuppliers"), STATS.total_suppliers, { format: (v) => fmtNum(Math.round(v)) });
    window.Motion.animateValue(document.getElementById("statVolume"), Math.round(STATS.monthly_volume_toman / 1e9), { format: (v) => `${fmtNum(Math.round(v))}B` });
    window.Motion.animateValue(document.getElementById("statCommission"), Math.round(STATS.monthly_commission_toman / 1e6), { format: (v) => `${fmtNum(Math.round(v))}M` });
  }

  function renderUsers() {
    const tbody = document.getElementById("usersBody");
    tbody.innerHTML = STATS.users
      .map((u) => {
        const roleKey = u.role === "buyer" ? "admin.role_buyer" : "admin.role_supplier";
        let actions = "";
        if (u.status === "pending") {
          actions = `<button class="btn btn-primary btn-sm" data-status="${u.id}:active">${window.I18N.t("admin.approve")}</button>`;
        } else if (u.status === "active") {
          actions = `<button class="btn btn-outline btn-sm" data-status="${u.id}:suspended">${window.I18N.t("admin.suspend")}</button>`;
        } else {
          actions = `<button class="btn btn-outline btn-sm" data-status="${u.id}:active">${window.I18N.t("admin.activate")}</button>`;
        }
        return `
        <tr>
          <td><div class="avatar-chip"><span class="dot">${window.I18N.pick(u.name).slice(0, 1)}</span>${window.I18N.pick(u.name)}</div></td>
          <td>${window.I18N.t(roleKey)}</td>
          <td>${window.I18N.pick(u.city)}</td>
          <td>${statusBadge(u.status)}</td>
          <td>${actions}</td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll("[data-status]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const [id, status] = btn.dataset.status.split(":");
        try {
          await fetchJSON(`/api/admin/users/${id}/status`, {
            method: "POST",
            body: JSON.stringify({ status }),
          });
          const user = STATS.users.find((u) => u.id === Number(id));
          if (user) user.status = status;
          toast(window.I18N.t("admin.toast_status_updated"), "success");
          renderUsers();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  }

  function renderCategories() {
    const wrap = document.getElementById("categoriesGrid");
    wrap.innerHTML = STATS.categories
      .map(
        (c) => `
        <div class="cat-card spot-card">
          <div class="cat-icon"><i data-lucide="${c.icon}"></i></div>
          <span>${window.I18N.pick(c.name)}</span>
        </div>`
      )
      .join("");
    if (window.lucide) lucide.createIcons();
    window.Motion.refresh(wrap);
  }

  function renderRevenueChart() {
    const ctx = document.getElementById("revenueChart").getContext("2d");
    if (revenueChart) revenueChart.destroy();
    revenueChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: STATS.revenue_series.map((_, i) => i + 1),
        datasets: [
          {
            data: STATS.revenue_series,
            borderColor: "#2454e8",
            backgroundColor: "rgba(36,84,232,.12)",
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 2.5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } },
      },
    });
  }

  async function loadCommissionForm() {
    const settings = await fetchJSON("/api/admin/commission");
    document.getElementById("tier1Input").value = settings.tier1_monthly;
    document.getElementById("tier2Input").value = settings.tier2_monthly;
    document.getElementById("tier3Input").value = settings.tier3_monthly;
    document.getElementById("feeInput").value = settings.fee_percent;
  }

  async function saveCommission() {
    try {
      await fetchJSON("/api/admin/commission", {
        method: "POST",
        body: JSON.stringify({
          tier1_monthly: Number(document.getElementById("tier1Input").value),
          tier2_monthly: Number(document.getElementById("tier2Input").value),
          tier3_monthly: Number(document.getElementById("tier3Input").value),
          fee_percent: Number(document.getElementById("feeInput").value),
        }),
      });
      toast(window.I18N.t("admin.toast_saved"), "success");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function loadAll() {
    STATS = await fetchJSON("/api/admin/stats");
    renderStats();
    renderUsers();
    renderCategories();
    renderRevenueChart();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await loadAll();
    await loadCommissionForm();
    document.getElementById("saveCommissionBtn").addEventListener("click", saveCommission);
  });

  document.addEventListener("i18n:changed", () => {
    if (STATS) {
      renderStats();
      renderUsers();
      renderCategories();
    }
  });
})();
