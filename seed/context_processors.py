from django.conf import settings
from django.core.cache import cache


def deployment_config():
    return {
        "branding": {
            "logo_url": settings.SEED_BRAND_LOGO_URL,
            "home_hero_image_url": settings.SEED_HOME_HERO_IMAGE_URL,
            "home_heading": settings.SEED_HOME_HEADING,
            "home_text": settings.SEED_HOME_TEXT,
            "login_heading": settings.SEED_LOGIN_HEADING,
            "login_text": settings.SEED_LOGIN_TEXT,
            "home_content_mode": settings.SEED_HOME_CONTENT_MODE,
        },
        "hidden_navigation": settings.SEED_HIDDEN_NAVIGATION,
        "integrations": {"salesforce": settings.SEED_SALESFORCE_ENABLED, "better": settings.SEED_BETTER_ENABLED},
    }


def global_vars(_request):
    method_2fa = cache.get("method_2fa")
    user_email = cache.get("user_email")
    return {"method_2fa": method_2fa, "user_email": user_email, "deployment": deployment_config()}
