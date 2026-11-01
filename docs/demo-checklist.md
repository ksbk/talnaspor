# Talnaspor demo checklist: Sunday 1 November, 20:00

Ten minutes per team. Print this page. For a short guide for the judges, see
[judges-guide.md](judges-guide.md).

## Before the day (by Sunday 16:00)

- [ ] **Feature freeze at 12:00.** No code changes after this; only this checklist.
- [ ] **Give the judges access to the repository.** Either make it public:
      `gh repo edit ksbk/talnaspor --visibility public --accept-visibility-change-consequences`
      or invite the organizers: GitHub › Settings › Collaborators.
- [ ] **Share the slides** from the deck's Share menu, and export a **PDF copy** to the laptop.
- [ ] **Record a backup video** (2–3 minutes) of the live demo below: QuickTime › File ›
      New Screen Recording. Save it to the desktop. If you play it, say that it is a
      recording and give the date it was made.
- [ ] **Rehearse once to the clock** (timings below).
- [ ] **Spot-check five figures by hand** on px.hagstofa.is (for example the first three
      answers below), so “verified against the official source” is your own claim.

## At the venue (30 minutes before)

- [ ] Wi-Fi reaches Statistics Iceland (expect `200`):
      `curl -s -o /dev/null -w "%{http_code}\n" https://px.hagstofa.is/pxis/api/v1/is/`
- [ ] Phone hotspot ready as a fallback network.
- [ ] Update and check: `git pull && make sync && make check` (expect 587 tests passed).
      `make check` makes no requests to Statistics Iceland.
- [ ] **Do not run `make evaluate` or any bulk testing on the demo day.** It sends hundreds
      of requests and can get the network address blocked for 10 minutes or more.
- [ ] Start without auto-reload, so no file change can restart it mid-demo:
      `uv run --locked uvicorn talnaspor.app:app`, open <http://127.0.0.1:8000>, select **ÍS**.
- [ ] **Warm up 15–45 minutes before presenting, slowly (one question every 30 seconds):**
      ask every demo question once. Responses are cached for an hour, so the live demo
      then makes no new requests to Statistics Iceland. Do not restart the server after
      warming up: the cache is in memory.
- [ ] Browser zoom 125–150% for the projector; other tabs closed; Do Not Disturb on.
- [ ] Slides open in Present mode in a second window; PDF and backup video on the desktop.

## Timing (10 minutes)

| Minutes | Slides | What |
|---|---|---|
| 0–2.5 | 1–3 | Talnaspor, the problem, how a question becomes a verified figure |
| 2.5–7 | 4–5 | **Live demo** (below) |
| 7–9.5 | 6–7 | Evidence, limitations, next steps |
| 9.5–10 | | Thank you; repository link |

## Live demo: pace it, about one question every 30 seconds

Statistics Iceland limits requests per network address. In testing it refused requests
(HTTP 429) after about 8 in 25 seconds, and after heavy use it blocked for 10 minutes or
more. One catalog question can make 10–20 requests. Talnaspor caches identical requests
for an hour and retries once, so warmed-up and repeated demo questions are safe. Results
below were verified on 31 October 2026; a figure changes only when Statistics Iceland
publishes new data, and the card always shows the period.

| # | Lang | Type | Expect | Shows |
|---|---|---|---|---|
| 1 | ÍS | Hver var verðbólgan í september 2026? | **5,9%** | Value, unit, period, source, response time |
| 2 | ÍS | *Open the table link on card 1* | Hagstofa’s CPI table | Check the figure at the source |
| 3 | EN | *Switch to EN.* How many people live in Iceland? | **394,324 people**, 2026 | English answer |
| 4 | EN | What is the population of Reykjavík in 2026? | **139,804** | Any of 2,102 tables; open “About the data” for every selection |
| 5 | ÍS | Hvernig breyttist atvinnuleysi frá 2020 til 2025? | **-2,0 prósentustig** (6,3 → 4,3) | Comparison from a catalog table |
| 6 | EN | What is the population of Iceland in 2026? | **394,324 people** | (sets up the follow-up) |
| 7 | EN | What about women? | **191,927**, “Understood as a follow-up …” | Follow-up, shown as understood |
| 8 | ÍS | Hver var verðbólgan árið 2024? | “Tilgreindu mánuð …” | Ambiguous → focused question |
| 9 | ÍS | Hver var mannfjöldinn árið 1650? | “… Taflan nær frá 1703 til 2026.” | Unavailable data, explained |
| 10 | EN | What is the capital of Iceland? | “I could not find an answer …” | Not statistics → not found |

Spare if time allows: “Inflation in September 2025 and 2026” → **+1.8 percentage points**;
in ÍS, “Hvað búa margir í Reykjavík?” then “En konur?” → **68.587**.

## Backup without the network

Every question above is recorded (`evaluation/recordings`) and can be answered with no
network at all:

```
uv run --locked python scripts/serve_recorded.py --port 8001
```

Open <http://127.0.0.1:8001> and keep to the questions above; others may get only
suggestions. **The page looks exactly as in a live demo.** It still says it is fetching
data from Statistics Iceland and shows a response time, and nothing on screen marks the
replay. So **say so before the first question**: “No network here, so these are Statistics
Iceland’s responses recorded on 31 October; nothing is fetched live, and the response times
are not live.” The backup video is the last resort, and is also announced as a recording.

## If something goes wrong

| Problem | Do this |
|---|---|
| Red card “Ekki náðist samband við Hagstofu” / “could not be reached” | Switch to the phone hotspot and ask again. Still failing: the recorded backup on port 8001 (above), then the backup video. |
| “Hagstofa Íslands takmarkar fjölda fyrirspurna” / “is limiting requests” | Rate limit. Ask a question you already asked (served from the cache), or wait a minute. Still blocked: play the backup video, and say that it is a recording and that the block is Statistics Iceland’s limit. |
| The page shows the wrong language | Click **ÍS** or **EN**; the choice is remembered. |
| The page looks out of date | Hard reload: Cmd+Shift+R. |
| Port 8000 is busy | `uv run --locked uvicorn talnaspor.app:app --port 8002` and open port 8002. |
| The server will not start | `uv sync --locked`, then `make run` again. Else: PDF slides plus backup video. |
| A figure differs from this sheet | Read the period on the card: Statistics Iceland has published new data. Open the table link to show it. |
| A question gets suggestions instead of an answer | That is designed behaviour: say Talnaspor answers only when it can verify every selection, and open a suggested table. |
