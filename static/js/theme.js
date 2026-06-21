/* مدیریت حالت روشن/تاریک/خودکار سازه‌مارکت */
(function () {
  const KEY = "sazeh_theme";
  const mq = window.matchMedia("(prefers-color-scheme: dark)");

  function effective(mode) {
    return mode === "dark" || (mode === "auto" && mq.matches) ? "dark" : "light";
  }

  function getMode() {
    const saved = localStorage.getItem(KEY);
    return ["light", "dark", "auto"].includes(saved) ? saved : "auto";
  }

  function apply(mode) {
    document.documentElement.setAttribute("data-theme", effective(mode));
    const icon = document.getElementById("themeIcon");
    if (icon) {
      icon.setAttribute("data-lucide", mode === "auto" ? "monitor" : mode === "dark" ? "moon" : "sun");
      if (window.lucide) lucide.createIcons();
    }
    document.querySelectorAll("#themeMenu [data-theme-choice]").forEach((b) => {
      b.classList.toggle("active", b.dataset.themeChoice === mode);
    });
  }

  function setMode(mode) {
    localStorage.setItem(KEY, mode);
    apply(mode);
  }

  mq.addEventListener("change", () => {
    if (getMode() === "auto") apply("auto");
  });

  function wire() {
    const sw = document.querySelector(".theme-switch");
    const btn = document.getElementById("themeBtn");
    const menu = document.getElementById("themeMenu");
    if (btn && menu) {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.toggle("hidden");
      });
      document.addEventListener("click", (e) => {
        if (sw && !sw.contains(e.target)) menu.classList.add("hidden");
      });
      menu.querySelectorAll("[data-theme-choice]").forEach((b) => {
        b.addEventListener("click", () => {
          setMode(b.dataset.themeChoice);
          menu.classList.add("hidden");
        });
      });
    }
    apply(getMode());
  }

  document.addEventListener("DOMContentLoaded", wire);
  window.Theme = { setMode, getMode };
})();
