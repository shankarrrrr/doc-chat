from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from django.http import HttpRequest, JsonResponse

from .supabase_auth import get_supabase_user


F = TypeVar('F', bound=Callable[..., Any])


def supabase_required(view_func: F) -> F:
    @wraps(view_func)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'detail': 'Missing bearer token'}, status=401)

        access_token = auth_header.split(' ', 1)[1].strip()
        if not access_token:
            return JsonResponse({'detail': 'Missing bearer token'}, status=401)

        try:
            user = get_supabase_user(access_token)
        except RuntimeError as e:
            return JsonResponse({'detail': str(e)}, status=500)

        if user is None:
            return JsonResponse({'detail': 'Invalid token'}, status=401)

        request.supabase_user = user  # type: ignore[attr-defined]
        return view_func(request, *args, **kwargs)

    return wrapped  # type: ignore[return-value]
