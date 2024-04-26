import pint
from django.core.paginator import EmptyPage, Paginator
from django.db.models.functions import Lower
from urllib.parse import urlencode

from seed.models import Column, PropertyState, TaxLotState


def public_feed(org, request, html_view=False):
    """
    Format all property and taxlot state data to be displayed on a public feed
    """
    base_url = request.build_absolute_uri("/")
    params = request.query_params
    page = _get_int(params.get("page"), 1)
    per_page = _get_int(params.get("per_page"), 100)
    properties_param = params.get("properties", "true").lower() == "true"
    taxlots_param = params.get("taxlots", "true").lower() == "true"
    if not org.public_feed_labels:
        labels = 'Disabled'
    else:
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
        data["properties"], p_count = _add_states_to_data(base_url, PropertyState, "propertyview", page, per_page, labels, cycles, org, html_view)

    if taxlots_param:
        data["taxlots"], t_count = _add_states_to_data(base_url, TaxLotState, "taxlotview", page, per_page, labels, cycles, org, html_view)

    pagination = {
        "page": page,
        "total_pages": int(max(p_count, t_count) / per_page) + 1,
        "per_page": per_page,
    }
    if not html_view:
        organization =  {"id": org.id, "name": org.name}
    else: 
        organization = {"organization_id": org.id, "organization_name": org.name}


    if properties_param:
        pagination["property_count"] = p_count
    if taxlots_param:
        pagination["taxlot_count"] = t_count


    return {
        "pagination": pagination,
        "query_params": {"labels": labels, "cycle_ids": cycles if cycles else "all", "properties": properties_param, "taxlots": taxlots_param},
        "organization": organization,
        "data": data,
    }


def _add_states_to_data(base_url, state_class, view_string, page, per_page, labels, cycles, org, html_view=False):
    states = state_class.objects.filter(**{f"{view_string}__cycle__in": cycles}).order_by("-updated")

    if labels is not None and org.public_feed_labels:
        states = states.filter(**{f"{view_string}__labels__name__in": labels})

    paginator = Paginator(states, per_page)
    try:
        states_paginated = paginator.page(page)
    except EmptyPage:
        states_paginated = paginator.page(paginator.num_pages)

    public_columns = (
        Column.objects.filter(organization_id=org.id, shared_field_type=1, table_name=state_class._meta.object_name)
        .annotate(column_name_lower=Lower("column_name"))
        .order_by("column_name_lower")
        .values_list("column_name", "is_extra_data")
    )

    data = []
    for state in states_paginated:
        view = getattr(state, f"{view_string}_set").first()

        state_data = {"id": view.id} 
        if html_view:
            state_data["cycle_id"] = view.cycle.id
            state_data["cycle_name"] = view.cycle.name 
        else:
            state_data["cycle"] = {"id": view.cycle.id, "name": view.cycle.name},
        if org.public_feed_labels:
            state_data["labels"] = ", ".join(view.labels.all().values_list("name", flat=True))
        state_data.update({
            "updated": state.updated,
            "created": state.created,
        })

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

        json_link = f'{base_url}api/v3/{"properties" if type(state) == PropertyState else "taxlots"}/{view.id}/?organization_id={view.cycle.organization.id}'
        html_link = f'{base_url}app/#/{"properties" if type(state) == PropertyState else "taxlots"}/{view.id}'
        if not html_view:
            state_data["json_link"] = json_link
            state_data["html_link"] = html_link
        else:
            state_data["links"] = f"<p><a href={json_link} target='_blank'>JSON</a>, <a href={html_link} target='_blank'>HTML</a></p>"

        data.append(state_data)

    return data, len(states)


def _get_int(value, default):
    try:
        result = int(float(value))
        return result if result > 0 else default
    except (ValueError, TypeError):
        return default
    
def dict_to_table(data, title):
    if not len(data):
        return f"<div class='title'>{title}: None</div>"
    
    html = f"<div class='title'>{title}</div>\n<table>\n"
    headers = data[0].keys()
    header_row = '<tr>' + ''.join(f'<th>{header}</th>' for header in headers) + '</tr>\n'
    html += header_row
    for datum in data:
        row = '<tr>' + ''.join(f'<td>{datum[header]}</td>' for header in headers) + '<tr/>\n'
        html += row
    html += '</table>'

    return html

def page_navigation_link(base_url, pagination, query_params, next_page):
    page = pagination['page']
    total_pages = pagination['total_pages']

    if next_page:
        action_text = "Next"
        query_params['page'] = page + 1 if page < total_pages else total_pages
        condition = page < total_pages
    else:
        action_text = "Previous"
        query_params['page'] = page -1 if page > 1 else 1
        condition = page > 1

    if condition:
        return f"<a type='button' href='{base_url}?{urlencode(query_params)}'>{action_text}</a>"
    else:
        return ""


PUBLIC_HTML_DISABLED = """                
    <html>
        <div style="'PT Sans Narrow', 'Helvetica Neue', helvetica, arial, sans-serif;"> 
            Public feed is not enabled for organization '{org.name}'. Public feed can be enabled in
            <a href="/app/#/accounts/{org.id}" target="_blank">organization settings</a>.
        </div>
    </html>
"""

PUBLIC_HTML_HEADER = """
    <div class="logo_container">
        <a class="logo" href="/">
        <div class="logo_text">
            <span class="logo_text_seed">Seed</span>
            <span class="logo_text_platform">Platform™</span>
        </div>
        </a>
    </div>
"""

PUBLIC_HTML_STYLE = """
            body {
                font-family: 'PT Sans Narrow', 'Helvetica Neue', helvetica, arial, sans-serif;
                font-weight: normal;
                margin: 0;
            }
            .logo_container {
                display: flex;
                height: 50px;
                background: #dcdcdc;

                .logo {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    color: black;

                    .logo_text {
                        padding: 0 20px;
                        font-size: 24px;
                        font-family: 'PT Sans Narrow', 'Helvetica Neue', helvetica, arial, sans-serif;
                        font-weight: normal;
                        text-transform: uppercase;

                        .logo_text_seed {
                        font-family: 'PT Sans', 'Helvetica Neue', helvetica, arial, sans-serif;
                        font-weight: bold;
                        }
                    }
                }
            }
            .content {
                width: 100vw;
                overflow: scroll;

                .title {
                    margin-left: 20px;
                }
                table, th, td {
                    border: 1px solid black;
                    border-collapse: collapse;
                    padding: 0 8px;
                    widthL 100%;
                }
                table {
                    margin: 20px;
                }
                th, td {
                    white-space: nowrap;
                }
                .table-controls {
                    margin: 20px;
                    display: flex;
                    a {
                        border: 1px solid gray;
                        border-radius: 3px;
                        padding: 5px;
                        margin-right: 5px;
                        text-decoration: none;
                        color: gray;
                    }
                }
                
            }
        """