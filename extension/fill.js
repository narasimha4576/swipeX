// Fills a Greenhouse application form. It never submits the form.
(() => {
  if (window.__swipexAutofillLoaded) return;
  window.__swipexAutofillLoaded = true;

  const SKIP_TOPICS =
    /(gender|\brace\b|ethnic|veteran|disabilit|pronoun|sexual orientation|hispanic|latino|transgender|demographic|self[- ]identif)/;

  function lpa(value) {
    return value === null || value === undefined ? null : value + " LPA";
  }

  const TEXT_RULES = [
    { test: /\b(first|given)\s*name\b/, get: (a) => a.first_name },
    { test: /\b(last|family)\s*name\b|\bsurname\b/, get: (a) => a.last_name },
    { test: /e[- ]?mail/, get: (a) => a.email },
    { test: /\b(phone|mobile|telephone|contact number)\b/, get: (a) => a.phone },
    { test: /linkedin/, get: (a) => a.linkedin_url },
    { test: /github/, get: (a) => a.github_url },
    {
      test: /\b(website|portfolio|personal (site|page)|other (url|link)|blog)\b/,
      get: (a) => a.website,
    },
    { test: /cover letter/, get: (a) => a.cover_letter },
    {
      test: /notice period/,
      get: (a) =>
        a.notice_period_days === null || a.notice_period_days === undefined
          ? null
          : a.notice_period_days + " days",
    },
    {
      test: /(expected|desired).{0,25}(ctc|salary|compensation|pay)|salary expectation/,
      get: (a) => lpa(a.expected_ctc_lpa),
    },
    { test: /current.{0,25}(ctc|salary|compensation)/, get: (a) => lpa(a.current_ctc_lpa) },
    { test: /\b(school|university|college|institution)\b/, get: (a) => a.college },
    { test: /\bdegree\b/, get: (a) => a.degree },
    {
      test: /\b(discipline|major|field of study|specialization|specialisation)\b/,
      get: (a) => a.discipline,
    },
    {
      test: /(graduation|passing|completion).{0,15}year|year of (graduation|passing)/,
      get: (a) => a.graduation_year,
    },
    {
      test: /how did you (hear|find)|where did you (hear|find)|referral source/,
      get: (a) => a.how_did_you_hear,
    },
    {
      test: /\b(current location|your location|city|where are you (based|located))\b/,
      get: (a) => a.location,
    },
    { test: /^location( \(city\))?$/, primaryOnly: true, get: (a) => a.location },
    { test: /^(full name|legal name|name)$/, primaryOnly: true, get: (a) => a.full_name },
  ];

  const COUNTRIES = [
    /\bindia\b/,
    /\b(united states|u\.s\.a?\.?|usa)\b|\bus\b/,
    /\b(united kingdom|u\.k\.|uk)\b/,
    /\bcanada\b/,
    /\bgermany\b/,
    /\bsingapore\b/,
    /\baustralia\b/,
    /\buae\b|united arab emirates/,
    /\bnetherlands\b/,
    /\bireland\b/,
  ];

  // Answers "authorized to work" only when the country is named and you listed countries.
  function authorized(applicant, text) {
    const have = (applicant.authorized_countries || "").toLowerCase();
    if (!have) return null;
    for (const country of COUNTRIES) {
      if (country.test(text)) return country.test(have);
    }
    return null;
  }

  const YES_NO = [
    { test: /sponsor/, answer: (a) => Boolean(a.requires_sponsorship) },
    { test: /relocat/, answer: (a) => Boolean(a.willing_to_relocate) },
    {
      test: /(authori[sz]ed|eligible|legally|permitted|right).{0,40}work|work authori[sz]ation/,
      answer: authorized,
    },
  ];

  function yesNoFor(text, applicant) {
    for (const rule of YES_NO) {
      if (rule.test.test(text)) return rule.answer(applicant, text);
    }
    return null;
  }

  const state = { filled: 0, resume: false, dismissed: false };

  function hasValue(value) {
    return value !== null && value !== undefined && value !== "";
  }

  function clean(text) {
    return String(text || "")
      .replace(/[_\[\]]+/g, " ")
      .replace(/[*:]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function usable(el) {
    if (el.disabled || el.readOnly) return false;
    const type = (el.type || "").toLowerCase();
    if (type === "hidden") return false;
    if (type === "file" || type === "radio" || type === "checkbox") return true;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function describe(el) {
    const labels = [];
    if (el.id) {
      document
        .querySelectorAll('label[for="' + CSS.escape(el.id) + '"]')
        .forEach((label) => labels.push(label.textContent));
    }
    const wrapper = el.closest("label");
    if (wrapper) labels.push(wrapper.textContent);
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      labelledBy.split(/\s+/).forEach((id) => {
        const node = document.getElementById(id);
        if (node) labels.push(node.textContent);
      });
    }
    const aria = el.getAttribute("aria-label");
    if (aria) labels.push(aria);

    const primary = clean(labels[0] || el.getAttribute("placeholder") || el.name || el.id);
    const all = clean(
      labels.concat([el.getAttribute("placeholder"), el.name, el.id]).filter(Boolean).join(" ")
    );
    return { primary: primary, all: all };
  }

  function groupQuestion(radio) {
    const box = radio.closest("fieldset, [role='radiogroup'], [role='group']");
    let text = "";
    if (box) {
      const legend = box.querySelector("legend");
      if (legend) text = legend.textContent;
      const labelledBy = box.getAttribute("aria-labelledby");
      if (!text && labelledBy) {
        text = labelledBy
          .split(/\s+/)
          .map((id) => (document.getElementById(id) ? document.getElementById(id).textContent : ""))
          .join(" ");
      }
      if (!text) text = box.getAttribute("aria-label") || "";
    }
    return clean(text);
  }

  function setNative(el, value) {
    const proto =
      el instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : el instanceof HTMLSelectElement
        ? HTMLSelectElement.prototype
        : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function chooseOption(select, wanted) {
    const target = clean(wanted);
    const options = Array.from(select.options).filter((o) => o.value !== "");
    const hit =
      options.find((o) => clean(o.textContent) === target) ||
      options.find((o) => clean(o.textContent).startsWith(target)) ||
      options.find((o) => clean(o.textContent).includes(target));
    if (!hit) return false;
    setNative(select, hit.value);
    return true;
  }

  function holderFor(el) {
    const parent = el.parentElement;
    return parent && parent.getBoundingClientRect().height < 160 ? parent : el;
  }

  function holderFor(el) {
    const parent = el.parentElement;
    return parent && parent.getBoundingClientRect().height < 160 ? parent : el;
  }

  function mark(el) {
    el.classList.add("swipex-filled");
  }

  function textValue(type, primary, all, applicant) {
    if (type === "email") return applicant.email;
    if (type === "tel") return applicant.phone;
    for (const rule of TEXT_RULES) {
      if (rule.test.test(rule.primaryOnly ? primary : all)) return rule.get(applicant);
    }
    return undefined;
  }

  function looksLikeResume(el) {
    const own = describe(el).all;
    if (/cover/.test(own)) return false;
    if (/resume|\bcv\b|curriculum/.test(own)) return true;
    let box = el.parentElement;
    let text = "";
    for (let i = 0; i < 4 && box; i++, box = box.parentElement) {
      const t = clean(box.textContent);
      if (t.length < 300) text = t;
      else break;
    }
    return /resume|\bcv\b|curriculum/.test(text) && !/cover letter/.test(text);
  }

  function attachResume(resume) {
    if (!resume || !resume.data_base64) return false;
    const input = Array.from(document.querySelectorAll('input[type="file"]')).find(
      (el) => !el.disabled && looksLikeResume(el)
    );
    if (!input || input.files.length > 0) return false;
    try {
      const bytes = Uint8Array.from(atob(resume.data_base64), (c) => c.charCodeAt(0));
      const file = new File([bytes], resume.filename || "resume.pdf", {
        type: resume.mime || "application/pdf",
      });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      mark(holderFor(input));
      return true;
    } catch (error) {
      return false;
    }
  }

  function flagMissing() {
    let missing = 0;
    document.querySelectorAll("input, textarea, select").forEach((el) => {
      const type = (el.type || "").toLowerCase();
      if (["hidden", "submit", "button", "checkbox", "radio", "reset", "image"].includes(type)) return;
      const required = el.required || el.getAttribute("aria-required") === "true";
      if (!required || el.disabled || !usable(el)) return;
      const empty = type === "file" ? el.files.length === 0 : !el.value;
      const target = type === "file" ? holderFor(el) : el;
      if (empty) {
        target.classList.add("swipex-needs");
        missing++;
      } else {
        target.classList.remove("swipex-needs");
      }
    });
    return missing;
  }

  function injectStyles() {
    if (document.getElementById("swipex-style")) return;
    const style = document.createElement("style");
    style.id = "swipex-style";
    style.textContent =
      ".swipex-filled{outline:2px solid #ff6a1a !important;outline-offset:1px;}" +
      ".swipex-needs{outline:2px dashed #d13b2f !important;outline-offset:1px;}" +
      "#swipex-banner{position:fixed;z-index:2147483647;top:0;left:0;right:0;display:flex;gap:12px;" +
      "align-items:center;justify-content:space-between;padding:10px 14px;background:#161616;color:#fff;" +
      "font:13px/1.4 system-ui,sans-serif;border-bottom:3px solid #ff6a1a;}" +
      "#swipex-banner button{background:#ff6a1a;color:#161616;border:0;padding:4px 10px;font-weight:700;cursor:pointer;}";
    document.documentElement.appendChild(style);
  }

  function showBanner(missing) {
    if (state.dismissed) return;
    let box = document.getElementById("swipex-banner");
    if (!box) {
      box = document.createElement("div");
      box.id = "swipex-banner";
      document.documentElement.appendChild(box);
    }
    box.textContent = "";
    let message =
      "SwipeX filled " +
      state.filled +
      " field" +
      (state.filled === 1 ? "" : "s") +
      (state.resume ? ", including your resume" : "") +
      ". ";
    if (missing > 0) {
      message +=
        missing +
        " required field" +
        (missing === 1 ? " still needs" : "s still need") +
        " your answer (red dashed outline). ";
    }
    message += "Check everything, then press Submit yourself.";
    const text = document.createElement("span");
    text.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "Dismiss";
    close.addEventListener("click", () => {
      state.dismissed = true;
      box.remove();
    });
    box.append(text, close);
  }

  function runPass(applicant, resume) {
    const fields = Array.from(document.querySelectorAll("input, textarea, select")).filter(usable);
    const radioGroups = new Map();

    for (const el of fields) {
      const type = (el.type || "").toLowerCase();
      if (type === "radio") {
        const list = radioGroups.get(el.name) || [];
        list.push(el);
        radioGroups.set(el.name, list);
        continue;
      }
      if (["file", "checkbox", "submit", "button", "reset", "image", "password", "search"].includes(type)) {
        continue;
      }
      if (el.getAttribute("role") === "combobox" || el.getAttribute("aria-haspopup") === "listbox") {
        continue;
      }

      const names = describe(el);
      if (SKIP_TOPICS.test(names.all)) continue;

      if (el.tagName === "SELECT") {
        if (el.value) continue;
        const yes = yesNoFor(names.all, applicant);
        if (yes !== null && yes !== undefined) {
          if (chooseOption(el, yes ? "yes" : "no")) {
            mark(el);
            state.filled++;
          }
          continue;
        }
        const wanted = textValue(type, names.primary, names.all, applicant);
        if (hasValue(wanted) && chooseOption(el, wanted)) {
          mark(el);
          state.filled++;
        }
        continue;
      }

      if (el.value) continue;
      const value = textValue(type, names.primary, names.all, applicant);
      if (!hasValue(value)) continue;
      setNative(el, String(value));
      mark(el);
      state.filled++;
    }

    for (const group of radioGroups.values()) {
      if (group.some((radio) => radio.checked)) continue;
      const question = groupQuestion(group[0]) || describe(group[0]).all;
      if (SKIP_TOPICS.test(question)) continue;
      const yes = yesNoFor(question, applicant);
      if (yes === null || yes === undefined) continue;
      const wanted = yes ? "yes" : "no";
      const target = group.find((radio) => describe(radio).primary.startsWith(wanted));
      if (target) {
        target.click();
        mark(target.closest("label") || target.parentElement || target);
        state.filled++;
      }
    }

    if (!state.resume && attachResume(resume)) {
      state.resume = true;
      state.filled++;
    }

    showBanner(flagMissing());
  }

  function waitForForm(timeout) {
    const found = () =>
      document.querySelector(
        "input[type='email'], input[name*='email' i], input#first_name, input[name*='first' i]"
      );
    return new Promise((resolve) => {
      if (found()) return resolve(true);
      const observer = new MutationObserver(() => {
        if (found()) {
          observer.disconnect();
          clearTimeout(timer);
          resolve(true);
        }
      });
      observer.observe(document.documentElement, { childList: true, subtree: true });
      const timer = setTimeout(() => {
        observer.disconnect();
        resolve(false);
      }, timeout);
    });
  }

  async function start() {
    let response = null;
    for (let attempt = 0; attempt < 3 && !(response && response.ok); attempt++) {
      try {
        response = await chrome.runtime.sendMessage({ type: "GET_PAYLOAD" });
      } catch (error) {
        return;
      }
      if (!(response && response.ok)) await new Promise((resolve) => setTimeout(resolve, 600));
    }
    if (!response || !response.ok) return;

    injectStyles();
    const applicant = response.payload.applicant;
    const resume = response.payload.resume;
    if (!(await waitForForm(20000))) return;

    runPass(applicant, resume);
    setTimeout(() => runPass(applicant, resume), 2500);
    setTimeout(() => runPass(applicant, resume), 6000);
  }

  start();
})();