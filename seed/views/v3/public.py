from django.http import HttpResponse, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from seed.models import Organization
from seed.utils.public import PUBLIC_HTML_DISABLED, PUBLIC_HTML_HEADER, PUBLIC_HTML_STYLE, dict_to_table, page_navigation_link, public_feed


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
        {seed_url}/api/v3/public/organizations/feed.json?{query_param1}={value1}&{query_param2}={value2}
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.json
        dev1.seed-platform.org/api/v3/public/organizations/1/feed.json?page=2&labels=Compliant&cycles=1,2,3&taxlots=False
        """

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"erorr": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not org.public_feed_enabled:
            return JsonResponse(
                {"detail": f"Public feed is not enabled for organization '{org.name}'. Public feed can be enabled in organization settings"}
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
        {seed_url}/api/v3/public/organizations/feed.html?{query_param1}={value1}&{query_param2}={value2}
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

        table_properties = ""
        if data["query_params"].get("properties"):
            table_properties = dict_to_table(data["data"].get("properties", []), "Properties")

        table_taxlots = ""
        if data["query_params"].get("taxlots"):
            table_taxlots = dict_to_table(data["data"].get("taxlots", []), "Tax Lots")

        params = [{**data.get("pagination"), **data.get("organization"), **data.get("query_params")}]
        params_table = dict_to_table(params, "")

        page_controls = f"""
            <div class='table-controls'>
                {page_navigation_link(base_url, data['pagination'], query_params, False)}
                {page_navigation_link(base_url, data['pagination'], query_params, True)}
            </div>
        """
        content = f"""
            <div class='content'>
                {params_table}
                {page_controls}
                {table_properties}
                {table_taxlots}
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
