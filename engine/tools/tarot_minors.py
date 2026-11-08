"""One-off: write per-card minor arcana meanings into data/knowledge/tarot.json ("minors" key).

Original wording for this project (not copied from any deck book). Review status: draft.
Run:  cd engine && python tools/tarot_minors.py
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "tarot.json"

# (upright_en, reversed_en, upright_hi, reversed_hi)
M = {
"Wands": [
 ("A spark of a new venture or passion; the urge to begin.", "A plan that lacks fuel; a start that keeps getting postponed.",
  "नए काम या जोश की चिंगारी; शुरू करने की तड़प।", "ऐसी योजना जिसमें ईंधन नहीं; टलती हुई शुरुआत।"),
 ("Looking out from what you have built and planning the next step.", "Fear of leaving the known; plans stay on paper.",
  "जो बनाया है वहाँ से आगे देखना और अगला क़दम सोचना।", "जाने-पहचाने को छोड़ने का डर; योजना काग़ज़ पर ही रहती है।"),
 ("Early results arriving; widening your reach with others' help.", "Delays in what you sent out; expecting too much too soon.",
  "शुरुआती नतीजे आना; दूसरों की मदद से दायरा बढ़ाना।", "भेजे हुए काम में देर; बहुत जल्दी बहुत ज़्यादा की उम्मीद।"),
 ("A milestone to celebrate; a stable base, home or team.", "A celebration postponed; instability at home or in the team.",
  "मनाने लायक पड़ाव; स्थिर आधार, घर या टीम।", "टला हुआ उत्सव; घर या टीम में अस्थिरता।"),
 ("Healthy competition or friction that sharpens everyone.", "Pointless quarrels; energy wasted on being right.",
  "स्वस्थ प्रतिस्पर्धा या घर्षण जो सबको तराशे।", "बेमतलब झगड़े; सही साबित होने में ऊर्जा बर्बाद।"),
 ("Recognition after effort; a win others can see.", "Praise that feels hollow; a fall after pride.",
  "मेहनत के बाद पहचान; ऐसी जीत जो सब देखें।", "खोखली तारीफ़; घमंड के बाद गिरावट।"),
 ("Holding your ground against pressure; defending what you earned.", "Feeling overwhelmed; giving up a position too easily.",
  "दबाव के सामने डटे रहना; अपनी कमाई हुई जगह बचाना।", "दबाव में घिर जाना; जगह बहुत आसानी से छोड़ देना।"),
 ("Fast movement; messages, travel and things falling into place quickly.", "Rushing without direction; delays in messages or travel.",
  "तेज़ गति; संदेश, यात्रा और चीज़ों का जल्दी बैठना।", "दिशा के बिना जल्दबाज़ी; संदेश या यात्रा में देर।"),
 ("Tired but still standing; one more effort before the end.", "Exhaustion that asks for rest; defending against an imagined threat.",
  "थके हुए पर डटे हुए; अंत से पहले एक और प्रयास।", "थकान जो आराम माँगे; काल्पनिक ख़तरे से बचाव।"),
 ("Carrying too much by choice; responsibility near completion.", "Putting a burden down; delegating what was never yours.",
  "अपनी मर्ज़ी से बहुत कुछ उठाना; पूरी होने वाली ज़िम्मेदारी।", "बोझ उतारना; जो आपका नहीं था उसे सौंपना।"),
 ("Enthusiastic news or a fresh idea; eagerness to learn by doing.", "Hasty words; an idea without follow-through.",
  "उत्साही ख़बर या ताज़ा विचार; करके सीखने की ललक।", "जल्दबाज़ी के शब्द; बिना अमल का विचार।"),
 ("Bold action, travel, charging ahead with confidence.", "Recklessness; moving fast in the wrong direction.",
  "साहसी क़दम, यात्रा, आत्मविश्वास से आगे बढ़ना।", "लापरवाही; ग़लत दिशा में तेज़ी।"),
 ("Warm confidence and magnetism; leading by encouragement.", "Jealousy or self-doubt behind a bright face.",
  "गर्म आत्मविश्वास और आकर्षण; प्रोत्साहन से नेतृत्व।", "चमकते चेहरे के पीछे ईर्ष्या या आत्म-संदेह।"),
 ("Vision with authority; a leader who inspires action.", "Domineering; expecting others to run on your fire.",
  "अधिकार के साथ दृष्टि; ऐसा नेता जो काम करवा दे।", "दबंगई; दूसरों से अपनी आग पर दौड़ने की उम्मीद।"),
],
"Cups": [
 ("An opening of the heart; new feeling, compassion or creativity.", "Emotion held back; a cup not yet accepted.",
  "हृदय का खुलना; नई भावना, करुणा या सृजन।", "रोकी हुई भावना; प्याला जो अभी स्वीकार नहीं हुआ।"),
 ("A meeting of equals; mutual attraction or partnership.", "Imbalance in a bond; misunderstanding between two.",
  "बराबर वालों का मिलन; आपसी आकर्षण या साझेदारी।", "रिश्ते में असंतुलन; दो के बीच ग़लतफ़हमी।"),
 ("Friendship and shared joy; a community that celebrates you.", "Overindulgence; feeling left out of the group.",
  "मित्रता और साझा आनंद; ऐसा समुदाय जो आपको माने।", "अति; समूह से बाहर छूटा हुआ महसूस करना।"),
 ("Discontent despite plenty; an offer you have not noticed.", "Waking from apathy; ready to accept what is offered.",
  "बहुत होते हुए भी असंतोष; ऐसा प्रस्ताव जो दिखा नहीं।", "उदासीनता से जागना; जो मिला उसे लेने को तैयार।"),
 ("Grieving what was spilled while cups still stand behind you.", "Beginning to turn around; acceptance after loss.",
  "जो छलका उसका शोक, जबकि पीछे प्याले अब भी खड़े हैं।", "पलटकर देखना शुरू; नुक़सान के बाद स्वीकार।"),
 ("Nostalgia, innocence, a gift from the past or a childhood tie.", "Stuck in the past; refusing to grow out of old roles.",
  "स्मृति, मासूमियत, अतीत का उपहार या बचपन का नाता।", "अतीत में अटके; पुरानी भूमिकाओं से बाहर न आना।"),
 ("Many options and fantasies; choose with clear eyes.", "Clarity arriving; a choice finally made.",
  "कई विकल्प और कल्पनाएँ; साफ़ नज़र से चुनिए।", "स्पष्टता का आना; आख़िरकार चुनाव हो जाना।"),
 ("Walking away from what no longer satisfies, toward meaning.", "Fear of leaving; drifting without deciding.",
  "जो अब संतुष्ट न करे उसे छोड़कर अर्थ की ओर चलना।", "छोड़ने का डर; बिना तय किए बहते रहना।"),
 ("Contentment and a wish fulfilled; enjoy it without smugness.", "Satisfaction that fades; wanting more for its own sake.",
  "संतोष और पूरी हुई इच्छा; बिना अकड़ के इसे जिएँ।", "फीका पड़ता संतोष; बस और की चाह।"),
 ("Emotional harmony at home; a family or bond that feels whole.", "A picture of harmony that hides strain.",
  "घर में भावनात्मक सामंजस्य; परिवार या रिश्ता जो पूरा लगे।", "सामंजस्य की तस्वीर जिसके पीछे तनाव।"),
 ("A tender message or a creative impulse; intuition speaking softly.", "Emotional immaturity; a message that disappoints.",
  "कोमल संदेश या सृजनात्मक उमंग; धीरे बोलती अंतर्दृष्टि।", "भावनात्मक अपरिपक्वता; निराश करने वाला संदेश।"),
 ("A romantic or idealistic offer; following the heart gracefully.", "Moodiness; promises made in feeling, not kept in fact.",
  "रोमांटिक या आदर्शवादी प्रस्ताव; शालीनता से दिल की सुनना।", "मूड की उथल-पुथल; भावना में किए वादे जो निभे नहीं।"),
 ("Deep empathy and intuition; care that does not drown itself.", "Taking on everyone's feelings; emotional dependence.",
  "गहरी सहानुभूति और अंतर्दृष्टि; ऐसी देखभाल जो ख़ुद को न डुबोए।", "सबकी भावनाएँ ओढ़ लेना; भावनात्मक निर्भरता।"),
 ("Calm mastery of feeling; wise, steady support for others.", "Feelings suppressed until they leak out sideways; manipulation.",
  "भावना पर शांत पकड़; दूसरों को बुद्धिमान, स्थिर सहारा।", "दबी भावनाएँ जो तिरछे रास्ते निकलें; हेरफेर।"),
],
"Swords": [
 ("A breakthrough of clarity; truth cutting through confusion.", "A sharp idea misused; confusion or cruel words.",
  "स्पष्टता का उभार; सच का उलझन को काटना।", "तीखा विचार ग़लत इस्तेमाल; उलझन या कठोर शब्द।"),
 ("A stalemate; refusing to look at what must be decided.", "The blindfold comes off; a decision can no longer wait.",
  "गतिरोध; जो तय करना है उसे न देखना।", "पट्टी उतरती है; फ़ैसला अब टल नहीं सकता।"),
 ("Heartache from a painful truth; grief that needs naming.", "Beginning to heal; releasing an old hurt.",
  "कड़वे सच से दिल का दर्द; ऐसा शोक जिसे नाम देना हो।", "भरने की शुरुआत; पुरानी चोट को छोड़ना।"),
 ("Rest and recovery; a pause to think before acting.", "Restlessness; returning to action, ready or not.",
  "आराम और सँभलना; काम से पहले सोचने का विराम।", "बेचैनी; तैयार हों या न हों, काम पर लौटना।"),
 ("A win that costs more than it gives; conflict with no real victor.", "Letting go of a fight; making amends.",
  "ऐसी जीत जो देने से ज़्यादा लेती है; बिना विजेता का टकराव।", "लड़ाई छोड़ना; सुलह करना।"),
 ("Moving away from trouble toward calmer waters; a transition.", "Carrying the trouble with you; a move that is resisted.",
  "मुसीबत से शांत पानी की ओर जाना; बदलाव का सफ़र।", "मुसीबत साथ ले जाना; ऐसा बदलाव जिसका विरोध हो।"),
 ("Strategy or stealth; getting away with something, for now.", "A secret coming out; the cost of cleverness.",
  "रणनीति या चुपके का काम; फ़िलहाल बच निकलना।", "राज़ का खुलना; चालाकी की क़ीमत।"),
 ("Feeling trapped by your own thoughts; the way out is nearer than it looks.", "Loosening the binds; seeing the options again.",
  "अपने ही विचारों में बँधा महसूस करना; रास्ता जितना लगता है उससे पास है।", "बंधन ढीले होना; विकल्प फिर दिखना।"),
 ("Anxiety and sleepless worry; fears larger than the facts.", "The worst did not happen; worry starting to lift.",
  "चिंता और नींद उड़ाने वाली फ़िक्र; तथ्यों से बड़े डर।", "सबसे बुरा नहीं हुआ; चिंता हल्की होना।"),
 ("An ending that is final; the low point from which the sun rises.", "Recovery after collapse; refusing to stay down.",
  "ऐसा अंत जो अंतिम है; सबसे नीचे का बिंदु जहाँ से सूरज उगता है।", "टूटने के बाद उठना; गिरे रहने से इनकार।"),
 ("Curiosity and watchfulness; new information, questions asked.", "Gossip or snooping; talk without substance.",
  "जिज्ञासा और सतर्कता; नई जानकारी, पूछे गए सवाल।", "गपशप या ताक-झाँक; बिना सार की बातें।"),
 ("Direct, fast and argumentative; a rush toward the goal.", "Aggression without a plan; words that wound.",
  "सीधा, तेज़ और बहस करने वाला; लक्ष्य की ओर दौड़।", "बिना योजना का आक्रामक रुख़; घायल करने वाले शब्द।"),
 ("Clear perception and honest boundaries; independence earned.", "Coldness or bitterness; sharpness turned against oneself.",
  "साफ़ समझ और ईमानदार सीमाएँ; कमाई हुई स्वतंत्रता।", "ठंडापन या कड़वाहट; तीखापन ख़ुद के ख़िलाफ़।"),
 ("Intellectual authority; fair judgement, clear rules.", "Misuse of authority; cleverness without conscience.",
  "बौद्धिक अधिकार; निष्पक्ष निर्णय, स्पष्ट नियम।", "अधिकार का दुरुपयोग; बिना विवेक की चतुराई।"),
],
"Pentacles": [
 ("A tangible new opportunity: money, work, health or a seed to plant.", "An opportunity missed or mishandled; shaky foundations.",
  "ठोस नया अवसर: धन, काम, स्वास्थ्य या बोने लायक बीज।", "चूका या बिगड़ा अवसर; कमज़ोर नींव।"),
 ("Juggling priorities; adapting as resources shift.", "Dropping a ball; overcommitted and disorganised.",
  "प्राथमिकताओं की जुगलबंदी; साधन बदलने पर ढलना।", "कोई गेंद गिरना; ज़रूरत से ज़्यादा ज़िम्मेदारी और अव्यवस्था।"),
 ("Skilled work recognised; collaboration that builds something lasting.", "Sloppy work or a team that does not mesh.",
  "कुशल काम की पहचान; ऐसा सहयोग जो टिकाऊ चीज़ बनाए।", "लापरवाह काम या टीम जो जमे नहीं।"),
 ("Holding on to what you have; security, perhaps too tightly.", "Loosening the grip; spending or sharing more freely.",
  "जो है उसे थामे रहना; सुरक्षा, शायद कुछ ज़्यादा कसकर।", "पकड़ ढीली करना; खुले हाथ ख़र्च या साझा।"),
 ("Hardship or feeling left out in the cold; help is closer than it seems.", "Recovery from loss; finding support again.",
  "कठिनाई या ठंड में छूटा हुआ महसूस करना; मदद जितनी लगती है उससे पास।", "नुक़सान से उबरना; सहारा फिर मिलना।"),
 ("Giving and receiving in balance; generosity, charity, a fair deal.", "Strings attached; a lopsided exchange.",
  "देना और पाना संतुलन में; उदारता, दान, उचित सौदा।", "शर्तों वाली मदद; असंतुलित लेन-देन।"),
 ("Patient assessment of what you have grown; long-term thinking.", "Impatience with slow returns; effort in the wrong field.",
  "जो उगाया उसका धैर्य से आकलन; दूरगामी सोच।", "धीमे फल पर अधीरता; ग़लत खेत में मेहनत।"),
 ("Diligent practice; craftsmanship improving step by step.", "Repetitive work without growth; cutting corners.",
  "लगन से अभ्यास; क़दम-दर-क़दम निखरती कारीगरी।", "बिना विकास का दोहराव; काम में कोताही।"),
 ("Self-sufficiency and refined comfort earned by discipline.", "Comfort that depends on others; living beyond means.",
  "अनुशासन से कमाई आत्मनिर्भरता और सुरुचिपूर्ण सुख।", "दूसरों पर टिका आराम; हैसियत से ज़्यादा ख़र्च।"),
 ("Lasting wealth, family legacy and stability across generations.", "Family disputes over money; stability that feels confining.",
  "टिकाऊ संपन्नता, पारिवारिक विरासत और पीढ़ियों की स्थिरता।", "धन पर पारिवारिक विवाद; स्थिरता जो बाँधती लगे।"),
 ("A student's attitude; a practical new skill or small income.", "Procrastination; a lesson not applied.",
  "विद्यार्थी का रवैया; व्यावहारिक नया हुनर या छोटी आय।", "टालमटोल; सीख जो अमल में न आई।"),
 ("Reliable, methodical progress; slow but it arrives.", "Stuck in routine; stubborn about method.",
  "भरोसेमंद, क्रमबद्ध प्रगति; धीमी पर पहुँचती है।", "दिनचर्या में अटके; तरीक़े को लेकर ज़िद।"),
 ("Practical nurturing; abundance shared with warmth.", "Self-neglect while providing for others; materialism.",
  "व्यावहारिक पोषण; गर्मजोशी से बाँटी संपन्नता।", "दूसरों की देखभाल में ख़ुद की उपेक्षा; भौतिकवाद।"),
 ("Prosperity through steady management; a dependable provider.", "Greed or rigidity; worth measured only in money.",
  "स्थिर प्रबंधन से समृद्धि; भरोसेमंद पालक।", "लालच या जड़ता; मूल्य सिर्फ़ पैसे से नापना।"),
],
}


def main():
    d = json.loads(P.read_text(encoding="utf-8"))
    ranks = [r["name"] for r in d["ranks"]]
    minors = {}
    for suit, rows in M.items():
        assert len(rows) == 14, suit
        for i, (up, rev, up_hi, rev_hi) in enumerate(rows):
            minors[f"{suit.lower()}-{i + 1:02d}"] = {"rank": ranks[i], "suit": suit, "up": up, "rev": rev, "up_hi": up_hi, "rev_hi": rev_hi}
    d["minors"] = minors
    d["_note"] = ("Original wording written for this project (not copied from any book or deck). Review status: draft. "
                  "Minor arcana now carry per-card meanings ('minors'); the rank x suit composition remains as a fallback.")
    P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", len(minors), "minor cards")


if __name__ == "__main__":
    main()
