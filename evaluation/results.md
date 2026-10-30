# Evaluation results

Run on 2026-10-30 against the live PX-Web API. Expected values recorded 2026-10-30.

**43 questions: 2 KNOWN LIMITATION, 41 PASS.**

Expected values were fetched independently of Talnaspor's query and decoding code (`scripts/fetch_expected.py`). KNOWN LIMITATION marks a question that behaves as documented below but is not answered well. STALE means Statistics Iceland has published a newer period since the values were recorded.

| ID | Question | Expected | Result | Shown | ms |
|---|---|---|---|---|---:|
| cpi-01 | Hver var verðbólgan í september 2026? | answer | PASS | 5,9% | 89 |
| cpi-02 | Hver var verðbólgan í janúar 2025? | answer | PASS | 4,6% | 82 |
| cpi-03 | What was inflation in May 2025? | answer | PASS | 3,8% | 75 |
| cpi-04 | Verðbólga án húsnæðis í mars 2026 | answer | PASS | 4,9% | 78 |
| cpi-05 | Hver var mánaðarbreyting vísitölu neysluverðs í ágúst 2026? | answer | PASS | 0,2% | 78 |
| cpi-06 | Hver var vísitala neysluverðs í desember 2024? | answer | PASS | 637,2 stig | 82 |
| cpi-07 | What was the consumer price index in June 2025? | answer | PASS | 656,5 stig | 79 |
| cpi-08 | What was the monthly change in the CPI in September 2026? | answer | PASS | 0,39% | 79 |
| cpi-09 | Hver er verðbólgan núna? | answer | PASS | 5,9% | 79 |
| cpi-10 | Hver er verðbólgan án húsnæðis? | answer | PASS | 5,9% | 78 |
| cpi-11 | Verðbólga í september 2025 og 2026 | comparison | PASS | 4,1% → 5,9% | 81 |
| cpi-12 | Breyting vísitölu neysluverðs frá janúar 2025 til september 2026 | comparison | PASS | 635,5 stig → 697,3 stig | 81 |
| cpi-13 | Hvernig hefur verðbólgan þróast? | comparison | PASS | 4,3% → 5,9% | 80 |
| cpi-14 | Hvað er verðlag að hækka mikið? | answer | PASS | 5,9% | 73 |
| pop-01 | Hvað búa margir á Íslandi? | answer | PASS | 394.324 íbúar | 77 |
| pop-02 | Hver var mannfjöldinn árið 2020? | answer | PASS | 354.042 íbúar | 72 |
| pop-03 | What was the population of Iceland in 2000? | answer | PASS | 279.049 íbúar | 78 |
| pop-04 | Hver var fjölgun íbúa árið 2024? | answer | PASS | 5.718 manns | 86 |
| pop-05 | Population growth rate in 2024 | answer | PASS | 1,49% | 87 |
| pop-06 | Hve margir aðfluttir umfram brottflutta 2023? | answer | PASS | 6.790 manns | 79 |
| pop-07 | Fæddir umfram dána á Íslandi 2023 | answer | PASS | 1.744 manns | 79 |
| pop-08 | Hvað fjölgaði íbúum mikið árið 2024? | answer | PASS | 5.718 manns | 80 |
| pop-09 | How has Iceland's population changed? | comparison | PASS | 326.036 íbúar → 394.324 íbúar | 88 |
| pop-10 | Hvernig hefur mannfjöldinn breyst frá 2015 til 2025? | comparison | PASS | 323.024 íbúar → 389.444 íbúar | 111 |
| pop-11 | Hvernig hefur mannfjöldinn breyst frá 2000? | comparison | PASS | 279.049 íbúar → 394.324 íbúar | 83 |
| pop-12 | Hve margir bjuggu á Íslandi árið 1990? | answer | PASS | 253.785 íbúar | 82 |
| pop-13 | Hver var mannfjöldinn í fyrra? | answer | PASS | 389.444 íbúar | 89 |
| find-01 | Hversu margir eru atvinnulausir á Íslandi? | suggestions | PASS | 5 töflur, t.d. Atvinnulausir eftir lengd atvinnuleitar 2003-2026 | 52 |
| find-02 | What is the unemployment rate? | suggestions | PASS | 5 töflur, t.d. Atvinnuþátttaka, starfandi, vinnulitlir og atvinnuleysi, hlutfall eftir ársfjórðungum 2003-2026 | 5 |
| find-03 | Hver er munurinn á launum karla og kvenna? | suggestions | PASS | 5 töflur, t.d. Óleiðréttur launamunur kynjanna 2008-2024 | 9 |
| find-04 | How many tourists visit Iceland? | suggestions | PASS | 5 töflur, t.d. Útgjöld erlendra ferðamanna á Íslandi eftir atvinnugreinum og tegund ferðamanna 2009-2025 | 3 |
| find-05 | Hver er landsframleiðslan? | suggestions | PASS | 5 töflur, t.d. Landsframleiðslan á mann 1980-2024 | 2 |
| find-06 | Hver er kosningaþátttaka? | suggestions | PASS | 5 töflur, t.d. Fjöldi sveitarfélaga eftir kosningaþátttöku 2002-2022 | 2 |
| find-07 | Hvað eru margir bílar á Íslandi? | suggestions | PASS | 5 töflur, t.d. Bílaeign og akstur eftir atvinnugreinum 2005-2024 | 4 |
| clar-01 | Verðbólga árið 2024 | clarification | PASS | Tilgreindu mánuð, til dæmis „verðbólga í september 2026“. | 0 |
| clar-02 | Hver var breytingin á vísitölu neysluverðs í september 2026? | clarification | PASS | Viltu mánaðarbreytingu eða ársbreytingu? Til dæmis „mánaðarbreyting vísitölu neysluverðs í september 2026“. | 0 |
| clar-03 | Verðbólga og mannfjöldi árið 2024 | clarification | PASS | Spyrðu um eitt efni í einu. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 0 |
| clar-04 | Hvernig er veðrið? | clarification | PASS | Ég skildi ekki spurninguna. Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum og um mannfjölda á Íslandi eftir árum. | 1 |
| clar-05 | What was inflation last year? | clarification | PASS | Verðbólga er birt eftir mánuðum. Tilgreindu mánuð, til dæmis „verðbólga í desember 2025“. | 0 |
| ref-01 | Hver var fjölgun íbúa árið 2026? | refusal | PASS | Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands. | 68 |
| ref-02 | Hver var verðbólgan í janúar 2030? | refusal | PASS | Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands. | 35 |
| lim-01 | Hvernig hefur mannfjöldinn breyst síðustu fimm ár? | clarification (known limitation) | KNOWN LIMITATION | Ég get ekki enn svarað um afstæð tímabil eins og „síðustu fimm ár“. Tilgreindu tímabil, til dæmis „september 2026“ eða „2020 og 2025“. | 0 |
| lim-02 | Hver var verðbólgan í síðasta mánuði? | clarification (known limitation) | KNOWN LIMITATION | Ég get ekki enn svarað um afstæð tímabil eins og „síðustu fimm ár“. Tilgreindu tímabil, til dæmis „september 2026“ eða „2020 og 2025“. | 0 |

## Known limitations

- `lim-01`: Relative periods other than "last year", such as "síðustu fimm ár", get a clarification instead of an answer.
- `lim-02`: "Last month" is ambiguous between the calendar month and the latest published month, so it gets a clarification.
