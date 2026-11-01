/**
 * Renders page 1 of a PDF to a canvas INSIDE the popup.
 *
 * Why not open the PDF in a tab? The user is mid-form on a deadline: a new tab
 * steals focus, and when they come back the popup has closed and their place is
 * lost. An in-popup thumbnail keeps them exactly where they are.
 *
 * Loaded as an ES module (pdf.js v4 is ESM-only). Plain logic + one import, so
 * the filename rules also run in node tests.
 */
import * as pdfjsLib from "./pdfjs/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("./pdfjs/pdf.worker.min.mjs", import.meta.url).href;

export function isPdf(doc) {
  return !!doc && ((doc.mime || "").toLowerCase().includes("pdf") || (doc.filename || "").toLowerCase().endsWith(".pdf"));
}

export function isImage(doc) {
  return !!doc && (doc.mime || "").toLowerCase().startsWith("image/");
}

/** @param {ArrayBuffer} bytes @param {HTMLCanvasElement} canvas */
export async function renderPdfFirstPage(bytes, canvas, maxWidth) {
  const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(bytes) }).promise;
  try {
    const page = await pdf.getPage(1);
    const base = page.getViewport({ scale: 1 });
    const scale = (maxWidth || 200) / base.width;
    const viewport = page.getViewport({ scale });
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
    return { pages: pdf.numPages };
  } finally {
    await pdf.destroy();
  }
}

// Popup (module scope) and node tests (require) both need the small helpers.
if (typeof window !== "undefined") window.ApplyPilotPdf = { renderPdfFirstPage, isPdf, isImage };
