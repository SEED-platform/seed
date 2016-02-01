# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from seed.models import Project, ProjectBuilding
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
        projects.append(project_dict)

    return projects


def transfer_buildings(source_project_slug, target_project_slug, buildings,
                       select_all, search_params, user, copy_flag=False):
    """copies or moves buildings from one project to another

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
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

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
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

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
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

       :param project_slug: str, a slug to get a Project inst.
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

       :param source_project_slug: str, a slug to get a Project inst.
       :param target_project_slug: str, a slug to get a Project inst.
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
