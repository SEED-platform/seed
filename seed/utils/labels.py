from seed.models import ProjectBuilding, StatusLabel
from seed.utils.buildings import get_search_query


# TODO: piper: this needs to be u


def get_labels(user):
    """return an JSON friendly list of labels for a user in an
       owner__organization__users
       lables = [
        {
            'name': name,
            'color': color,
            'id': label_id
        },
        ...
       ]

    """
    status_labels = StatusLabel.objects.filter(
        super_organization__in=user.orgs.all()
    )
    labels = []
    for label in status_labels:
        labels.append({
            'name': label.name,
            'color': label.color,
            'id': label.pk,
        })
    return labels


def update_buildings_with_labels(buildings, project_id):
    """update the buildings in a buildings list with their StatusLabel"""
    for b in buildings:
        pb = ProjectBuilding.objects.get(
            building_snapshot__pk=b['pk'],
            project__pk=project_id
        )
        if pb.status_label:
            b['project_building_snapshots__status_label__name'] = {
                'name': pb.status_label.name,
                'color': pb.status_label.color,
                'id': pb.status_label.pk,
            }
    return buildings


def apply_label(project_slug, buildings, select_all, label, search_params,
                user):
    """adds or updates a label for a ProjectBuilding related to a
       project and building in the buildings list of source_facility_ids

       :param project_slug: str, a slug to get a Project inst.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we get all buildings or just the ones in the list
       :param label: dict, dict of a info to get a StatusLabel inst., if label
       if an empty dict, apply_label will remove the label
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)

    """
    if 'id' in label:
        label = StatusLabel.objects.get(pk=label['id'])
    else:
        label = None

    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        pb_qs = ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project__slug=project_slug
        ).exclude(
            building_snapshot__pk__in=buildings
        )
    else:
        # just add selected buildings
        pb_qs = ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project__slug=project_slug,
        )
    pb_qs.update(
        status_label=label
    )
