import os

# The suite fires hundreds of guard() calls from one "IP"; keep the public rate limits out of the way (test_ratelimit re-enables them).
os.environ.setdefault("KUNDALI_RATE_LIMIT", "0")
