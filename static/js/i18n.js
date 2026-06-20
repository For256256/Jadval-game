/* سامانه چندزبانه سازه‌مارکت — فارسی / عربی / انگلیسی */
(function () {
  const SUPPORTED = ["fa", "ar", "en"];
  const STORAGE_KEY = "sazeh_lang";

  const I18N = {
    lang: "fa",
    dict: {},

    async init() {
      const saved = localStorage.getItem(STORAGE_KEY);
      const lang = SUPPORTED.includes(saved) ? saved : "fa";
      await this.setLang(lang, { silent: true });
      this._wireLangMenu();
    },

    async setLang(lang, opts = {}) {
      if (!SUPPORTED.includes(lang)) lang = "fa";
      const res = await fetch(`/static/i18n/${lang}.json`);
      this.dict = await res.json();
      this.lang = lang;
      localStorage.setItem(STORAGE_KEY, lang);

      document.documentElement.setAttribute("lang", lang);
      document.documentElement.setAttribute("dir", this.dict.dir || (lang === "en" ? "ltr" : "rtl"));

      this.apply();
      if (!opts.silent) {
        document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lang } }));
      }
    },

    t(path, fallback = "") {
      const parts = path.split(".");
      let cur = this.dict;
      for (const p of parts) {
        if (cur == null) return fallback;
        cur = cur[p];
      }
      return cur == null ? fallback : cur;
    },

    /** برای مقادیر سه‌زبانه برگشتی از بک‌اند: {fa, ar, en} */
    pick(obj) {
      if (obj == null) return "";
      if (typeof obj === "string") return obj;
      return obj[this.lang] || obj.fa || obj.en || "";
    },

    apply(root = document) {
      root.querySelectorAll("[data-i18n]").forEach((el) => {
        const val = this.t(el.getAttribute("data-i18n"));
        if (val) el.textContent = val;
      });
      root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        const val = this.t(el.getAttribute("data-i18n-placeholder"));
        if (val) el.setAttribute("placeholder", val);
      });
      root.querySelectorAll("[data-i18n-html]").forEach((el) => {
        const val = this.t(el.getAttribute("data-i18n-html"));
        if (val) el.innerHTML = val;
      });
      root.querySelectorAll(".lang-menu button").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.lang === this.lang);
      });
      const langLabel = document.getElementById("currentLangLabel");
      if (langLabel) {
        langLabel.textContent = { fa: "فا", ar: "AR", en: "EN" }[this.lang];
      }
    },

    _wireLangMenu() {
      document.querySelectorAll(".lang-menu button").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.setLang(btn.dataset.lang);
          document.querySelectorAll(".lang-menu").forEach((m) => m.classList.add("hidden"));
        });
      });
    },
  };

  window.I18N = I18N;
})();
