from superperms.orgs.models import (
    Organization as SuperOrganization,
    OrganizationUser as SuperOrganizationUser
)


def create_organization(user, org_name='', *args, **kwargs):
    """Helper script to create a user/org relationship from scratch.

    :param user: user inst.
    :param org_name: str, name of Organization we'd like to create.
    :param (optional) kwargs: 'role', int; 'staus', str.

    """
    org = SuperOrganization.objects.create(
        name=org_name
    )
    org_user, user_added = SuperOrganizationUser.objects.get_or_create(
        user=user, organization=org
    )

    return org, org_user, user_added
