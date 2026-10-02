"""CLI to connect Clio without a browser session.

  make clio-connect                 → link using CLIO_REDIRECT_URI (backend on :8000 receives the code)
  make clio-connect MANUAL=1        → link using Clio's hosted approval page; then:
  make clio-code CODE=<code>        → exchange the code shown on that page
"""
import sys
from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings
from .client import APPROVAL_REDIRECT, authorize_url, connection_status, exchange_code

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "code":
        exchange_code(args[1].strip(), redirect_uri=APPROVAL_REDIRECT)
        print(f"✓ Clio connected as {connection_status()['clio_user'] or '(unknown user)'}")
        sys.exit(0)
    manual = bool(args and args[0] == "manual")
    if connection_status()["connected"]:
        print(f"Already connected to Clio as {connection_status()['clio_user']}")
    state = jwt.encode({"uid": 0, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.jwt_secret,
                       algorithm="HS256")
    redirect = APPROVAL_REDIRECT if manual else settings.clio_redirect_uri
    print(f"Redirect URI used: {redirect}  (must be listed on your Clio developer app)\n")
    print(authorize_url(state, redirect))
    if manual:
        print("\nAfter approving, copy the code Clio shows and run:  make clio-code CODE=<code>")
