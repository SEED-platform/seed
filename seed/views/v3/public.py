from django.http import HttpResponse, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from seed.models import Cycle, Organization
from seed.utils.public import (
    PUBLIC_HTML_DISABLED,
    PUBLIC_HTML_HEADER,
    PUBLIC_HTML_STYLE,
    dict_to_table,
    page_navigation_link,
    public_feed,
    public_geojson,
)


class PublicOrganizationViewSet(viewsets.ViewSet):
    """
    Public endpoints that do not require a login
    """

    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"], url_path="feed.json")
    def feed_json(self, request, pk):
        """
        Returns all property and taxlot state data for a given organization as a json object. The results are ordered by "state.update".

        Optional and configurable url query_params:
        :query_param labels: comma separated list of case sensitive label names. Results will include inventory that has any of the listed labels. Default is all inventory
        :query_param cycles: comma separated list of cycle ids. Results include inventory from the listed cycles. Default is all cycles
        :query_param properties: boolean to return properties. Default is True
        :query_param taxlots: boolan to return taxlots. Default is True
        :query_param page: integer page number
        :query_param per_page: integer results per page

        Example requests:
        {seed_url}/api/v3/public/organizations/{organization_id}/feed.json?{query_param1}={value1}&{query_param2}={value2}
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.json
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.json?page=2&labels=Compliant&cycles=1,2,3&taxlots=False
        """

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"erorr": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not org.public_feed_enabled:
            return JsonResponse(
                {
                    "detail": f"Public feed is not enabled for organization '{org.name}'. Public endpoints can be enabled in organization settings"
                }
            )

        feed = public_feed(org, request)
        return JsonResponse(feed, json_dumps_params={"indent": 4}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="feed.html")
    def feed_html(self, request, pk):
        """
        Returns all property and taxlot state data for a given organization as an HTML string. The results are ordered by "state.update".

        Optional and configurable url query_params:
        :query_param labels: comma separated list of case sensitive label names. Results will include inventory that has any of the listed labels. Default is all inventory
        :query_param cycles: comma separated list of cycle ids. Results include inventory from the listed cycles. Default is all cycles
        :query_param properties: boolean to return properties. Default is True
        :query_param taxlots: boolan to return taxlots. Default is True
        :query_param page: integer page number
        :query_param per_page: integer results per page

        Example requests:
        {seed_url}/api/v3/public/organizations/{organization_id}/feed.html?{query_param1}={value1}&{query_param2}={value2}
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.html
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.html?page=2&labels=Compliant&cycles=1,2,3&taxlots=False
        """

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"erorr": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not org.public_feed_enabled:
            return HttpResponse(PUBLIC_HTML_DISABLED.format(org.name, org.id))

        query_params = request.GET.copy()
        base_url = f"/api/v3/public/organizations/{pk}/feed.html"
        data = public_feed(org, request, html_view=True)

        page_header = f"""
            <div class="page_title">
                <h1>Public Disclosure Data - {org.name}</h1>
            </div>
        """

        params = {**data.get("pagination"), **data.get("organization"), **data.get("query_params")}
        table_properties = ""
        if data["query_params"].get("properties"):
            table_properties = dict_to_table(data["data"].get("properties", []), "Properties", params)

        table_taxlots = ""
        if data["query_params"].get("taxlots"):
            table_taxlots = dict_to_table(data["data"].get("taxlots", []), "Tax Lots", params)

        page_controls = f"""
            <div class='table-controls'>
                <div class='page-num'>Page {data['pagination']['page']} of {data['pagination']['total_pages']}</div>
                <div class='nav-links'> {page_navigation_link(base_url, data['pagination'], query_params, False)}
                {page_navigation_link(base_url, data['pagination'], query_params, True)}</div>
            </div>
        """
        content = f"""
            <div class='content'>
                {page_header}
                {page_controls}
                {table_properties}
                {table_taxlots}
                {page_controls}
            </div>
        """
        html = f"""
            <html>
                <head>
                <style>
                    {PUBLIC_HTML_STYLE}
                </style>
                </head>
                <body>
                    {PUBLIC_HTML_HEADER}
                    {content}
                </body>
            </html
        """

        return HttpResponse(html)


class PublicCycleViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"], url_path="geo.json")
    def public_geojson(self, request, organization_pk, pk):
        """
        Returns geojson data for selected inventory type within a specific cycle

        Optional and configurable query_params
        :query_param inventory: string, 'properties' or 'taxlots'. Default is 'properties'

        Example Requests:
        {seed_url}/api/v3/public/organizations/{organization_id}/cycles/{cycle_id}/geo.json?{query_param1}={value1}
        dev1.seed-platform.org/api/v3/public/organizations/1/cycles/2/geo.json
        dev1.seed-platform.org/api/v3/public/organizations/1/cycles/2/geo.json?inventory='taxlots'
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
            cycle = Cycle.objects.get(organization_id=organization_pk, pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"erorr": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Cycle.DoesNotExist:
            return JsonResponse({"erorr": "Cycle does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not org.public_feed_enabled:
            return JsonResponse(
                {
                    "detail": f"Public GeoJson is not enabled for organization '{org.name}'. Public endpoints can be enabled in organization settings"
                }
            )

        geojson_data = public_geojson(org, cycle, request)

        return JsonResponse(geojson_data, json_dumps_params={"indent": 4}, status=status.HTTP_200_OK)
