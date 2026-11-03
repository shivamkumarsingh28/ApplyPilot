// Per-screen help (spec 8.1). One content file, plain words, editable without code.
export const HELP: Record<string, { title: string; body: string[]; actions?: { label: string; href: string }[] }> = {
  "/": {
    title: "Home",
    body: ["Home answers one question: what should I do next?", "Finish the setup checklist once. After that, your next deadline and quick actions are always here."],
    actions: [{ label: "Add a notice", href: "/notices" }, { label: "Ask the assistant", href: "/assistant" }],
  },
  "/assistant": {
    title: "Assistant",
    body: ["Ask anything about your notices: dates, fees, eligibility, documents, photo rules.", "Every answer shows the page it came from. Tap “How I answered” to see the steps.", "The assistant never submits a form and never fills passwords or ID fields."],
  },
  "/notices": {
    title: "Notices",
    body: ["Upload a notice PDF, a photo of it, or paste its text. We read it once and share it with everyone who uploads the same notice.", "Do not upload personal documents (marksheets, ID cards) here — those belong in your Vault."],
    actions: [{ label: "Open your vault", href: "/vault" }],
  },
  "/photo": {
    title: "Photo Studio",
    body: ["Portals reject files for wrong pixels, wrong KB, or wrong background. Pick a mode, set the rules (or choose a notice), and we make a file that passes.", "Resize only changes nothing but size. Your original is never changed — results save as copies."],
  },
  "/vault": {
    title: "Vault",
    body: ["Keep your originals here once: photo, signature, certificates. For each application we make a separate copy that fits its rules.", "Files are encrypted before they are saved. Only you can see them."],
  },
  "/tracker": {
    title: "Tracker",
    body: ["Every application with its deadline and status. “Closing soon” is always on top so nothing is missed.", "Use the board view to drag your work from Planned to Submitted."],
  },
  "/profile": {
    title: "Profile",
    body: ["Filled once, used everywhere: eligibility checks and form filling. We never ask for ID numbers, passport or bank details.", "Add your own fields (blood group, mother tongue…) — the extension will offer them on matching forms, always for your confirmation."],
  },
  "/chat-apps": {
    title: "Chat apps",
    body: ["Connect Telegram or WhatsApp to ask questions and get deadline reminders in chat.", "In Telegram: tap Open Telegram, press Start. Or send the shown code to the bot."],
  },
  "/extension": {
    title: "Browser extension",
    body: ["The extension fills forms from your profile and attaches vault files. You review every field, and you press Submit yourself.", "It never fills passwords, captcha, OTP or ID fields."],
  },
  "/settings": {
    title: "Settings",
    body: ["Language, sharing and your data. Download everything we hold about you, or delete your account.", "Sharing a public notice helps other students: the same notice is read once for everyone."],
  },
};

export function helpFor(path: string) {
  if (path.startsWith("/notices/")) return { title: "This notice", body: ["Key facts show the page each fact came from. “As written in the notice” quotes are copied exactly from the PDF.", "Eligibility is checked from your profile — add the missing field and it re-runs here."] };
  return HELP[path] ?? HELP["/"];
}
