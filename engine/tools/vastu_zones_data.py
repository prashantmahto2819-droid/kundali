"""One-off: write data/knowledge/vastu_zones.json — the 16-zone degree wheel and the 45 devatas of the
Vastu Purusha Mandala (81 padas). Own wording, tendency language, draft (a vastu practitioner should review
the zone themes and the room lists). Run:  cd engine && python tools/vastu_zones_data.py
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "vastu_zones.json"

# 16 zones of 22.5 deg each, zone centre at k*22.5 (N centred on 0 deg). Themes follow the common 16-zone
# school; the room lists are the almanac-level guidance used in the 8-direction table, split per zone.
ZONES = [
    ("N",   "उत्तर",            "North",            "जल",   "water", "धन-प्रवाह, अवसर, करियर की दिशा",            "flow of money, opportunity, career path",
     ["living", "office", "safe"], ["kitchen", "toilet", "staircase"]),
    ("NNE", "उत्तर-उत्तर-पूर्व", "North-north-east", "जल",   "water", "स्वास्थ्य-लाभ, रोग-निवारण की ऊर्जा",         "recovery and healing energy",
     ["pooja", "living", "borewell"], ["toilet", "kitchen", "store"]),
    ("NE",  "ईशान",             "North-east",       "जल",   "water", "स्पष्टता, ज्ञान, साधना, निर्णय",             "clarity, knowledge, meditation, decisions",
     ["pooja", "living", "study"], ["toilet", "kitchen", "master_bedroom", "staircase", "septic_tank"]),
    ("ENE", "पूर्व-उत्तर-पूर्व", "East-north-east",  "वायु", "air",   "मनोरंजन, ताज़गी, हल्कापन",                  "recreation, freshness, lightness",
     ["living", "study", "guest_bedroom"], ["toilet", "store"]),
    ("E",   "पूर्व",             "East",             "वायु", "air",   "सामाजिक जुड़ाव, नई शुरुआत, ऊर्जा",           "social connections, new beginnings, vitality",
     ["living", "entrance", "dining", "study"], ["toilet", "store"]),
    ("ESE", "पूर्व-दक्षिण-पूर्व", "East-south-east", "वायु", "air",   "मंथन, चिंतन, विश्लेषण",                     "churning, analysis, reflection",
     ["study", "store", "toilet"], ["pooja", "master_bedroom"]),
    ("SE",  "आग्नेय",            "South-east",       "अग्नि", "fire",  "अग्नि, पाचन, नक़दी-प्रवाह",                  "fire, digestion, cash flow",
     ["kitchen", "electrical", "generator"], ["pooja", "borewell", "master_bedroom"]),
    ("SSE", "दक्षिण-दक्षिण-पूर्व", "South-south-east", "अग्नि", "fire", "शक्ति, आत्मविश्वास, साहस",                "power, confidence, courage",
     ["kitchen", "gym", "children_bedroom"], ["pooja", "borewell"]),
    ("S",   "दक्षिण",            "South",            "अग्नि", "fire",  "विश्राम, यश, पहचान",                        "rest, fame, recognition",
     ["master_bedroom", "store", "staircase"], ["entrance", "pooja", "borewell"]),
    ("SSW", "दक्षिण-दक्षिण-पश्चिम", "South-south-west", "पृथ्वी", "earth", "व्यय, निष्कासन, त्याग",              "expense, disposal, letting go",
     ["toilet", "store", "staircase"], ["pooja", "safe", "kitchen"]),
    ("SW",  "नैऋत्य",            "South-west",       "पृथ्वी", "earth", "स्थिरता, संबंध, कौशल, जड़ें",             "stability, relationships, skills, roots",
     ["master_bedroom", "safe", "store"], ["toilet", "kitchen", "septic_tank", "entrance", "borewell"]),
    ("WSW", "पश्चिम-दक्षिण-पश्चिम", "West-south-west", "पृथ्वी", "earth", "शिक्षा, बचत, ज्ञान-संचय",             "education, savings, accumulated knowledge",
     ["study", "children_bedroom", "store"], ["toilet", "kitchen"]),
    ("W",   "पश्चिम",            "West",             "आकाश", "space", "लाभ, फल-प्राप्ति, संतुष्टि",                "gains, fulfilment, satisfaction",
     ["dining", "children_bedroom", "study"], ["pooja", "entrance"]),
    ("WNW", "पश्चिम-उत्तर-पश्चिम", "West-north-west", "आकाश", "space", "मनोभाव, मन की हलचल",                     "mood, emotional stirring",
     ["store", "toilet", "staircase"], ["master_bedroom", "pooja"]),
    ("NW",  "वायव्य",            "North-west",       "वायु", "air",   "सहयोग, गति, आवाजाही",                      "support, movement, comings and goings",
     ["guest_bedroom", "store", "toilet", "garage"], ["pooja", "safe", "master_bedroom"]),
    ("NNW", "उत्तर-उत्तर-पश्चिम", "North-north-west", "वायु", "air",   "आकर्षण, संबंधों की मिठास",                  "attraction, warmth in relationships",
     ["master_bedroom", "guest_bedroom", "living"], ["toilet", "kitchen", "store"]),
]

# 32 outer padas of the 9x9 mandala, clockwise from the north-east corner pad (NE corner = Isha / Shikhi).
OUTER_32 = [
    ("Isha", "ईश"), ("Parjanya", "पर्जन्य"), ("Jayanta", "जयंत"), ("Indra", "इंद्र"), ("Surya", "सूर्य"), ("Satya", "सत्य"), ("Bhrisha", "भृश"), ("Antariksha", "अंतरिक्ष"),
    ("Agni", "अग्निदेव"), ("Pusha", "पूषा"), ("Vitatha", "वितथ"), ("Grihakshata", "गृहक्षत"), ("Yama", "यम"), ("Gandharva", "गंधर्व"), ("Bhringaraja", "भृंगराज"), ("Mriga", "मृग"),
    ("Pitru", "पितृ"), ("Dauvarika", "दौवारिक"), ("Sugriva", "सुग्रीव"), ("Pushpadanta", "पुष्पदंत"), ("Varuna", "वरुण"), ("Asura", "असुर"), ("Shosha", "शोष"), ("Papayakshma", "पापयक्ष्मा"),
    ("Roga", "रोग"), ("Naga", "नाग"), ("Mukhya", "मुख्य"), ("Bhallata", "भल्लाट"), ("Soma", "सोम"), ("Bhujaga", "भुजग"), ("Aditi", "अदिति"), ("Diti", "दिति"),
]
INNER_8 = {"E": ("Aryama", "अर्यमा"), "SE": ("Savita", "सविता"), "S": ("Vivasvan", "विवस्वान"), "SW": ("Indra-Jaya", "इंद्र-जय"),
           "W": ("Mitra", "मित्र"), "NW": ("Rudra", "रुद्र"), "N": ("Prithvidhara", "पृथ्वीधर"), "NE": ("Apa", "आप")}
CENTRE = ("Brahma", "ब्रह्मा")


def main():
    zones = []
    for i, (key, hi, en, el_hi, el, th_hi, th, good, avoid) in enumerate(ZONES):
        c = i * 22.5
        zones.append({"key": key, "hi": hi, "en": en, "centre_deg": c, "from_deg": (c - 11.25) % 360, "to_deg": (c + 11.25) % 360,
                      "element_hi": el_hi, "element": el, "theme_hi": th_hi, "theme": th, "good_rooms": good, "avoid_rooms": avoid})
    extra_rooms = {
        "septic_tank": {"hi": "सेप्टिक टैंक", "en": "Septic tank"}, "electrical": {"hi": "बिजली का मीटर / पैनल", "en": "Electrical panel"},
        "generator": {"hi": "जनरेटर / इन्वर्टर", "en": "Generator / inverter"}, "gym": {"hi": "व्यायाम कक्ष", "en": "Gym"}, "safe": {"hi": "तिजोरी", "en": "Safe / locker"},
    }
    P.write_text(json.dumps({"_comment": "16-zone vastu wheel (22.5 deg each, N centred on 0) and the 45 devatas of the 81-pada Vastu Purusha Mandala. Own wording; draft.",
                             "review_status": "draft", "zones": zones,
                             "mandala": {"outer_32_clockwise_from_ne": [{"en": e, "hi": h} for e, h in OUTER_32],
                                         "inner_8": {k: {"en": e, "hi": h} for k, (e, h) in INNER_8.items()}, "centre": {"en": CENTRE[0], "hi": CENTRE[1]}},
                             "extra_rooms": extra_rooms}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", len(zones), "zones")


if __name__ == "__main__":
    main()
