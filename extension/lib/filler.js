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

  /** Attach bytes to a file input via DataTransfer and fire change (plan 4.7 step 4). */
  function attachFile(doc, index, bytes, filename, mime) {
    const el = doc.querySelector("[" + ATTR + '="' + index + '"]');
    if (!el || el.type !== "file") return { attached: false, reason: "field-not-found" };
    try {
      const file = new doc.defaultView.File([bytes], filename, { type: mime });
      const dt = new doc.defaultView.DataTransfer();
      dt.items.add(file);
      el.files = dt.files;
      el.dispatchEvent(new doc.defaultView.Event("input", { bubbles: true }));
      el.dispatchEvent(new doc.defaultView.Event("change", { bubbles: true }));
      const ok = el.files && el.files.length > 0;
      if (ok) {
        el.style.outline = "2px solid #2f9e44";
        el.title = "Attached by ApplyPilot: " + filename + ". Check it before you submit.";
        // Small visible label next to the field: mid-form, the user must SEE which file landed where.
        try {
          const tag = doc.createElement("span");
          tag.dataset.applypilotAttached = "1";
          tag.textContent = "✓ ApplyPilot: " + filename;
          tag.style.cssText = "display:inline-block;margin:4px 0;padding:2px 6px;background:#e6f4ea;color:#14532d;border-radius:4px;font-size:12px";
          el.insertAdjacentElement("afterend", tag);
        } catch (e) { /* label is best-effort; the outline already marks the field */ }
      }
      return { attached: !!ok, reason: ok ? "" : "files-not-set" };
    } catch (e) {
      return { attached: false, reason: String(e && e.message || e) };
    }
  }

  const api = { fillFields, setNativeValue, attachFile };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ApplyPilotFiller = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
