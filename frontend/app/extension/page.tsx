"use client";
import AuthGate from "@/components/AuthGate";
import { Card } from "@/components/ui";

export default function Page() {
  return (
    <AuthGate>
      <h1>Browser extension</h1>
      <p className="muted">Fill forms in one click and attach vault files to upload fields. You review every field — you always press Submit yourself.</p>
      <Card title="Install and use (about 2 minutes)">
        <ol>
          <li><strong>Add to Chrome:</strong> open <code>chrome://extensions</code>, turn on Developer mode, “Load unpacked”, and choose the <code>extension</code> folder of this project.</li>
          <li><strong>Pin it</strong> so ApplyPilot sits next to the address bar.</li>
          <li><strong>Open the form page</strong> you want to fill.</li>
          <li>Click <strong>ApplyPilot → Scan this page</strong>. Sign in there once.</li>
          <li><strong>Check the rows.</strong> “Exact match” files are pre-picked; “Please choose” waits for you — preview first.</li>
          <li><strong>Fill / Attach</strong>, look at the green fields on the page, then submit yourself.</li>
        </ol>
      </Card>
      <div className="grid">
        <Card title="What it never does">
          <ul className="plain">
            <li>Never submits a form.</li>
            <li>Never fills passwords, captcha, OTP or ID fields.</li>
            <li>Never uploads a file without your click.</li>
            <li>Never stores your files — they are fetched only when you attach.</li>
          </ul>
        </Card>
        <Card title="Try it safely first">
          <p className="muted">Practice on the sample form that ships with the project (<code>samples/sample_form.html</code>): it has photo, signature and certificate fields, and nothing you do there is real.</p>
        </Card>
      </div>
    </AuthGate>
  );
}
