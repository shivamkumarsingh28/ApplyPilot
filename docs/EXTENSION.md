# Browser extension

Fills application forms from your ApplyPilot profile. **You** review every value and **you** press submit.

## Install (Chrome, Edge, Brave)

1. Make sure the backend is running.
2. Open `chrome://extensions`.
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and choose the `extension/` folder.
5. Pin the ApplyPilot icon.

## Use

1. Click the icon, enter the API address (default `http://localhost:8000/api/v1`) and sign in.
2. Open the form page. Try `samples/sample_form.html` first.
3. Click **Scan this page**. You see each field with the value we plan to fill.
4. Yellow rows need a look. Edit any value, untick what you do not want.
5. Click **Fill selected fields**. Filled fields get a blue outline (yellow if please-check).
6. Read the whole form, then submit it yourself.

## What it will never do

- Submit the form
- Fill password, captcha, OTP, file, ID-number or payment fields (they are shown as "skipped")
- Tick checkboxes (like "I declare...")
- Run on pages you did not open it on (it uses the `activeTab` permission, not "all websites")

## How it works

| File | Job |
|---|---|
| `manifest.json` | Permissions and entry points (Manifest V3) |
| `lib/fieldScanner.js` | Finds fields and works out their labels, including table-style government forms |
| `lib/filler.js` | Writes values like a person typing, so React and Vue forms notice |
| `content.js` | Receives "scan" and "fill" messages inside the page |
| `popup.html/.js/.css` | The small window: sign in, scan, review, fill |

The popup sends the field list to `POST /forms/map`. The backend matches each field to your profile and returns a value and a confidence.

## Using your own backend address

Chrome blocks requests to servers the extension has no permission for. `manifest.json` allows `http://localhost:8000/*`. For production, add your API address to `host_permissions`.

## Tests

```bash
cd extension && npm install && npm test
```

The tests run the scanner and filler on `samples/sample_form.html` in a simulated browser.

## Known limits

- Forms inside iframes or shadow DOM are not scanned yet.
- Some portals use custom dropdowns made of `<div>`s. These are not detected.
- Date formats are guessed from the placeholder. Always check dates.
