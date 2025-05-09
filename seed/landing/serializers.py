from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class SeedTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        # token["name"] = f"{user.first_name} {user.last_name}".strip()

        return token
