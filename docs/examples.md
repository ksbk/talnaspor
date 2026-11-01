# Example questions

These are the four examples previously shown in the README, preserved from the existing
[demo checklist](demo-checklist.md) and [judges’ guide](judges-guide.md). The demonstration
figures are documented as checked on 31 October 2026; they are not a new evaluation run.
Live answers may change when Statistics Iceland publishes data. Always check the period
and selections shown on the answer card.

| Question | Recorded answer | Period | Unit | Source table |
|---|---|---|---|---|
| *Hver var verðbólgan í september 2026?* | 5,9% | September 2026 | % annual change | `VIS01000` |
| *What is the population of Reykjavík in 2026?* | 139,804 | 1 January 2026 | Number (people) | `MAN03270` |
| *Hvernig breyttist atvinnuleysi frá 2020 til 2025?* | −2,0 prósentustig (6,3 → 4,3) | 2020 → 2025 | Percentage points; endpoints are percentages | `VIN00911` |
| *Hver var verðbólgan árið 2024?* | Asks which month | 2024; month unresolved | No numerical answer | CPI topic (`VIS01000`); no completed query |

## Source selections and evidence

- **Inflation:** `Mánuður=2026M09`, `Vísitala=CPI`, `Liður=change_A`.
  The question, selections and 5.9 value are recorded as `cpi-01` in the
  [development question set](../evaluation/questions.json), with a passing row in the
  [30 October results](../evaluation/results.md).
- **Reykjavík population:** the development set's `cat-11` records `MAN03270`, period
  `2026`, and category labels `Hverfi=Alls`, `Aldur=Alls`, `Kyn=Alls`, with value 139804.
  That entry uses different wording from the example above. The exact example wording
  and table ID are documented in the judges’ guide; the external evaluation also records
  the same figure for Reykjavík on 1 January 2026. `cat-11` has no row in the older
  development results report, so this is not a claim that it passed that run.
- **Unemployment comparison:** the demo checklist documents the exact question and
  6.3 → 4.3 result. The development set's `cat-03` identifies `VIN00911` selections
  `Landsvæði=Alls`, `Kyn=Alls`, `Aldur=16-74 ára`, and
  `Hlutfall, %=Atvinnuleysi, % (af vinnuafli)` for the 2025 endpoint. The understanding
  report's development question `d10` records the same endpoints for an English
  comparison of 2020 and 2025. The displayed change is calculated as 4.3 − 6.3 = −2.0
  percentage points. These supporting records do not contain a full query for the exact
  Icelandic demonstration wording.
- **Clarification:** the judges’ guide documents the exact question and request for a
  month. The development set's `clar-01` records the shorter “Verðbólga árið 2024” and
  expects “Tilgreindu mánuð”. No numerical value or completed selections are claimed.

See [evaluation methodology](how-it-works.md#7-evaluation) for the distinction between
development results, recorded expectations and demonstration evidence.
