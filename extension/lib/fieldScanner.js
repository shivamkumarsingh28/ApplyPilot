/**
 * Field scanner: finds the fillable fields on a page and describes each one
 * (label, name, placeholder, type, options) so the backend can map it to the profile.
 *
 * Pure DOM code with no browser-extension APIs, so it runs in the page and in
 * jsdom unit tests. Each element gets a data-applypilot-idx attribute that the
 * filler uses to find it again later.
 */
(function (root) {
  "use strict";

  const SKIP_TYPES = new Set(["hidden", "submit", "button", "image", "reset", "file", "password"]);
  const ATTR = "data-applypilot-idx";

  function clean(text) {
    return (text || "").replace(/\s+/g, " ").replace(/[*:]+\s*$/, "").trim();
  }

  function isVisible(el) {
    if (el.hidden || el.getAttribute("aria-hidden") === "true") return false;
    const style = el.ownerDocument.defaultView.getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden";
  }

  /** Best human-readable label for a form control. */
  function labelFor(el) {
    const doc = el.ownerDocument;
    if (el.id) {
      const lab = doc.querySelector('label[for="' + (root.CSS && root.CSS.escape ? root.CSS.escape(el.id) : el.id) + '"]');
      if (lab) return clean(lab.textContent);
    }
    const wrap = el.closest("label");
    if (wrap) return clean(wrap.textContent.replace(el.value || "", ""));
    const labelledby = el.getAttribute("aria-labelledby");
    if (labelledby) {
      const t = labelledby.split(/\s+/).map((id) => (doc.getElementById(id) || {}).textContent || "").join(" ");
      if (clean(t)) return clean(t);
    }
    if (el.getAttribute("aria-label")) return clean(el.getAttribute("aria-label"));
    // Table-style forms (common on government portals): label sits in the previous cell.
    const cell = el.closest("td, th");
    if (cell && cell.previousElementSibling) {
      const t = clean(cell.previousElementSibling.textContent);
      if (t) return t;
    }
    // Label-like text just before the control inside the same container.
    let prev = el.previousSibling;
    while (prev) {
      const t = clean(prev.textContent || "");
      if (t) return t;
      prev = prev.previousSibling;
    }
    return clean(el.getAttribute("placeholder") || el.getAttribute("title") || el.name || "");
  }

  function optionsOf(el) {
    return Array.from(el.options)
      .filter((o) => o.value !== "") // drop the empty "--Select--" placeholder
      .map((o) => ({ value: o.value, label: clean(o.textContent) }));
  }

  /** Returns [{index,id,name,label,placeholder,type,autocomplete,pattern,options}] */
  function scanFields(doc) {
    doc = doc || root.document;
    const controls = Array.from(doc.querySelectorAll("input, select, textarea"));
    const out = [];
    const radios = new Map();
    let index = 0;
    for (const el of controls) {
      const tag = el.tagName.toLowerCase();
      const type = tag === "select" ? "select" : tag === "textarea" ? "textarea" : (el.getAttribute("type") || "text").toLowerCase();
      if (SKIP_TYPES.has(type) || el.disabled || el.readOnly || !isVisible(el)) continue;

      if (type === "radio") {
        const key = el.name || el.id;
        if (!radios.has(key)) {
          const desc = { index: index++, id: key, name: el.name, label: "", placeholder: "", type: "radio", autocomplete: el.getAttribute("autocomplete") || "", pattern: "", options: [] };
          radios.set(key, desc);
          out.push(desc);
          el.setAttribute(ATTR, String(desc.index));
        }
        const desc = radios.get(key);
        const optLabel = labelFor(el);
        desc.options.push({ value: el.value, label: optLabel });
        if (!desc.label) {
          const group = el.closest("fieldset");
          const legend = group && group.querySelector("legend");
          desc.label = legend ? clean(legend.textContent) : clean(el.name);
        }
        continue;
      }
      if (type === "checkbox") continue; // consent boxes must be ticked by the person

      const desc = {
        index: index++,
        id: el.id || el.name || "field-" + index,
        name: el.name || "",
        label: labelFor(el),
        placeholder: el.getAttribute("placeholder") || "",
        type: type,
        autocomplete: el.getAttribute("autocomplete") || "",
        pattern: el.getAttribute("pattern") || "",
        options: tag === "select" ? optionsOf(el) : [],
      };
      el.setAttribute(ATTR, String(desc.index));
      out.push(desc);
    }
    return out;
  }

  const api = { scanFields, labelFor, ATTR };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ApplyPilotScanner = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
