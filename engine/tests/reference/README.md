# Reference charts (the Phase-0 accuracy gate)

Put charts exported from a **trusted program** here, one JSON file each. The engine is then
compared against them:

```bash
cd engine
python tools/check_reference.py                     # all files, tolerance 1 arc-minute
python tools/check_reference.py --tol-arcmin 20     # looser, for the dev backend
```

## Settings to use in the reference program (so we compare like with like)
- Ayanamsa: **Lahiri (Chitrapaksha)**
- Nodes: **Mean node** (not true node)
- Houses: **Whole sign** (only the Lagna degree is compared)
- Only charts with a **reliable birth time**

## File format
```json
{
  "name": "Example person",
  "source": "Jagannatha Hora 8.0 (or the program/site you used)",
  "input": {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.1815, "lon": 79.9864},
  "expected": {
    "lagna": "Vrishabha 21°03′",
    "planets": {
      "Sun": "Vrishabha 2°10′45″", "Moon": "Makara 22°56′",
      "Mars": "Kumbha 25°45′", "Mercury": "Mesha 14°12′", "Jupiter": "Mithuna 16°09′",
      "Venus": "Meena 20°52′", "Saturn": "Makara 1°25′", "Rahu": "Makara 17°32′", "Ketu": "Karka 17°32′"
    },
    "moon_nakshatra": "Shravana",
    "birth_dasha_lord": "Moon",
    "balance_years": 5.2
  }
}
```
Sign names may be Sanskrit or English (Taurus/Vrishabha); degrees may be `2°10′45″`, `2:10:45`
or `2 10 45`. All keys under `expected` are optional: give what the program shows.
The numbers above are **only the format example** (they are this engine's own output, not a reference).
Files starting with `_` are ignored.
