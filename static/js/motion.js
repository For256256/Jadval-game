/* افکت‌های حرکتی رابط کاربری: ظاهر تدریجی هنگام اسکرول، شمارش اعداد،
   نقطه‌نور تعقیب‌کننده ماوس روی کارت‌ها، افکت ripple دکمه‌ها، و scrollspy سایدبار */
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let revealObserver;
  function initReveal(root) {
    const targets = root.querySelectorAll("[data-reveal]:not(.in-view)");
    if (!targets.length) return;
    if (reduceMotion) {
      targets.forEach((el) => el.classList.add("in-view"));
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("in-view");
              revealObserver.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
      );
    }
    targets.forEach((el, i) => {
      el.style.transitionDelay = `${(i % 6) * 70}ms`;
      revealObserver.observe(el);
    });
  }

  function initSpotlight(root) {
    root.querySelectorAll(".spot-card:not([data-spot-wired])").forEach((card) => {
      card.dataset.spotWired = "1";
      card.addEventListener("pointermove", (e) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
        card.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
      });
    });
  }

  function initRipple() {
    if (reduceMotion) return;
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn");
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height) * 1.6;
      const ripple = document.createElement("span");
      ripple.className = "btn-ripple";
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
      btn.appendChild(ripple);
      ripple.addEventListener("animationend", () => ripple.remove());
    });
  }

  function initScrollSpy() {
    const sidebar = document.querySelector(".sidebar");
    const links = Array.from(document.querySelectorAll(".side-link"));
    if (!sidebar || !links.length) return;
    const ids = [...new Set(links.map((l) => l.getAttribute("href")).filter((h) => h && h.startsWith("#")))];
    const sections = ids.map((id) => document.getElementById(id.slice(1))).filter(Boolean);
    if (!sections.length) return;
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const href = `#${entry.target.id}`;
          links.forEach((l) => l.classList.toggle("active", l.getAttribute("href") === href));
        });
      },
      { rootMargin: "-15% 0px -65% 0px" }
    );
    sections.forEach((s) => spy.observe(s));
  }

  function animateValue(el, target, opts = {}) {
    if (!el) return;
    const { duration = 850, format } = opts;
    const fmt = format || ((v) => String(Math.round(v)));
    target = Number(target) || 0;
    if (reduceMotion) {
      el.textContent = fmt(target);
      return;
    }
    const startTime = performance.now();
    function tick(now) {
      const p = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * eased);
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = fmt(target);
    }
    requestAnimationFrame(tick);
  }

  function refresh(root) {
    root = root || document;
    initReveal(root);
    initSpotlight(root);
  }

  window.Motion = { refresh, animateValue };

  document.addEventListener("DOMContentLoaded", () => {
    initRipple();
    initScrollSpy();
    refresh(document);
  });

  document.addEventListener("i18n:changed", () => refresh(document));
})();
