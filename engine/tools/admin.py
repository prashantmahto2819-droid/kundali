"""Manage organisations and API keys (run on the server).

    python tools/admin.py create-org "Acme Astro" [--plan free|pro|unlimited]
    python tools/admin.py create-key ORG_ID [--label NAME]     # prints the key ONCE
    python tools/admin.py list-orgs
    python tools/admin.py usage ORG_ID [--days 7]
    python tools/admin.py revoke KEY_ID_OR_PREFIX
    python tools/admin.py set-plan ORG_ID PLAN

The database path comes from KUNDALI_DB (default: kundali_access.db in the repo root).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jyotish import access  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-org"); p.add_argument("name"); p.add_argument("--plan", default="free")
    p = sub.add_parser("create-key"); p.add_argument("org_id"); p.add_argument("--label", default="")
    sub.add_parser("list-orgs")
    p = sub.add_parser("usage"); p.add_argument("org_id"); p.add_argument("--days", type=int, default=7)
    p = sub.add_parser("revoke"); p.add_argument("key")
    p = sub.add_parser("set-plan"); p.add_argument("org_id"); p.add_argument("plan")
    a = ap.parse_args()
    st = access.default_store()
    try:
        if a.cmd == "create-org":
            o = st.create_org(a.name, a.plan)
            print(f"org {o['id']}  name={o['name']}  plan={o['plan']}")
        elif a.cmd == "create-key":
            key, rec = st.create_key(a.org_id, a.label)
            print(f"key id: {rec['id']}\nAPI key (shown once, store it safely):\n{key}")
        elif a.cmd == "list-orgs":
            for o in st.list_orgs():
                print(f"{o['id']}  {o['plan']:9}  {o['name']}")
        elif a.cmd == "usage":
            for r in st.usage(a.org_id, a.days):
                print(f"{r['day']}  {r['endpoint']:20} {r['count']}")
        elif a.cmd == "revoke":
            print("revoked" if st.revoke_key(a.key) else "no such key")
        elif a.cmd == "set-plan":
            st.set_plan(a.org_id, a.plan)
            print("ok")
    except ValueError as exc:
        print("error:", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
