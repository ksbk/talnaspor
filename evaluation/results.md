# Evaluation results

Run on 2026-10-30 against the live PX-Web API. Expected values recorded 2026-10-30.

**62 questions: 2 KNOWN LIMITATION, 60 PASS.**

Expected values were fetched independently of Talnaspor's query and decoding code (`scripts/fetch_expected.py`). KNOWN LIMITATION marks a question that behaves as documented below but is not answered well. STALE means Statistics Iceland has published a newer period since the values were recorded.

| ID | Lang | Question | Expected | Result | Shown | ms |
|---|---|---|---|---|---|---:|
| cpi-01 | IS | Hver var verðbólgan í september 2026? | answer | PASS | 5,9% | 82 |
| cpi-02 | IS | Hver var verðbólgan í janúar 2025? | answer | PASS | 4,6% | 69 |
| cpi-03 | IS | What was inflation in May 2025? | answer | PASS | 3,8% | 73 |
| cpi-04 | IS | Verðbólga án húsnæðis í mars 2026 | answer | PASS | 4,9% | 76 |
| cpi-05 | IS | Hver var mánaðarbreyting vísitölu neysluverðs í ágúst 2026? | answer | PASS | 0,2% | 81 |
| cpi-06 | IS | Hver var vísitala neysluverðs í desember 2024? | answer | PASS | 637,2 stig | 77 |
| cpi-07 | IS | What was the consumer price index in June 2025? | answer | PASS | 656,5 stig | 81 |
| cpi-08 | IS | What was the monthly change in the CPI in September 2026? | answer | PASS | 0,39% | 80 |
| cpi-09 | IS | Hver er verðbólgan núna? | answer | PASS | 5,9% | 74 |
| cpi-10 | IS | Hver er verðbólgan án húsnæðis? | answer | PASS | 5,9% | 88 |
| cpi-11 | IS | Verðbólga í september 2025 og 2026 | comparison | PASS | 4,1% → 5,9% | 78 |
| cpi-12 | IS | Breyting vísitölu neysluverðs frá janúar 2025 til september 2026 | comparison | PASS | 635,5 stig → 697,3 stig | 73 |
| cpi-13 | IS | Hvernig hefur verðbólgan þróast? | comparison | PASS | 4,3% → 5,9% | 89 |
| cpi-14 | IS | Hvað er verðlag að hækka mikið? | answer | PASS | 5,9% | 62 |
| pop-01 | IS | Hvað búa margir á Íslandi? | answer | PASS | 394.324 íbúar | 67 |
| pop-02 | IS | Hver var mannfjöldinn árið 2020? | answer | PASS | 354.042 íbúar | 69 |
| pop-03 | IS | What was the population of Iceland in 2000? | answer | PASS | 279.049 íbúar | 72 |
| pop-04 | IS | Hver var fjölgun íbúa árið 2024? | answer | PASS | 5.718 manns | 71 |
| pop-05 | IS | Population growth rate in 2024 | answer | PASS | 1,49% | 68 |
| pop-06 | IS | Hve margir aðfluttir umfram brottflutta 2023? | answer | PASS | 6.790 manns | 78 |
| pop-07 | IS | Fæddir umfram dána á Íslandi 2023 | answer | PASS | 1.744 manns | 72 |
| pop-08 | IS | Hvað fjölgaði íbúum mikið árið 2024? | answer | PASS | 5.718 manns | 73 |
| pop-09 | IS | How has Iceland's population changed? | comparison | PASS | 326.036 íbúar → 394.324 íbúar | 96 |
| pop-10 | IS | Hvernig hefur mannfjöldinn breyst frá 2015 til 2025? | comparison | PASS | 323.024 íbúar → 389.444 íbúar | 68 |
| pop-11 | IS | Hvernig hefur mannfjöldinn breyst frá 2000? | comparison | PASS | 279.049 íbúar → 394.324 íbúar | 69 |
| pop-12 | IS | Hve margir bjuggu á Íslandi árið 1990? | answer | PASS | 253.785 íbúar | 85 |
| pop-13 | IS | Hver var mannfjöldinn í fyrra? | answer | PASS | 389.444 íbúar | 78 |
| cat-01 | IS | Hversu margir eru atvinnulausir á Íslandi? | catalog | PASS | 15.400 (Fjöldi/Hlutfall) | 153 |
| cat-02 | IS | What is the unemployment rate? | catalog | PASS | 4,3 (Fjöldi/hlutfall) | 122 |
| cat-03 | IS | Atvinnuleysi 16-74 ára | catalog | PASS | 4,3 (Fjöldi/hlutfall) | 163 |
| cat-04 | IS | Hver er munurinn á launum karla og kvenna? | catalog | PASS | 10,4 (%) | 130 |
| cat-05 | IS | Hver er landsframleiðslan? | catalog | PASS | 4.941.211 (Milljónir króna) | 215 |
| cat-06 | IS | Hver er kosningaþátttaka? | catalog | PASS | 80,2 (Fjöldi/hlutfall) | 216 |
| cat-07 | IS | Kosningaþátttaka 2024 fjöldi | catalog | PASS | 215.173 (Fjöldi/hlutfall) | 75 |
| cat-08 | IS | Kosningaþátttaka 2024 hlutfall | catalog | PASS | 80,2 (Fjöldi/hlutfall) | 301 |
| cat-09 | IS | Hversu margir voru atvinnulausir í september 2025? | catalog | PASS | 7.500 (Fjöldi/Hlutfall) | 170 |
| find-04 | IS | How many tourists visit Iceland? | suggestions | PASS | 5 töflur, t.d. Útgjöld erlendra ferðamanna á Íslandi eftir atvinnugreinum og tegund ferðamanna 2009-2025 | 301 |
| find-07 | IS | Hvað eru margir bílar á Íslandi? | suggestions | PASS | 5 töflur, t.d. Bílaeign og akstur eftir atvinnugreinum 2005-2024 | 303 |
| clar-01 | IS | Verðbólga árið 2024 | clarification | PASS | Tilgreindu mánuð, til dæmis „verðbólga í september 2026“. | 0 |
| clar-02 | IS | Hver var breytingin á vísitölu neysluverðs í september 2026? | clarification | PASS | Viltu mánaðarbreytingu eða ársbreytingu? Til dæmis „mánaðarbreyting vísitölu neysluverðs í september 2026“. | 0 |
| clar-03 | IS | Verðbólga og mannfjöldi árið 2024 | clarification | PASS | Spyrðu um eitt efni í einu. Spyrðu til dæmis um verðbólgu, mannfjölda, atvinnuleysi eða laun, og nefndu tímabil ef þú vilt. | 0 |
| clar-04 | IS | Hvernig er veðrið? | clarification | PASS | Ég fann ekki svar við þessari spurningu í gögnum Hagstofu Íslands. Spyrðu til dæmis um verðbólgu, mannfjölda, atvinnuleysi eða laun, og nefndu tímabil ef þú vilt. | 1 |
| clar-05 | IS | What was inflation last year? | clarification | PASS | Verðbólga er birt eftir mánuðum. Tilgreindu mánuð, til dæmis „verðbólga í desember 2025“. | 0 |
| ref-01 | IS | Hver var fjölgun íbúa árið 2026? | refusal | PASS | Hagstofa Íslands hefur ekki birt þessa tölu (merkt „..“ í töflunni). | 69 |
| ref-02 | IS | Hver var verðbólgan í janúar 2030? | refusal | PASS | Engin tala er til fyrir janúar 2030 í töflu Hagstofu Íslands. Taflan nær frá maí 1988 til október 2026. | 34 |
| en-01 | EN | What is inflation now? | answer | PASS | 5.9% | 75 |
| en-02 | EN | Inflation excluding housing in March 2026 | answer | PASS | 4.9% | 69 |
| en-03 | EN | How has Iceland's population changed? | comparison | PASS | 326,036 people → 394,324 people | 69 |
| en-04 | EN | What was the population increase in 2024? | answer | PASS | 5,718 people | 70 |
| en-05 | EN | How many people are unemployed in Iceland? | catalog | PASS | 15,400 (Number/percent) | 206 |
| en-06 | EN | What is the GDP of Iceland? | catalog | PASS | 4,941,211 (Million ISK) | 290 |
| en-07 | EN | Unemployment among women 2025 | catalog | PASS | 4.3 (Number/percent) | 128 |
| en-08 | EN | What is the gender pay gap? | catalog | PASS | 10.4 (%) | 128 |
| en-09 | EN | What was inflation in 2024? | clarification | PASS | Please name a month, for example “inflation in September 2026”. | 0 |
| en-10 | EN | Inflation and population in 2024 | clarification | PASS | Please ask about one topic at a time. Try asking about inflation, population, unemployment or wages, for example, and name a period if you like. | 0 |
| pop-14 | IS | Hvernig hefur mannfjöldinn breyst síðustu fimm ár? | comparison | PASS | 358.298 íbúar → 394.324 íbúar | 71 |
| cpi-15 | IS | Hvernig hefur verðbólgan þróast síðustu tíu árin? | comparison | PASS | 1,8% → 5,9% | 71 |
| ref-03 | IS | Hver var mannfjöldinn árið 1650? | refusal | PASS | Engin tala er til fyrir 1650 í töflu Hagstofu Íslands. Taflan nær frá 1703 til 2026. | 33 |
| en-11 | EN | How many people were unemployed in March 2025? | catalog | PASS | 8,500 (Number/percent) | 179 |
| en-12 | EN | What was inflation in January 2030? | refusal | PASS | Statistics Iceland's table has no figure for January 2030. It covers May 1988 to October 2026. | 35 |
| lim-02 | IS | Hver var verðbólgan í síðasta mánuði? | clarification (known limitation) | KNOWN LIMITATION | Ég get ekki enn svarað um afstæð tímabil eins og „í síðasta mánuði“. Tilgreindu tímabil, til dæmis „september 2026“ eða „2020 og 2025“. | 0 |
| lim-03 | IS | Atvinnuleysi kvenna 2025 | suggestions (known limitation) | KNOWN LIMITATION | 5 töflur, t.d. Atvinnuþátttaka, starfandi, vinnulitlir og atvinnuleysi, hlutfall eftir ársfjórðungum 2003-2026 | 272 |

## Known limitations

- `lim-02`: "Last month" is ambiguous between the calendar month and the latest published month, so it gets a clarification.
- `lim-03`: Answers from catalog tables need every dimension settled; here the best table also needs an age group, so Talnaspor asks for it instead of answering.
