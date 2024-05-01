
import datetime
import json
from urllib.parse import urlencode

import pint
from django.core.paginator import EmptyPage, Paginator
from django.db.models.functions import Lower
from seed.models import Column, PropertyState, PropertyView, TaxLotState, TaxLotView
from seed.utils.tax_lot_properties import format_export_data
from seed.views.v3.tax_lot_properties import TaxLotPropertyViewSet


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
        labels = "Disabled"
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
        data["properties"], p_count = _add_states_to_data(
            base_url, PropertyState, "propertyview", page, per_page, labels, cycles, org, html_view
        )

    if taxlots_param:
        data["taxlots"], t_count = _add_states_to_data(base_url, TaxLotState, "taxlotview", page, per_page, labels, cycles, org, html_view)

    pagination = {
        "page": page,
        "total_pages": int(max(p_count, t_count) / per_page) + 1,
        "per_page": per_page,
    }
    if not html_view:
        organization = {"id": org.id, "name": org.name}
    else:
        organization = {"organization_id": org.id, "organization_name": org.name}

    if properties_param:
        pagination["property_count"] = p_count
    if taxlots_param:
        pagination["taxlot_count"] = t_count

    return {
        "pagination": pagination,
        "query_params": {
            "labels": labels,
            "cycle_ids": cycles if cycles else "all",
            "properties": properties_param,
            "taxlots": taxlots_param,
        },
        "organization": organization,
        "data": data,
    }


def _add_states_to_data(base_url, state_class, view_string, page, per_page, labels, cycles, org, html_view=False):
    states = state_class.objects.filter(**{f"{view_string}__cycle__in": cycles, "organization": org}).order_by("-updated")

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
            if isinstance(value, datetime.datetime):
                # convert datetime to readable format
                value = value.strftime("%Y/%m/%d, %H:%M:%S")

            state_data[name] = value

        # add the "automatically" added content to the end of the data
        if html_view:
            state_data["cycle"] = f"{view.cycle.name} ({view.cycle.id})"
        else:
            state_data["cycle"] = {"id": view.cycle.id, "name": view.cycle.name}
        if org.public_feed_labels:
            state_data["labels"] = ", ".join(view.labels.all().values_list("name", flat=True))
        state_data.update(
            {"updated": state.updated.strftime("%Y/%m/%d, %H:%M:%S"), "created": state.created.strftime("%Y/%m/%d, %H:%M:%S")}
        )

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


def dict_to_table(data, title, params):
    if not len(data):
        return f"<h2>{title}: None</h2>"
    cnt = 0
    if title == "Properties":
        cnt = params["property_count"]
    else:
        cnt = params["taxlot_count"]
    html = f"<h2>{title}: {cnt}</h2>\n<table>\n"
    headers = data[0].keys()
    header_row = "<tr>" + "".join(f"<th>{header.replace('_', ' ').title()}</th>" for header in headers) + "</tr>\n"
    html += header_row
    for datum in data:
        row = "<tr>" + "".join(f"<td>{datum[header]}</td>" for header in headers) + "</tr>"
        html += row
    html += "</table>"

    return html


def page_navigation_link(base_url, pagination, query_params, next_page):
    page = pagination["page"]
    total_pages = pagination["total_pages"]

    if next_page:
        action_text = "Next"
        query_params["page"] = page + 1 if page < total_pages else total_pages
        condition = page < total_pages
    else:
        action_text = "Previous"
        query_params["page"] = page - 1 if page > 1 else 1
        condition = page > 1

    if condition:
        return f"<a type='button' href='{base_url}?{urlencode(query_params)}'>{action_text}</a>"
    else:
        return ""


PUBLIC_HTML_DISABLED = """
    <html>
        <div style="font-family: 'PT Sans Narrow', 'Helvetica Neue', helvetica, arial, sans-serif;">
            Public feed is not enabled for organization '{}'. Public feed can be enabled in
            <a href="/app/#/accounts/{}" target="_blank">organization settings</a>.
        </div>
    </html>
"""

PUBLIC_HTML_HEADER = """
    <div class="logo_container">
        <a id="logo-link" class="logo" href="/">
        <div class="logo_text">
            <span class="logo_text_seed">Seed</span>
            <span class="logo_text_platform">Platform™</span>
        </div>
        </a>
    </div>
"""

PUBLIC_HTML_STYLE = """
            body {
                font-family: 'PT Sans', 'Helvetica Neue', helvetica, arial, sans-serif;
                font-weight: normal;
                margin: 0;
            }
            #logo-link {
                text-decoration: none;
            }
            .logo_container {
                display: flex;
                height: 50px;
                border-bottom: 1px solid #dcdcdc;

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

            .page_title {
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                text-overflow: ellipsis;
                padding: 10px 0px;
                border-bottom: 1px solid #dcdcdc;

                h1 {
                    font-size: 18px;
                    font-weight: bold;
                    margin: 0;
                    white-space: nowrap;
                }
            }
            h2 {
                font-size: 18px;
                font-weight: bold;
                margin: 5px 20px 5px 20px;
            }
            .page-num {
                margin: 5px 0px;
            }
            .nav-links {
                margin: 5px; 0px; 5px; 5px;
            }
            .content {
                width: 100vw;
                overflow: scroll;

                .title {
                    margin-left: 20px;
                }
                table, th, td {
                    border: 1px solid #dcdcdc;
                    border-collapse: collapse;
                    padding: 6px 10px 5px;
                    width: 80%;
                }
                table {
                    display: table;
                    border-spacing: 0;
                    margin: 20px;

                    tr:nth-child(odd) {
                        background-color: #eee;
                    }
                }
                tr {
                    display: table-row;
                    background-color: #fff;

                }
                th, td {
                    white-space: nowrap;
                    color: #222;
                    font-size: 13px;
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

def public_geojson(org, cycle, request):
        params = request.query_params
        # default to properties
        view_klass_str = params.get('inventory', 'properties').lower()
        if view_klass_str == 'taxlots':
            view_klass = TaxLotView 
            view_ids = view_klass.objects.filter(taxlot__organization=org, cycle=cycle).values_list('id', flat=True)
        else: 
            view_klass = PropertyView
            view_ids = view_klass.objects.filter(property__organization=org, cycle=cycle).values_list('id', flat=True)
        
        metadata = {
            "organization": {"id": org.id, "name": org.name},
            "cycle": {"id": cycle.id, "name": cycle.name},
            "inventory": view_klass_str,
            "inventory count": len(view_ids)
        }
        
        if not view_ids:
            return {
                "metadata": metadata,
                "data": []
            }

        access_level_instance = org.root 
        data, column_name_mappings = format_export_data(
            view_ids,
            org.id,
            None,
            view_klass_str,
            view_klass,
            access_level_instance,
            None,
            False,
            False,
            'geojson',
        )
        viewset = TaxLotPropertyViewSet()
        # make data json readable
        data = viewset._json_response('', data, column_name_mappings)
        data = json.loads(data.content)

        return {
            "metadata": metadata,
            "data": data
        }