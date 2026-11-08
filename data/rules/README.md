# Rules (phalādeśa data)

Rules are **data**, not code, so a scholar can add and correct them without programming.

```json
{
  "id": "sun_in_10",
  "category": "planet_in_house",
  "when": {"planet": "Sun", "house": 10},
  "text_en": "...", "text_hi": "...",
  "source": {"text": "Brihat Parashara Hora Shastra", "chapter": 0, "verse": 0},
  "review_status": "draft"
}
```

* `when` keys (all must match): `planet`, `house` (1-12), `sign` (0-11), `dignity`
  (`exalted`/`debilitated`/`own`), `retrograde` (true/false).
* `source` must name the classical text, chapter and verse before a rule can become `reviewed`.
* Write the texts **in our own words**. Original Sanskrit verses are public domain; modern
  translations and commentaries usually are not, so never paste them.
* Everything starts as `draft`. Only a scholar's sign-off moves it to `reviewed`.
* `planet_in_house.json` holds the first full set (9 planets x 12 houses, Hindi, draft). English text, sign/dignity/aspect rules and exact citations are still to come.
