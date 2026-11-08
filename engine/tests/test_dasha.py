

def test_running_chain_reaches_pratyantar_and_lists_siblings():
    from jyotish import compute_chart
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    levels = [r["level"] for r in c["dasha_running"]]
    assert levels == [1, 2, 3]
    pr = c["pratyantars_now"]
    assert len(pr) == 9 and sum(1 for p in pr if p["running"]) == 1
    ad = next(r for r in c["dasha_running"] if r["level"] == 2)
    assert pr[0]["start"] == ad["start"] and pr[-1]["end"] == ad["end"]        # pratyantars tile the antardasha exactly
    assert pr[0]["lord"] == ad["lord"]                                           # first pratyantar is the antardasha lord's own
