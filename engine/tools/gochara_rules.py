"""One-off: write data/rules/gochara.json — transit (gochara) tendencies for 9 planets x 12 houses from the Moon.

Own wording, tendency language, draft. Favourable houses follow the usual gochara lists; the texts for
other houses describe the classical caution without predicting illness, death or loss.
Run:  cd engine && python tools/gochara_rules.py
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "data" / "rules" / "gochara.json"

HOUSE_THEME = {1: ("self, body and mood", "स्वयं, शरीर और मन"), 2: ("family, speech and savings", "कुटुंब, वाणी और बचत"),
               3: ("effort, siblings and courage", "प्रयास, भाई-बहन और साहस"), 4: ("home, mother and peace of mind", "घर, माता और मन की शांति"),
               5: ("children, study and creativity", "संतान, विद्या और सृजन"), 6: ("work, rivals and routine", "काम, प्रतिद्वंद्वी और दिनचर्या"),
               7: ("partner and dealings with others", "जीवनसाथी और व्यवहार"), 8: ("sudden change and hidden matters", "अचानक बदलाव और छिपी बातें"),
               9: ("fortune, travel and guidance", "भाग्य, यात्रा और मार्गदर्शन"), 10: ("career and public standing", "कर्म और प्रतिष्ठा"),
               11: ("gains, friends and wishes", "लाभ, मित्र और इच्छाएँ"), 12: ("expense, rest and distant places", "व्यय, विश्राम और दूर के स्थान")}
PLANET = {"Sun": ("the Sun's transit (vitality, authority)", "सूर्य का गोचर (ऊर्जा, अधिकार)"), "Moon": ("the Moon's transit (mood, flow of days)", "चंद्र का गोचर (मन, दिनों का प्रवाह)"),
          "Mars": ("Mars's transit (drive, friction)", "मंगल का गोचर (ऊर्जा, टकराव)"), "Mercury": ("Mercury's transit (talk, trade, study)", "बुध का गोचर (बात, व्यापार, पढ़ाई)"),
          "Jupiter": ("Jupiter's transit (growth, grace)", "गुरु का गोचर (वृद्धि, कृपा)"), "Venus": ("Venus's transit (comfort, relationships)", "शुक्र का गोचर (सुख, संबंध)"),
          "Saturn": ("Saturn's transit (discipline, delay)", "शनि का गोचर (अनुशासन, विलंब)"), "Rahu": ("Rahu's transit (ambition, restlessness)", "राहु का गोचर (महत्वाकांक्षा, बेचैनी)"),
          "Ketu": ("Ketu's transit (detachment, insight)", "केतु का गोचर (वैराग्य, अंतर्दृष्टि)")}
FAV = {"Sun": {3, 6, 10, 11}, "Moon": {1, 3, 6, 7, 10, 11}, "Mars": {3, 6, 11}, "Mercury": {2, 4, 6, 8, 10, 11}, "Jupiter": {2, 5, 7, 9, 11},
       "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12}, "Saturn": {3, 6, 11}, "Rahu": {3, 6, 11}, "Ketu": {3, 6, 11}}
GOOD_EN = {"Sun": "tends to bring energy, recognition and a push to act", "Moon": "tends to keep the mind light and days flowing",
           "Mars": "tends to give courage, initiative and the will to compete", "Mercury": "tends to help talks, deals, learning and paperwork",
           "Jupiter": "tends to open doors, bring support and a sense of growth", "Venus": "tends to add comfort, charm and ease in relationships",
           "Saturn": "tends to reward steady work with slow, solid gains", "Rahu": "tends to feed ambition and unconventional gains",
           "Ketu": "tends to sharpen insight and loosen attachments helpfully"}
GOOD_HI = {"Sun": "ऊर्जा, पहचान और काम करने की प्रेरणा देने की प्रवृत्ति", "Moon": "मन को हल्का और दिनों को सहज रखने की प्रवृत्ति",
           "Mars": "साहस, पहल और प्रतिस्पर्धा की इच्छा देने की प्रवृत्ति", "Mercury": "बातचीत, सौदे, पढ़ाई और काग़ज़ी काम में मदद की प्रवृत्ति",
           "Jupiter": "रास्ते खोलने, सहारा और वृद्धि का भाव देने की प्रवृत्ति", "Venus": "सुख, आकर्षण और संबंधों में सहजता बढ़ाने की प्रवृत्ति",
           "Saturn": "लगातार मेहनत को धीमे पर पक्के लाभ से सींचने की प्रवृत्ति", "Rahu": "महत्वाकांक्षा और अनूठे लाभ बढ़ाने की प्रवृत्ति",
           "Ketu": "अंतर्दृष्टि तेज़ करने और मोह ढीला करने की प्रवृत्ति"}
CARE_EN = {"Sun": "calls for patience with authority figures and care of health routines", "Moon": "asks for a little extra care with mood and sleep",
           "Mars": "calls for restraint in anger, haste and arguments", "Mercury": "asks for double-checking words, figures and documents",
           "Jupiter": "asks not to over-expand or over-trust; growth comes slower here", "Venus": "asks for moderation in spending and indulgence",
           "Saturn": "asks for patience: delays, extra duties and tests of endurance are the classical caution", "Rahu": "asks for caution against confusion, shortcuts and over-reach",
           "Ketu": "asks for care with detachment turning into neglect"}
CARE_HI = {"Sun": "अधिकारियों से धैर्य और स्वास्थ्य-दिनचर्या की देखभाल माँगता है", "Moon": "मन और नींद की थोड़ी अतिरिक्त देखभाल माँगता है",
           "Mars": "क्रोध, जल्दबाज़ी और बहस में संयम माँगता है", "Mercury": "शब्द, आँकड़े और काग़ज़ दोबारा जाँचने को कहता है",
           "Jupiter": "अति-विस्तार और अति-विश्वास से बचने को कहता है; यहाँ वृद्धि धीमी होती है", "Venus": "ख़र्च और भोग में संयम माँगता है",
           "Saturn": "धैर्य माँगता है: विलंब, अतिरिक्त ज़िम्मेदारी और सहनशक्ति की परीक्षा शास्त्रीय सावधानी है", "Rahu": "भ्रम, शॉर्टकट और अति से सावधानी माँगता है",
           "Ketu": "वैराग्य के उपेक्षा में बदलने से सावधानी माँगता है"}


def main():
    rules = []
    for p, (pen, phi) in PLANET.items():
        for h in range(1, 13):
            ten, thi = HOUSE_THEME[h]
            good = h in FAV[p]
            en = (f"{pen[0].upper() + pen[1:]} in the {h}{'st' if h == 1 else 'nd' if h == 2 else 'rd' if h == 3 else 'th'} house from the Moon ({ten}): "
                  + (f"{GOOD_EN[p]}, especially in matters of {ten}." if good else f"{CARE_EN[p]}, especially in matters of {ten}."))
            hi = (f"{phi} चंद्र से {h}वें भाव में ({thi}): " + (f"{GOOD_HI[p]}, ख़ासकर {thi} के मामलों में।" if good else f"{CARE_HI[p]}, ख़ासकर {thi} के मामलों में।"))
            rules.append({"id": f"gochara_{p.lower()}_{h}", "category": "gochara", "when": {"planet": p, "house_from_moon": h},
                          "favourable": good, "text_en": en, "text_hi": hi,
                          "source": {"text": "Common gochara favourable-house lists (Phaladeepika / Brihat Samhita tradition); wording original", "chapter": None, "verse": None},
                          "review_status": "draft"})
    P.write_text(json.dumps({"_comment": "Transit (gochara) tendencies from the Moon sign, 9 planets x 12 houses. Own wording, tendency language; draft. Vedha not applied in the text.",
                             "rules": rules}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", len(rules))


if __name__ == "__main__":
    main()
