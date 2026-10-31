/**
 * Content script, injected only when the user opens the popup on a page
 * (activeTab permission), never on every site. It answers two messages:
 *   {type: "applypilot:scan"}            -> list of fields on the page
 *   {type: "applypilot:fill", items}     -> fill the chosen fields
 */
(function () {
  if (window.__applypilotLoaded) return;
  window.__applypilotLoaded = true;
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg && msg.type === "applypilot:scan") {
      sendResponse({ fields: window.ApplyPilotScanner.scanFields(document), url: location.hostname });
    } else if (msg && msg.type === "applypilot:fill") {
      sendResponse(window.ApplyPilotFiller.fillFields(document, msg.items || []));
    } else if (msg && msg.type === "applypilot:attach") {
      const bytes = new Uint8Array(msg.bytes || []);
      sendResponse(window.ApplyPilotFiller.attachFile(document, msg.index, bytes, msg.filename, msg.mime));
    }
    return false;
  });
})();
