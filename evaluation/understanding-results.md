# Understanding evaluation

Run on 2026-10-31; expected values recorded 2026-10-31. Latency: live (194 new PX-Web requests).

CORRECT: the right figure, or a refusal where none should be given. SAFE: no answer where one exists (a clarification, suggestions or a refusal). WRONG: a figure that does not match an accepted cell, or a figure where none should be given. Coverage: correct answers among the answerable questions.

| Split | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |
|---|---:|---:|---:|---:|---|---:|---:|
| dev | 4 | 11 | 0 | 0 | 2/13 | 2685 | 9166 |
| holdout | 4 | 11 | 0 | 0 | 2/13 | 1815 | 8132 |

## By category (both splits)

| Category | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |
|---|---:|---:|---:|---:|---|---:|---:|
| change | 0 | 4 | 0 | 0 | 0/4 | 13 | 2685 |
| follow-up | 0 | 4 | 0 | 0 | 0/4 | 914 | 1865 |
| no answer | 4 | 0 | 0 | 0 | 0/0 | 1360 | 5990 |
| paraphrase | 3 | 9 | 0 | 0 | 3/12 | 4564 | 9166 |
| restriction | 1 | 5 | 0 | 0 | 1/6 | 1872 | 8132 |

## Dev questions

| ID | Lang | Category | Question | Result | Shown | ms |
|---|---|---|---|---|---|---:|
| d01 | EN | paraphrase | How many people live in Iceland right now? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 7379 |
| d02 | IS | paraphrase | Hve hátt var atvinnuleysið árið 2024? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 4085 |
| d03 | EN | paraphrase | How many hotel overnight stays were there in August 2025? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 9166 |
| d04 | IS | paraphrase | Hversu mörg börn fæddust árið 2025? | CORRECT | 4.387 (2025, Lifandi fædd börn eftir aldursflokki móður og hjús) | 1818 |
| d05 | IS | paraphrase | Hverjar eru lífslíkur kvenna á Íslandi? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 3680 |
| d06 | EN | paraphrase | What is the latest consumer price index value? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 6826 |
| d07 | EN | restriction | What was the unemployment rate for women in 2025? | CORRECT | 4.3 (2025, Activity rate, unemployment, labour force and work) | 932 |
| d08 | IS | restriction | Hve margar konur bjuggu á Íslandi 1. janúar 2026? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 4724 |
| d09 | IS | restriction | Hvert var atvinnuleysi ungs fólks (16-24 ára) árið 2025? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 2321 |
| d10 | EN | change | How did unemployment change between 2020 and 2025? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 13 |
| d11 | EN | change | What was food inflation in September 2026? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 2685 |
| d12 | EN | follow-up | (What is the population of Iceland in 2026?) → What about women? | SAFE | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 450 |
| d13 | IS | follow-up | (Hvert var atvinnuleysi árið 2025?) → En hjá körlum? | SAFE | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 1378 |
| d14 | IS | no answer | Mun verðbólgan lækka á næsta ári? | CORRECT | suggestions: Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands fjalla líklega um  | 2713 |
| d15 | EN | no answer | What about women? | CORRECT | suggestions: I cannot answer this directly yet, but these Statistics Iceland tables probably cover it: | 6 |
