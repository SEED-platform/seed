from django.http import JsonResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from seed.models import Organization
from seed.utils.public import public_feed


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

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"erorr": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        
        style= """
            body {
                font-family: 'PT Sans Narrow', 'Helvetica Neue', helvetica, arial, sans-serif;
                font-weight: normal;
            }
            .logo_container {
                display: flex;
                height: 50px;

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
                
            }
        """
        header = """
            <div class="logo_container">
                <a class="logo" href="/">
                <div class="logo_text">
                    <span class="logo_text_seed">Seed</span>
                    <span class="logo_text_platform">Platform™</span>
                </div>
                </a>
            </div>
        """
        def dict_to_table(data):
            html = "<table>\n"

            headers = data[0].keys()
            header_row = '<tr>' + ''.join(f'<th>{header}</th>' for header in headers) + '</tr>\n'
            html += header_row

            for datum in data:

                row = '<tr>' + ''.join(f'<td>{datum[header]}</td>' for header in headers) + '<tr/>\n'
                html += row

            html += '</table>'

            return html
        
        data = public_feed(org, request, flat_cycle=True)
        table = dict_to_table(data['data']['properties'])

        content = f"""<div class='content'>{table}</div>"""
        html = f"""
            <html>
                <head>
                <style>
                    {style}
                </style>
                </head>
                <body>
                    {header}
                    {content}
                </body>
            </html"""
        return HttpResponse(html)