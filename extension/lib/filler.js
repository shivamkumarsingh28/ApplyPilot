/**
 * Filler: writes values into fields the way a person typing would, so React,
 * Vue and Angular forms notice the change. Never submits the form and never
 * touches password, file or captcha inputs (the scanner does not return them).
 */
(function (root) {
  "use strict";

  const ATTR = "data-applypilot-idx";

  function setNativeValue(el, value) {
    // Frameworks wrap the value setter; calling the prototype setter bypasses their tracking,
    // then the dispatched events make them re-read the value.
    const proto = el.tagName === "SELECT" ? el.ownerDocument.defaultView.HTMLSelectElement.prototype
      : el.tagName === "TEXTAREA" ? el.ownerDocument.defaultView.HTMLTextAreaElement.prototype
      : el.ownerDocument.defaultView.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new el.ownerDocument.defaultView.Event("input", { bubbles: true }));
    el.dispatchEvent(new el.ownerDocument.defaultView.Event("change", { bubbles: true }));
  }

  /** @param {{index:number,value:string}[]} items  @returns {{filled:number, missing:number[]}} */
  function fillFields(doc, items) {
    doc = doc || root.document;
    let filled = 0;
    const missing = [];
    for (const item of items) {
      if (item.value === null || item.value === undefined || item.value === "") continue;
      const el = doc.querySelector("[" + ATTR + '="' + item.index + '"]');
      if (!el) { missing.push(item.index); continue; }
      if (el.type === "radio") {
        const group = doc.querySelectorAll('input[type="radio"][name="' + el.name + '"]');
        const target = Array.from(group).find((r) => r.value === item.value);
        if (!target) { missing.push(item.index); continue; }
        target.checked = true;
        target.dispatchEvent(new doc.defaultView.Event("input", { bubbles: true }));
        target.dispatchEvent(new doc.defaultView.Event("change", { bubbles: true }));
      } else {
        setNativeValue(el, String(item.value));
      }
      el.style.outline = item.needsReview ? "2px solid #e0a100" : "2px solid #2f5bea";
      el.title = item.needsReview ? "ApplyPilot: please double-check this value" : "Filled by ApplyPilot";
      filled++;
    }
    return { filled, missing };
  }

  const api = { fillFields, setNativeValue };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ApplyPilotFiller = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
