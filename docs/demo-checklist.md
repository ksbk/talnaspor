# Talnaspor demo checklist: Sunday 1 November, 20:00

Ten minutes per team. Print this page.

## Before the day (by Sunday 16:00)

- [ ] **Feature freeze at 12:00.** No code changes after this; only this checklist.
- [ ] **Give the judges access to the repository.** Either make it public:
      `gh repo edit ksbk/talnaspor --visibility public --accept-visibility-change-consequences`
      or invite the organizers: GitHub › Settings › Collaborators.
- [ ] **Share the slides** from the deck's Share menu, and export a **PDF copy** to the laptop.
- [ ] **Record a backup video** (2–3 minutes) of the live demo below: QuickTime › File ›
      New Screen Recording. Save it to the desktop.
- [ ] **Rehearse once to the clock** (timings below).
- [ ] **Spot-check five figures by hand** on px.hagstofa.is (for example the first three
      answers below), so “verified against the official source” is your own claim.

## At the venue (30 minutes before)

- [ ] Wi-Fi reaches Statistics Iceland (expect `200`):
      `curl -s -o /dev/null -w "%{http_code}\n" https://px.hagstofa.is/pxis/api/v1/is/`
- [ ] Phone hotspot ready as a fallback network.
- [ ] Update and check: `git pull && make sync && make check` (expect 309 tests passed).
- [ ] Start: `make run`, open <http://127.0.0.1:8000>, select **ÍS**.
- [ ] **Warm up within 10 minutes of presenting:** ask the demo questions once. Table
      metadata is cached for 10 minutes, so answers are fastest right after this.
- [ ] Browser zoom 125–150% for the projector; other tabs closed; Do Not Disturb on.
- [ ] Slides open in Present mode in a second window; PDF and backup video on the desktop.

## Timing (10 minutes)

| Minutes | Slides | What |
|---|---|---|
| 0–2.5 | 1–3 | Talnaspor, the problem, how a question becomes a verified figure |
| 2.5–7 | 4–5 | **Live demo** (below) |
| 7–9.5 | 6–7 | Evidence, limitations, next steps |
| 9.5–10 | | Thank you; repository link |

## Live demo: pace it, about one question every 15 seconds

Statistics Iceland allows about 30 requests per 10 seconds, and one catalog question can
use 10–20 of them. Results below are as of 30 October 2026; a “latest” figure changes only
when Statistics Iceland publishes new data, and the card always shows the period.

| # | Lang | Type or click | Expect | Shows |
|---|---|---|---|---|
| 1 | ÍS | Hver er verðbólgan núna? | **5,9%**, október 2026 | Value, unit, period, source, response time |
| 2 | ÍS | *Open the table link on card 1* | Hagstofa’s CPI table | Check the figure at the source |
| 3 | EN | *Switch to EN.* How has Iceland’s population changed? | **+68,288 people (+20.9%)**, 2016 → 2026 | Comparison, English answer |
| 4 | ÍS | Hversu margir eru atvinnulausir á Íslandi? | **15.400**, 2. ársfjórðungur 2026 | Any table: “selected automatically” and every chosen value |
| 5 | ÍS | *Open “Sýna fyrirspurn til Hagstofu”* | The table and selections | Track 2 table selection |
| 6 | ÍS | Verðbólga árið 2024 | “Tilgreindu mánuð …” | Ambiguous query → focused question |
| 7 | EN | What was inflation in January 2030? | “… covers May 1988 to October 2026.” | Unavailable data, explained |
| 8 | EN | What is the capital of Iceland? | “I could not find an answer …” | Not statistics → not found |

Spare if time allows: “Hvernig hefur verðbólgan þróast síðustu tíu árin?” → **+4,1 prósentustig**
(1,8% → 5,9%).

## If something goes wrong

| Problem | Do this |
|---|---|
| Red card “Ekki náðist samband við Hagstofu” / “could not be reached” | Switch to the phone hotspot and ask again. Still failing: play the backup video. |
| An answer is slow or fails after several quick questions | Rate limit: wait 10–15 seconds and ask again. Say so: it is Statistics Iceland’s limit. |
| The page shows the wrong language | Click **ÍS** or **EN**; the choice is remembered. |
| The page looks out of date | Hard reload: Cmd+Shift+R. |
| Port 8000 is busy | `uv run --locked uvicorn talnaspor.app:app --port 8001` and open port 8001. |
| The server will not start | `uv sync --locked`, then `make run` again. Else: PDF slides plus backup video. |
| A figure differs from this sheet | Read the period on the card: Statistics Iceland has published new data. Open the table link to show it. |
| A question gets suggestions instead of an answer | That is designed behaviour: say Talnaspor answers only when it can verify every selection, and open a suggested table. |
