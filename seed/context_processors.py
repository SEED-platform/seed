from django.core.cache import cache


def global_vars(_request):
    method_2fa = cache.get("method_2fa")
    user_email = cache.get("user_email")
    return {"method_2fa": method_2fa, "user_email": user_email}
