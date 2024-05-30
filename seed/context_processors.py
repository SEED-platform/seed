from seed.landing.models import SEEDUser
def global_vars(request):
    require_2fa = False
    try:
        user = request._cached_user or SEEDUser.objects.filter(username=request.POST.get("auth-username")).first()
        if user:
            require_2fa = any(user.orgs.values_list('require_2fa', flat=True))
    except: 
        pass
    return {'require_2fa': require_2fa}