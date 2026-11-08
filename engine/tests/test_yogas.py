

def test_second_batch_of_yogas_is_consistent():
    from jyotish import compute_chart
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    y = {x["id"]: x for x in c["yogas"]}
    for k in ("sunapha", "anapha", "durudhara", "kemadruma", "vesi", "vasi", "ubhayachari", "adhi", "amala", "harsha", "sarala", "vimala",
              "parivartana", "dhana", "raja_kendra_trikona", "lakshmi", "saraswati"):
        assert k in y and y[k]["why_hi"] and y[k]["why"]
    # Moon yogas are mutually exclusive by construction
    assert sum(y[k]["present"] for k in ("sunapha", "anapha", "durudhara", "kemadruma")) <= 1
    assert sum(y[k]["present"] for k in ("vesi", "vasi", "ubhayachari")) <= 1
    # this chart: Mars 2nd from the Moon -> Sunapha; Jupiter 2nd and Mercury 12th from the Sun -> Ubhayachari; 9th lord Saturn own in 9th + Venus exalted -> Lakshmi
    assert y["sunapha"]["present"] and y["ubhayachari"]["present"] and y["lakshmi"]["present"] and not y["kemadruma"]["present"]
