# Generated manually to remove organization users whose access level instance belongs to a
# different organization.
#
# Access level filters compare nested-set bounds, which overlap between organizations, so such
# a membership can reach another organization's data. They could only be created through the
# v4 organization user update, which let users change their membership's organization. Since
# no access level instance of the membership's own organization can be inferred, they are
# deleted and reported so that administrators can review them.

from django.db import migrations
from django.db.models import F


def delete_cross_organization_memberships(apps, schema_editor):
    OrganizationUser = apps.get_model("orgs", "OrganizationUser")

    org_users = OrganizationUser.objects.exclude(access_level_instance__organization_id=F("organization_id")).select_related(
        "user", "access_level_instance"
    )
    for org_user in org_users:
        print(
            f"Deleting organization user {org_user.pk}: user {org_user.user_id} ({org_user.user.email}) in organization "
            f"{org_user.organization_id} with role level {org_user.role_level} had access level instance "
            f"{org_user.access_level_instance_id} of organization {org_user.access_level_instance.organization_id}"
        )
        org_user.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0046_repair_organizationuser_constraints"),
        # Goal.partner_note_approval_user references OrganizationUser and is set to null on delete
        ("seed", "0250_remove_goal_current_cycle_goal_partner_note_and_more"),
    ]

    operations = [
        migrations.RunPython(delete_cross_organization_memberships, migrations.RunPython.noop),
    ]
