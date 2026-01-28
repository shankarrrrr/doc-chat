from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


@dataclass(frozen=True)
class SupabaseUser:
    id: str
    email: str | None
    user_metadata: dict[str, Any]


def get_supabase_user(access_token: str) -> SupabaseUser | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError('Missing SUPABASE_URL or SUPABASE_ANON_KEY in backend/.env')

    url = settings.SUPABASE_URL.rstrip('/') + '/auth/v1/user'
    req = Request(
        url,
        method='GET',
        headers={
            'Authorization': f'Bearer {access_token}',
            'apikey': settings.SUPABASE_ANON_KEY,
            'Accept': 'application/json',
        },
    )

    try:
        with urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    user_id = payload.get('id')
    if not isinstance(user_id, str) or not user_id:
        return None

    email = payload.get('email')
    if not isinstance(email, str):
        email = None

    user_metadata = payload.get('user_metadata')
    if not isinstance(user_metadata, dict):
        user_metadata = {}

    return SupabaseUser(id=user_id, email=email, user_metadata=user_metadata)
