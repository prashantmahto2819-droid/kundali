"""One-off: add `marks` (signs on lines) and `extras` (counted lines) to data/knowledge/palm.json.
Own wording, tendency language; no health, lifespan, death or money predictions. Draft for a palmist's review.
Run:  cd engine && python tools/palm_marks_data.py
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "palm.json"

LINES = {"life": ("जीवन रेखा", "life line"), "head": ("मस्तिष्क रेखा", "head line"), "heart": ("हृदय रेखा", "heart line"), "fate": ("भाग्य रेखा", "fate line"), "sun": ("सूर्य रेखा", "sun line")}
MARKS = {
    "island": {"hi": "द्वीप", "en": "Island",
               "hi_t": "{line} पर द्वीप: उस दौर में ऊर्जा बँटी हुई और ध्यान छितरा हुआ रहने की प्रवृत्ति; एक समय में एक काम पर टिकना मदद करता है।",
               "en_t": "Island on the {line}: a phase where energy feels divided and attention scattered; staying with one thing at a time helps."},
    "break": {"hi": "टूट", "en": "Break",
              "hi_t": "{line} में टूट: दिशा या परिस्थिति में एक मोड़ का संकेत; परंपरा में साथ की समानांतर रेखा इसे सहारा देती मानी जाती है।",
              "en_t": "Break in the {line}: a turn in direction or circumstance; tradition reads an overlapping parallel line as support through it."},
    "chain": {"hi": "शृंखला (जंज़ीर)", "en": "Chain",
              "hi_t": "{line} शृंखलाबद्ध: मन या ऊर्जा का उतार-चढ़ाव; नियमित दिनचर्या और विश्राम की प्रवृत्ति सहायक।",
              "en_t": "Chained {line}: fluctuating mood or energy; routine and rest tend to steady it."},
    "cross": {"hi": "क्रॉस", "en": "Cross",
              "hi_t": "{line} पर क्रॉस: परंपरा में एक चुनौती या निर्णय-बिंदु; तर्जनी के नीचे का क्रॉस अपवाद रूप से शुभ माना गया है।",
              "en_t": "Cross on the {line}: traditionally a challenge or decision point; a cross under the index finger is the classic exception, read as fortunate."},
    "star": {"hi": "तारा", "en": "Star",
             "hi_t": "{line} पर तारा: किसी घटना या पहचान के अचानक उभार का चिह्न; सूर्य रेखा/पर्वत पर यह प्रसिद्धि की प्रवृत्ति माना जाता है।",
             "en_t": "Star on the {line}: a sudden surge of an event or recognition; on the sun line/mount it is read as a tendency to fame."},
    "fork": {"hi": "द्विशाखा (काँटा)", "en": "Fork",
             "hi_t": "{line} के अंत में काँटा: एक से अधिक रुचियाँ या दृष्टिकोण साथ चलना; मस्तिष्क रेखा पर इसे 'लेखक का काँटा' कहते हैं (कल्पना + व्यावहारिकता)।",
             "en_t": "Fork at the end of the {line}: more than one interest or outlook running together; on the head line it is the 'writer's fork' (imagination plus practicality)."},
    "square": {"hi": "वर्ग", "en": "Square",
               "hi_t": "{line} पर वर्ग: परंपरा में रक्षा-चिह्न, यानी कठिन दौर में बचाव या संभलने की प्रवृत्ति।",
               "en_t": "Square on the {line}: traditionally a mark of protection, a tendency to recover or be shielded through a hard phase."},
    "triangle": {"hi": "त्रिभुज", "en": "Triangle",
                 "hi_t": "{line} पर त्रिभुज: बुद्धि और कौशल के अच्छे उपयोग का संकेत; संबंधित क्षेत्र में दक्षता।",
                 "en_t": "Triangle on the {line}: a sign of good use of intellect and skill, competence in the related area."},
    "branch_up": {"hi": "ऊपर की शाखा", "en": "Upward branch",
                  "hi_t": "{line} से ऊपर की ओर शाखा: प्रयास और आकांक्षा का उभार, उस दौर में उन्नति की प्रवृत्ति।",
                  "en_t": "Upward branch from the {line}: a rise of effort and aspiration, a tendency to progress in that phase."},
    "branch_down": {"hi": "नीचे की शाखा", "en": "Downward branch",
                    "hi_t": "{line} से नीचे की ओर शाखा: उस दौर में ऊर्जा का बिखराव या थकान की प्रवृत्ति; विश्राम का महत्व।",
                    "en_t": "Downward branch from the {line}: a tendency to dispersal or tiredness in that phase; rest matters."},
}
EXTRAS = {
    "union_lines": {"hi": "संबंध रेखाएँ (कनिष्ठा के नीचे, हथेली के किनारे)", "en": "Union lines (edge of the palm under the little finger)",
                    "bands": [(0, "कोई स्पष्ट नहीं: लगाव भीतर रहता है, दिखावे में कम।", "None clear: attachment stays inward, little shown outwardly."),
                              (1, "एक गहरी: एक प्रमुख गहरे लगाव की प्रवृत्ति।", "One deep line: a tendency to one dominant deep attachment."),
                              (2, "दो: एक से अधिक महत्वपूर्ण लगाव या एक संबंध के दो चरण; यह विवाहों की गिनती नहीं है।", "Two: more than one significant attachment or two phases of one bond; this is not a count of marriages."),
                              (3, "कई हल्की: मिलनसार स्वभाव, कई मित्रताएँ और जुड़ाव।", "Several light lines: a sociable nature with many friendships and connections.")]},
    "bracelets": {"hi": "मणिबंध रेखाएँ (कलाई पर)", "en": "Bracelets (rascettes on the wrist)",
                  "bands": [(0, "अस्पष्ट: परंपरा में इसे सिर्फ़ सहनशक्ति का एक सूचक माना जाता है, और कुछ नहीं।", "Unclear: tradition takes these as only a rough marker of stamina, nothing more."),
                            (1, "एक स्पष्ट: आधारभूत सहनशक्ति।", "One clear: basic stamina."),
                            (2, "दो: अच्छी सहनशक्ति और स्थिरता की प्रवृत्ति।", "Two: good stamina and steadiness."),
                            (3, "तीन या अधिक: परंपरा में 'भाग्यशाली' मानी गईं; हम इसे स्थिर ऊर्जा का संकेत भर पढ़ते हैं।", "Three or more: called 'fortunate' in tradition; we read it only as steady energy.")]},
    "travel_lines": {"hi": "यात्रा रेखाएँ (हथेली के बाहरी किनारे, चंद्र पर्वत पर)", "en": "Travel lines (outer edge of the palm, on the mount of the Moon)",
                     "bands": [(0, "कोई नहीं: बदलाव घर के पास ही अधिक।", "None: change happens mostly close to home."),
                               (1, "एक-दो: कुछ यादगार यात्राएँ या स्थान-परिवर्तन।", "One or two: a few memorable journeys or relocations."),
                               (3, "कई: घूमने-फिरने, नई जगहों और बदलाव की प्रवृत्ति।", "Several: a tendency to travel, new places and change.")]},
    "girdle_of_venus": {"hi": "शुक्र मेखला (हृदय रेखा के ऊपर अर्धचंद्र)", "en": "Girdle of Venus (arc above the heart line)",
                        "bands": [(0, "नहीं: भावनाएँ संतुलित ढंग से व्यक्त।", "Absent: feelings expressed in a measured way."),
                                  (1, "है: तीव्र संवेदनशीलता और भावनात्मक गहराई; कला और सहानुभूति की ओर झुकाव।", "Present: heightened sensitivity and emotional depth; a pull towards art and empathy.")]},
}


def main():
    d = json.loads(P.read_text(encoding="utf-8"))
    d["lines"] = {k: {"hi": v[0], "en": v[1]} for k, v in LINES.items()}
    d["marks"] = MARKS
    d["extras"] = {k: {"hi": v["hi"], "en": v["en"], "bands": [{"min": b[0], "hi": b[1], "en": b[2]} for b in v["bands"]]} for k, v in EXTRAS.items()}
    d["trace_note_hi"] = ("फ़ोटो आपके फ़ोन/ब्राउज़र में ही रहती है; सर्वर को केवल आपके बनाए बिंदु भेजे जाते हैं। "
                          "माप हथेली की चौड़ाई-लंबाई के अनुपात में हैं; रेखा की गहराई और पर्वत आप स्वयं चुनिए।")
    d["trace_note"] = ("The photo stays in your phone/browser; only the points you draw are sent to the server. "
                       "Measurements are ratios of the palm's width and length; line depth and mounts are your own choices.")
    P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("marks", len(MARKS), "extras", len(EXTRAS))


if __name__ == "__main__":
    main()
