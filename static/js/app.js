/* توابع مشترک رابط کاربری سازه‌مارکت */
(function () {
  window.fmtNum = (n) => Number(n || 0).toLocaleString("en-US");

  window.toast = (msg, type = "info") => {
    const stack = document.getElementById("toastStack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "all .25s ease";
      setTimeout(() => el.remove(), 250);
    }, 3400);
  };

  window.fetchJSON = async (url, options = {}) => {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `خطا (${res.status})`);
    }
    return res.json();
  };

  window.openModal = (id) => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("hidden");
  };
  window.closeModal = (id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  };

  document.addEventListener("click", (e) => {
    if (e.target.matches("[data-close-modal]")) {
      const overlay = e.target.closest(".modal-overlay");
      if (overlay) overlay.classList.add("hidden");
    }
    if (e.target.classList.contains("modal-overlay")) {
      e.target.classList.add("hidden");
    }
  });

  function wireChrome() {
    const langSwitch = document.querySelector(".lang-switch");
    const langBtn = document.getElementById("langBtn");
    const langMenu = document.getElementById("langMenu");
    if (langBtn && langMenu) {
      langBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        langMenu.classList.toggle("hidden");
      });
      document.addEventListener("click", (e) => {
        if (langSwitch && !langSwitch.contains(e.target)) langMenu.classList.add("hidden");
      });
    }

    const burger = document.getElementById("burgerBtn");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    if (burger && sidebar) {
      burger.addEventListener("click", () => {
        sidebar.classList.add("open");
        overlay && overlay.classList.add("open");
      });
      overlay &&
        overlay.addEventListener("click", () => {
          sidebar.classList.remove("open");
          overlay.classList.remove("open");
        });
    }

    if (window.lucide) lucide.createIcons();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await window.I18N.init();
    wireChrome();
  });

  document.addEventListener("i18n:changed", () => {
    if (window.lucide) lucide.createIcons();
  });
})();
