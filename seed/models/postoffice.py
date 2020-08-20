# from django.db import models
# from seed.landing.models import SEEDUser as User

# from seed.lib.superperms.orgs.models import Organization
# from post_office.models import EmailTemplate, Email

# class seed_Email(Email): #check capitalization
# """
# Additional fields for Email
# """
#     organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cycles', blank=True, null=True)
#     user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

# class seed_EmailTemplate(EmailTemplate):
#     organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cycles', blank=True, null=True)
#     user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)