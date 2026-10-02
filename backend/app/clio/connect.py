"""CLI: print a Clio OAuth link (no browser login needed). The running backend's /auth/clio/callback stores the token.
    make clio-connect
"""
from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings
from .client import authorize_url, connection_status

if __name__ == "__main__":
    if connection_status()["connected"]:
        print(f"Already connected to Clio as {connection_status()['clio_user']}")
    state = jwt.encode({"uid": 0, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.jwt_secret,
                       algorithm="HS256")
    print("Open this link, approve access (backend must be running on :8000):\n")
    print(authorize_url(state))
