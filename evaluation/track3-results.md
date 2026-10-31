# Track 3 benchmark: an external check

The Gagnaþon 2026 Track 3 starter's 60 bilingual, source-backed questions ([questions/examples.jsonl](https://github.com/SyedMuhammadAzhar/gagnvist-starter/blob/main/questions/examples.jsonl), fetched 31 October 2026), each asked through `/ask` in its own language on 31 October 2026. CORRECT: the expected figure. SAFE: a clarification, suggestions or a refusal. WRONG: any other figure. Hard questions ask two things at once or need a ratio, which Talnaspor does not calculate.

| Level | Before: correct | safe | wrong | After: correct | safe | wrong |
|---|---:|---:|---:|---:|---:|---:|
| easy | 8 | 9 | 3 | 14 | 6 | 0 |
| medium | 1 | 18 | 1 | 2 | 18 | 0 |
| hard | 0 | 20 | 0 | 0 | 20 | 0 |
| **All 60** | 9 | 47 | 4 | 16 | 44 | 0 |

The four wrong answers before the fixes, and what changed:

- *How many immigrants…* (2): answered from a table titled “Innflytjendur” whose total also counts the second generation (85,577, against 77,226 immigrants). Immigrant questions now use the background table; that table is never used.
- *How many children were born in 2024?*: answered from children in preschools. Birth questions try the live-births table first.
- *Hver var launavísitalan í ágúst 2026?*: answered from the wage index for mortgage adjustment. An index table's level is now its default measure.

A question asking two things now gets “ask one question at a time”: after the fixes, one was read as a comparison of its two years.

These questions guided the fixes, so this is no longer an unseen test.

| Level | Lang | Question | Result | Shown | Expected |
|---|---|---|---|---|---|
| easy | EN | How many people lived in Iceland on 1 January 2026? | CORRECT | 394,324 people | 394324 |
| easy | IS | Hve margir bjuggu á Íslandi 1. janúar 2026? | CORRECT | 394.324 íbúar | 394324 |
| easy | EN | How many people lived in Reykjavík on 1 January 2026? | CORRECT | 139,804 (Number) | 139804 |
| easy | IS | Hve margir bjuggu í Reykjavík 1. janúar 2026? | CORRECT | 139.804 (Fjöldi) | 139804 |
| easy | EN | How many children were born in Iceland in 2024? | CORRECT | 4,311 (Number) | 4311 |
| easy | IS | Hve mörg börn fæddust á Íslandi árið 2024? | CORRECT | 4.311 (Fjöldi) | 4311 |
| easy | EN | What was the consumer price index in September 2026? | CORRECT | 697.3 points | 697.3 |
| easy | IS | Hver var vísitala neysluverðs í september 2026? | CORRECT | 697,3 stig | 697.3 |
| easy | EN | What was the wage index in August 2026? | CORRECT | 1,149.3 (Index/percent) | 1149.3 |
| easy | IS | Hver var launavísitalan í ágúst 2026? | CORRECT | 1.149,3 (Vísitala/hlutfall) | 1149.3 |
| easy | EN | What was the unemployment rate in Iceland in the second quarter of 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 6.5 |
| easy | IS | Hvert var atvinnuleysi á Íslandi á öðrum ársfjórðungi 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 6.5 |
| easy | EN | What was Iceland's gross domestic product in 2025? | CORRECT | 4,941,211 (Million ISK) | 4.94121e+06 |
| easy | IS | Hver var verg landsframleiðsla á Íslandi árið 2025? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 4.94121e+06 |
| easy | EN | How many overnight stays were there in registered accommodation in Iceland in 2025? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 9.85043e+06 |
| easy | IS | Hve margar gistinætur voru á skráðum gististöðum á Íslandi árið 2025? | CORRECT | 9.850.428 (Fjöldi) | 9.85043e+06 |
| easy | EN | How many immigrants lived in Iceland on 1 January 2026? | CORRECT | 77,226 (Number) | 77226 |
| easy | IS | Hve margir innflytjendur bjuggu á Íslandi 1. janúar 2026? | CORRECT | 77.226 (Fjöldi) | 77226 |
| easy | EN | How many valid votes did Vigdís Finnbogadóttir get in Reykjavík in the 1980 presidential election? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 15594 |
| easy | IS | Hve mörg gild atkvæði fékk Vigdís Finnbogadóttir í Reykjavík í forsetakjörinu 1980? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 15594 |
| medium | EN | By how many people did the population of Reykjavík grow from 1 January 2025 to 1 January 2026? | CORRECT | +1,032 (Number) | 1032 |
| medium | IS | Um hve marga fjölgaði íbúum Reykjavíkur frá 1. janúar 2025 til 1. janúar 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 1032 |
| medium | EN | What percentage of Iceland's population lived in Reykjavík on 1 January 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 35.4541 |
| medium | IS | Hve stórt hlutfall landsmanna bjó í Reykjavík 1. janúar 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 35.4541 |
| medium | EN | How many people lived in Reykjavík and Kópavogur together on 1 January 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 180090 |
| medium | IS | Hve margir bjuggu samtals í Reykjavík og Kópavogi 1. janúar 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 180090 |
| medium | EN | How many more men than women lived in Iceland on 1 January 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 10254 |
| medium | IS | Hve mörgum fleiri karlar en konur bjuggu á Íslandi 1. janúar 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 10254 |
| medium | EN | By how many points did the consumer price index rise from September 2025 to September 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 39 |
| medium | IS | Um hve mörg stig hækkaði vísitala neysluverðs frá september 2025 til september 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 39 |
| medium | EN | By what percentage did the number of overnight stays in registered accommodation in Iceland increase from 2024 to 2025? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 5.77473 |
| medium | IS | Um hve mörg prósent fjölgaði gistinóttum á skráðum gististöðum á Íslandi frá 2024 til 2025? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 5.77473 |
| medium | EN | What percentage of Iceland's population on 1 January 2026 were women? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 48.6724 |
| medium | IS | Hve stórt hlutfall landsmanna 1. janúar 2026 voru konur? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 48.6724 |
| medium | EN | By how many points did the wage index rise from August 2025 to August 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 61.6 |
| medium | IS | Um hve mörg stig hækkaði launavísitalan frá ágúst 2025 til ágúst 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 61.6 |
| medium | EN | By how many people did the number of immigrants living in Iceland grow from 1 January 2025 to 1 January 2026? | CORRECT | +3,430 (Number) | 3430 |
| medium | IS | Um hve marga fjölgaði innflytjendum á Íslandi frá 1. janúar 2025 til 1. janúar 2026? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 3430 |
| medium | EN | What percentage of the overnight stays in registered accommodation in Iceland in 2025 were by foreigners? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 86.8346 |
| medium | IS | Hve stórt hlutfall gistinátta á skráðum gististöðum á Íslandi árið 2025 voru gistinætur útlendinga? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 86.8346 |
| hard | EN | How many people lived in Iceland on 1 January 2026, and what was the consumer price index in September 2026? | SAFE | Please ask one question at a time: the first, then the secon | 394324; 697.3 |
| hard | IS | Hve margir bjuggu á Íslandi 1. janúar 2026 og hver var vísitala neysluverðs í september 2026? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 394324; 697.3 |
| hard | EN | What were the wage index and the consumer price index in August 2026? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 1149.3; 694.6 |
| hard | IS | Hver var launavísitalan og hver var vísitala neysluverðs í ágúst 2026? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 1149.3; 694.6 |
| hard | EN | How many overnight stays were there in registered accommodation in Iceland in 2025, and how many people lived in Iceland on 1 January 2025? | SAFE | Please ask one question at a time: the first, then the secon | 9.85043e+06; 389444 |
| hard | IS | Hve margar gistinætur voru á skráðum gististöðum á Íslandi árið 2025 og hve margir bjuggu á Íslandi 1. janúar 2025? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 9.85043e+06; 389444 |
| hard | EN | What was Iceland's gross domestic product in 2025, and how many children were born in Iceland in 2025? | SAFE | Please ask one question at a time: the first, then the secon | 4.94121e+06; 4387 |
| hard | IS | Hver var verg landsframleiðsla á Íslandi árið 2025 og hve mörg börn fæddust á Íslandi árið 2025? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 4.94121e+06; 4387 |
| hard | EN | How many overnight stays in registered accommodation were there in Iceland in 2025 per inhabitant on 1 January 2025? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 25.2936 |
| hard | IS | Hve margar gistinætur á skráðum gististöðum voru á Íslandi árið 2025 á hvern íbúa 1. janúar 2025? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 25.2936 |
| hard | EN | How many children were born in Iceland in 2025 per 1,000 inhabitants on 1 January 2025? | SAFE | I cannot answer this directly yet, but these Statistics Icel | 11.2648 |
| hard | IS | Hve mörg börn fæddust á Íslandi árið 2025 á hverja 1.000 íbúa 1. janúar 2025? | SAFE | Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagst | 11.2648 |
| hard | EN | What was the wage index in August 2026, and what was the unemployment rate in Iceland in the second quarter of 2026? | SAFE | Please ask one question at a time: the first, then the secon | 1149.3; 6.5 |
| hard | IS | Hver var launavísitalan í ágúst 2026 og hvert var atvinnuleysi á Íslandi á öðrum ársfjórðungi 2026? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 1149.3; 6.5 |
| hard | EN | What was Iceland's gross domestic product in 2025, and how many overnight stays were there in registered accommodation in Iceland in 2025? | SAFE | Please ask one question at a time: the first, then the secon | 4.94121e+06; 9.85043e+06 |
| hard | IS | Hver var verg landsframleiðsla á Íslandi árið 2025 og hve margar gistinætur voru á skráðum gististöðum á Íslandi árið 2025? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 4.94121e+06; 9.85043e+06 |
| hard | EN | How many children were born in Iceland in 2025, and how many immigrants lived in Iceland on 1 January 2026? | SAFE | Please ask one question at a time: the first, then the secon | 4387; 77226 |
| hard | IS | Hve mörg börn fæddust á Íslandi árið 2025 og hve margir innflytjendur bjuggu á Íslandi 1. janúar 2026? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 4387; 77226 |
| hard | EN | What was the consumer price index in September 2026, and what was the unemployment rate in Iceland in the second quarter of 2026? | SAFE | Please ask one question at a time: the first, then the secon | 697.3; 6.5 |
| hard | IS | Hver var vísitala neysluverðs í september 2026 og hvert var atvinnuleysi á Íslandi á öðrum ársfjórðungi 2026? | SAFE | Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og | 697.3; 6.5 |
