# Evaluation results

Run on 2026-10-30 against the live PX-Web API. Expected values recorded 2026-10-30.

**33 questions: 3 KNOWN LIMITATION, 30 PASS.**

Expected values were fetched independently of Talnaspor's query and decoding code (`scripts/fetch_expected.py`). KNOWN LIMITATION marks a question that behaves as documented below but is not answered well. STALE means Statistics Iceland has published a newer period since the values were recorded.

| ID | Question | Expected | Result | Shown | ms |
|---|---|---|---|---|---:|
| cpi-01 | Hver var verðbólgan í september 2026? | answer | PASS | 5,9% | 92 |
| cpi-02 | Hver var verðbólgan í janúar 2025? | answer | PASS | 4,6% | 76 |
| cpi-03 | What was inflation in May 2025? | answer | PASS | 3,8% | 77 |
| cpi-04 | Verðbólga án húsnæðis í mars 2026 | answer | PASS | 4,9% | 72 |
| cpi-05 | Hver var mánaðarbreyting vísitölu neysluverðs í ágúst 2026? | answer | PASS | 0,2% | 142 |
| cpi-06 | Hver var vísitala neysluverðs í desember 2024? | answer | PASS | 637,2 stig | 82 |
| cpi-07 | What was the consumer price index in June 2025? | answer | PASS | 656,5 stig | 79 |
| cpi-08 | What was the monthly change in the CPI in September 2026? | answer | PASS | 0,39% | 81 |
| cpi-09 | Hver er verðbólgan núna? | answer | PASS | 5,9% | 78 |
| cpi-10 | Hver er verðbólgan án húsnæðis? | answer | PASS | 5,9% | 77 |
| cpi-11 | Verðbólga í september 2025 og 2026 | comparison | PASS | 4,1% → 5,9% | 229 |
| cpi-12 | Breyting vísitölu neysluverðs frá janúar 2025 til september 2026 | comparison | PASS | 635,5 stig → 697,3 stig | 80 |
| cpi-13 | Hvernig hefur verðbólgan þróast? | comparison | PASS | 4,3% → 5,9% | 87 |
| pop-01 | Hvað búa margir á Íslandi? | answer | PASS | 394.324 íbúar | 135 |
| pop-02 | Hver var mannfjöldinn árið 2020? | answer | PASS | 354.042 íbúar | 91 |
| pop-03 | What was the population of Iceland in 2000? | answer | PASS | 279.049 íbúar | 77 |
| pop-04 | Hver var fjölgun íbúa árið 2024? | answer | PASS | 5.718 manns | 75 |
| pop-05 | Population growth rate in 2024 | answer | PASS | 1,49% | 72 |
| pop-06 | Hve margir aðfluttir umfram brottflutta 2023? | answer | PASS | 6.790 manns | 71 |
| pop-07 | Fæddir umfram dána á Íslandi 2023 | answer | PASS | 1.744 manns | 72 |
| pop-08 | Hvað fjölgaði íbúum mikið árið 2024? | answer | PASS | 5.718 manns | 76 |
| pop-09 | How has Iceland's population changed? | comparison | PASS | 326.036 íbúar → 394.324 íbúar | 84 |
| pop-10 | Hvernig hefur mannfjöldinn breyst frá 2015 til 2025? | comparison | PASS | 323.024 íbúar → 389.444 íbúar | 82 |
| pop-11 | Hvernig hefur mannfjöldinn breyst frá 2000? | comparison | PASS | 279.049 íbúar → 394.324 íbúar | 80 |
| clar-01 | Verðbólga árið 2024 | clarification | PASS | Tilgreindu mánuð, til dæmis „verðbólga í september 2026“. | 0 |
| clar-02 | Hver var breytingin á vísitölu neysluverðs í september 2026? | clarification | PASS | Viltu mánaðarbreytingu eða ársbreytingu? Til dæmis „mánaðarbreyting vísitölu neysluverðs í september 2026“. | 0 |
| clar-03 | Verðbólga og mannfjöldi árið 2024 | clarification | PASS | Spyrðu um eitt efni í einu. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 0 |
| clar-04 | Hvernig er veðrið? | clarification | PASS | Ég skildi ekki spurninguna. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 0 |
| ref-01 | Hver var fjölgun íbúa árið 2026? | refusal | PASS | Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands. | 81 |
| ref-02 | Hver var verðbólgan í janúar 2030? | refusal | PASS | Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands. | 41 |
| lim-01 | Hvað er verðlag að hækka mikið? | clarification (known limitation) | KNOWN LIMITATION | Ég skildi ekki spurninguna. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 0 |
| lim-02 | Hve margir bjuggu á Íslandi árið 1990? | clarification (known limitation) | KNOWN LIMITATION | Ég skildi ekki spurninguna. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 0 |
| lim-03 | What was inflation last year? | answer (known limitation) | KNOWN LIMITATION | 5,9% | 75 |

## Known limitations

- `lim-01`: "Verðlag" (price level) is not recognized as a CPI term.
- `lim-02`: The past tense "bjuggu" is not recognized as a population question.
- `lim-03`: Relative periods such as "last year" are ignored, so the latest month is answered instead (the period is shown).
