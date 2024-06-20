from django.core.cache import cache
from seed.landing.models import SEEDUser
def global_vars(request):

    method_2fa = cache.get("method_2fa")
    return {"method_2fa": method_2fa}