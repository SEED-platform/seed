from seed.models import Project, ProjectBuilding, StatusLabel
from seed.utils.buildings import get_search_query


def get_projects(building, organization):
    """return an JSON friendly list of the building's projects

    :param building: the BuildingSnapshot inst.
    :param organization: the Organization inst.
    :returns: list of projects
    """
    projects = []
    for p in building.project_set.filter(
            super_organization=organization
    ).distinct():
        project_dict = p.__dict__.copy()
        project_dict['is_compliance'] = p.has_compliance
        if project_dict['is_compliance']:
            c = p.get_compliance()
            project_dict['compliance_type'] = c.compliance_type
            project_dict['end_date'] = c.end_date.strftime("%m/%d/%Y")
            project_dict['deadline_date'] = c.deadline_date.strftime(
                "%m/%d/%Y"
            )

        del(project_dict['_state'])
        del(project_dict['modified'])
        del(project_dict['created'])

        pb = ProjectBuilding.objects.get(project=p, building_snapshot=building)
        if pb.approved_date:
            approved_date = pb.approved_date.strftime("%m/%d/%Y")
        else:
            approved_date = None
        project_dict['building'] = {
            'compliant': pb.compliant,
            'approver': pb.approver.email if pb.approver else None,
            'approved_date': approved_date,
        }
        if pb.status_label:
            label = {
                'name': pb.status_label.name,
                'color': pb.status_label.color,
                'id': pb.status_label.pk,
            }
            project_dict['building']['label'] = label
        projects.append(project_dict)

    return projects


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

       :param project_slug: str, a slug to get a Project isnt.
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


def transfer_buildings(source_project_slug, target_project_slug, buildings,
                       select_all, search_params, user, copy_flag=False):
    """copies or moves buildings from one project to another

       :param source_project_slug: str, a slug to get a Project isnt.
       :param target_project_slug: str, a slug to get a Project isnt.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset
       and to update the projects' "last changed" and "last changed by"
       :copy_flag: bool, True - copy buildings, False - move buildings

    """
    target_project = Project.objects.get(slug=target_project_slug)
    source_project = Project.objects.get(slug=source_project_slug)

    # update source and target project info
    target_project.last_modified_by = user
    source_project.last_modified_by = user
    target_project.save()
    source_project.save()

    if copy_flag:
        copy_buildings(source_project, target_project, buildings,
                       select_all, search_params, user)
    else:
        move_buildings(source_project, target_project, buildings,
                       select_all, search_params, user)


def copy_buildings(source_project, target_project, buildings,
                   select_all, search_params, user):
    """copies buildings from source project to target project

       :param source_project_slug: str, a slug to get a Project isnt.
       :param target_project_slug: str, a slug to get a Project isnt.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    delete_matching_buildings(
        target_project, buildings, select_all, search_params, user
    )
    pb_queryset = get_transfer_buildings(
        source_project, target_project, buildings, select_all, search_params,
        user
    )
    pbs = []
    for b in pb_queryset:
            # setting pk to None will create a copy the django instance
            b.pk = None
            b.project = target_project
            pbs.append(b)

    ProjectBuilding.objects.bulk_create(pbs)


def move_buildings(source_project, target_project, buildings,
                   select_all, search_params, user):
    """moves buildings from source project to target project

       :param source_project_slug: str, a slug to get a Project isnt.
       :param target_project_slug: str, a slug to get a Project isnt.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    delete_matching_buildings(
        target_project, buildings, select_all, search_params, user
    )
    pb_queryset = get_transfer_buildings(
        source_project, target_project, buildings, select_all, search_params,
        user
    )
    # move buildings from source to target
    pb_queryset.update(project=target_project)


def delete_matching_buildings(project, buildings,
                              select_all, search_params, user):
    """deletes buildings in a project that match search search params

       :param project_slug: str, a slug to get a Project isnt.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

    """
    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project=project
        ).exclude(building_snapshot__pk__in=buildings).delete()
    else:
        ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project=project
        ).delete()


def get_transfer_buildings(source_project, target_project, buildings,
                           select_all, search_params, user):
    """generates move or copy buildings queryset

       :param source_project_slug: str, a slug to get a Project isnt.
       :param target_project_slug: str, a slug to get a Project isnt.
       :param buildings: list, list of source_facility_id as str to get
       BuildingSnapshot inst.
       :param select_all: bool, if the select all checkbox was
       checked. i.e. should we transfer all buildings in a project or just the
       buildings in the list
       :search_params: dict, params needed to generate a queryset of buildings,
       with keys (q, other_params, project_slug)
       :user: User inst., django user instance needed for select all queryset

       :rtype Queryset: a django queryset of buildings to move or copy

    """
    if select_all:
        # get all the buildings for a project minus unselected ones
        qs = get_search_query(user, search_params)
        pb_queryset = ProjectBuilding.objects.filter(
            building_snapshot__in=qs,
            project=source_project
        ).exclude(building_snapshot__pk__in=buildings)
    else:
        pb_queryset = ProjectBuilding.objects.filter(
            building_snapshot__pk__in=buildings,
            project=source_project
        )
    return pb_queryset
