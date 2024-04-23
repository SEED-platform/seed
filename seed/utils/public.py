import pint
from django.core.paginator import EmptyPage, Paginator
from django.db.models.functions import Lower

from seed.models import Column, PropertyState, TaxLotState


def public_feed(org, request):
    """
    Format all property and taxlot state data to be displayed on a public feed
    """
    base_url = request.build_absolute_uri("/")
    params = request.query_params
    page = _get_int(params.get("page"), 1)
    per_page = _get_int(params.get("per_page"), 100)
    properties_param = params.get("properties", "true").lower() == "true"
    taxlots_param = params.get("taxlots", "true").lower() == "true"
    labels = params.get("labels", None)
    if labels is not None:
        labels = labels.split(",")
    cycles = params.get("cycles", None)
    if cycles is not None:
        cycles = cycles.split(",")
    else:
        cycles = list(org.cycles.values_list("id", flat=True))

    data = {}
    p_count = 0
    t_count = 0

    if properties_param:
        data["properties"], p_count = _add_states_to_data(base_url, PropertyState, "propertyview", page, per_page, labels, cycles)

    if taxlots_param:
        data["taxlots"], t_count = _add_states_to_data(base_url, TaxLotState, "taxlotview", page, per_page, labels, cycles)

    pagination = {
        "page": page,
        "total_pages": int(max(p_count, t_count) / per_page) + 1,
        "per_page": per_page,
    }

    if properties_param:
        pagination["properties"] = p_count
    if taxlots_param:
        pagination["taxlots"] = t_count

    return {
        "pagination": pagination,
        "query_params": {"labels": labels, "cycles": cycles if cycles else "all", "properties": properties_param, "taxlots": taxlots_param},
        "organization": {"id": org.id, "name": org.name},
        "data": data,
    }


def _add_states_to_data(base_url, state_class, view_string, page, per_page, labels, cycles):
    states = state_class.objects.filter(**{f"{view_string}__cycle__in": cycles}).order_by("-updated")

    if labels is not None:
        states = states.filter(**{f"{view_string}__labels__name__in": labels})

    paginator = Paginator(states, per_page)
    try:
        states_paginated = paginator.page(page)
    except EmptyPage:
        states_paginated = paginator.page(paginator.num_pages)

    public_columns = (
        Column.objects.filter(shared_field_type=1, table_name=state_class._meta.object_name)
        .annotate(column_name_lower=Lower("column_name"))
        .order_by("column_name_lower")
        .values_list("column_name", "is_extra_data")
    )

    data = []
    for state in states_paginated:
        view = getattr(state, f"{view_string}_set").first()

        state_data = {
            "id": view.id,
            "cycle": {"id": view.cycle.id, "name": view.cycle.name},
            "updated": state.updated,
            "created": state.created,
            "labels": ", ".join(view.labels.all().values_list("name", flat=True)),
        }

        for name, extra_data in public_columns:
            if name in ["updated", "created"]:
                continue
            if not extra_data:
                value = getattr(state, name, None)
            else:
                value = state.extra_data.get(name, None)
            if isinstance(value, pint.Quantity):
                # convert pint to string with units (json cannot display exponents)
                value = f"{value.m} {value.u}"

            state_data[name] = value

        state_data["json_link"] = (
            f'{base_url}api/v3/{"properties" if type(state) == PropertyState else "taxlots"}/{view.id}/?organization_id={view.cycle.organization.id}'
        )
        state_data["html_link"] = f'{base_url}app/#/{"properties" if type(state) == PropertyState else "taxlots"}/{view.id}'

        data.append(state_data)

    return data, len(states)


def _get_int(value, default):
    try:
        result = int(float(value))
        return result if result > 0 else default
    except (ValueError, TypeError):
        return default
