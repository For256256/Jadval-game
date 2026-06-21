/* باکس تبلیغات متحرک سازه‌مارکت */
(function () {
  const SLIDES = [
    {
      icon: "crown",
      gradient: "linear-gradient(120deg,#2454e8,#5b85ff 60%,#7ea0ff)",
      titleKey: "ads.slide1_title",
      descKey: "ads.slide1_desc",
      ctaKey: "ads.slide1_cta",
      href: "#pricingSection",
    },
    {
      icon: "sparkles",
      gradient: "linear-gradient(120deg,#9333ea,#c026d3 60%,#e879f9)",
      titleKey: "ads.slide2_title",
      descKey: "ads.slide2_desc",
      ctaKey: "ads.slide2_cta",
      href: "#rfqText",
    },
    {
      icon: "bell-ring",
      gradient: "linear-gradient(120deg,#0e7a5f,#15a36e 60%,#34d399)",
      titleKey: "ads.slide3_title",
      descKey: "ads.slide3_desc",
      ctaKey: "ads.slide3_cta",
      href: "/supplier",
    },
    {
      icon: "gift",
      gradient: "linear-gradient(120deg,#c2680f,#f0a324 60%,#fbc760)",
      titleKey: "ads.slide4_title",
      descKey: "ads.slide4_desc",
      ctaKey: "ads.slide4_cta",
      href: "/register",
    },
  ];

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let idx = 0;
  let timer = null;
  let track, dotsWrap;

  function isRTL() {
    return document.documentElement.getAttribute("dir") === "rtl";
  }

  function update() {
    const sign = isRTL() ? 1 : -1;
    track.style.transform = `translateX(${sign * idx * 100}%)`;
    dotsWrap.querySelectorAll(".ad-dot").forEach((d, i) => d.classList.toggle("active", i === idx));
  }

  function goTo(i) {
    idx = (i + SLIDES.length) % SLIDES.length;
    update();
  }
  function next() { goTo(idx + 1); }
  function prev() { goTo(idx - 1); }

  function start() {
    if (reduceMotion) return;
    stop();
    timer = setInterval(next, 5000);
  }
  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  function render() {
    track.innerHTML = SLIDES.map(
      (s) => `
      <a class="ad-slide" href="${s.href}" style="background:${s.gradient}">
        <span class="ad-slide-icon"><i data-lucide="${s.icon}"></i></span>
        <span class="ad-slide-text">
          <b>${window.I18N.t(s.titleKey)}</b>
          <span>${window.I18N.t(s.descKey)}</span>
        </span>
        <span class="ad-cta">${window.I18N.t(s.ctaKey)}</span>
      </a>`
    ).join("");
    dotsWrap.innerHTML = SLIDES.map((_, i) => `<button class="ad-dot" type="button" data-go="${i}" aria-label="slide ${i + 1}"></button>`).join("");
    if (window.lucide) lucide.createIcons();
    update();
  }

  function waitForI18N(cb) {
    if (window.I18N && Object.keys(window.I18N.dict || {}).length) { cb(); return; }
    const t = setInterval(() => {
      if (window.I18N && Object.keys(window.I18N.dict || {}).length) {
        clearInterval(t);
        cb();
      }
    }, 20);
  }

  function init() {
    const carousel = document.getElementById("adCarousel");
    if (!carousel) return;
    track = document.getElementById("adTrack");
    dotsWrap = document.getElementById("adDots");

    waitForI18N(() => {
      render();
      start();
    });

    carousel.addEventListener("mouseenter", stop);
    carousel.addEventListener("mouseleave", start);
    carousel.addEventListener("focusin", stop);
    carousel.addEventListener("focusout", start);

    document.getElementById("adPrev").addEventListener("click", () => { prev(); start(); });
    document.getElementById("adNext").addEventListener("click", () => { next(); start(); });
    dotsWrap.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-go]");
      if (!btn) return;
      goTo(Number(btn.dataset.go));
      start();
    });
  }

  document.addEventListener("DOMContentLoaded", init);
  document.addEventListener("i18n:changed", () => {
    if (track) render();
  });
})();
