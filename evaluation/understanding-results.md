# Understanding evaluation

Run on 2026-10-31; expected values recorded 2026-10-31. Latency: live (5 new PX-Web requests).

CORRECT: the right figure, or a refusal where none should be given. SAFE: no answer where one exists (a clarification, suggestions or a refusal). WRONG: a figure that does not match an accepted cell, or a figure where none should be given. Coverage: correct answers among the answerable questions.

| Split | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |
|---|---:|---:|---:|---:|---|---:|---:|
| dev | 7 | 8 | 0 | 0 | 5/13 | 10 | 523 |
| holdout | 5 | 10 | 0 | 0 | 3/13 | 14 | 906 |

## By category (both splits)

| Category | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |
|---|---:|---:|---:|---:|---|---:|---:|
| change | 0 | 4 | 0 | 0 | 0/4 | 9 | 10 |
| follow-up | 3 | 1 | 0 | 0 | 3/4 | 8 | 14 |
| no answer | 4 | 0 | 0 | 0 | 0/0 | 5 | 12 |
| paraphrase | 3 | 9 | 0 | 0 | 3/12 | 20 | 523 |
| restriction | 2 | 4 | 0 | 0 | 2/6 | 12 | 906 |

## Dev questions

| ID | Lang | Category | Question | Result | Shown | ms |
|---|---|---|---|---|---|---:|
| d01 | EN | paraphrase | How many people live in Iceland right now? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 523 |
| d02 | IS | paraphrase | Hve hátt var atvinnuleysið árið 2024? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 33 |
| d03 | EN | paraphrase | How many hotel overnight stays were there in August 2025? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 19 |
| d04 | IS | paraphrase | Hversu mörg börn fæddust árið 2025? | CORRECT | 4.387 (Fjöldi) (2025, Lifandi fædd börn eftir aldursflokki móður og hjús) | 8 |
| d05 | IS | paraphrase | Hverjar eru lífslíkur kvenna á Íslandi? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 8 |
| d06 | EN | paraphrase | What is the latest consumer price index value? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 21 |
| d07 | EN | restriction | What was the unemployment rate for women in 2025? | CORRECT | 4.3 (Number/percent) (2025, Activity rate, unemployment, labour force and work) | 13 |
| d08 | IS | restriction | Hve margar konur bjuggu á Íslandi 1. janúar 2026? | CORRECT | 191.927 (Fjöldi) (2026, Mannfjöldi eftir kyni og aldri 1841-2026) | 10 |
| d09 | IS | restriction | Hvert var atvinnuleysi ungs fólks (16-24 ára) árið 2025? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 12 |
| d10 | EN | change | How did unemployment change between 2020 and 2025? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 7 |
| d11 | EN | change | What was food inflation in September 2026? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 10 |
| d12 | EN | follow-up | (What is the population of Iceland in 2026?) → What about women? | CORRECT | 191,927 (Number) (2026, Population by sex and age 1841-2026) | 8 |
| d13 | IS | follow-up | (Hvert var atvinnuleysi árið 2025?) → En hjá körlum? | CORRECT | 4,4 (Fjöldi/hlutfall) (2025, Atvinnuþátttaka, atvinnuleysi 1991-2025) | 8 |
| d14 | IS | no answer | Mun verðbólgan lækka á næsta ári? | CORRECT | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 10 |
| d15 | EN | no answer | What about women? | CORRECT | clarification: I don't know which question this follows. Please ask the whole question, for example “What | 0 |
