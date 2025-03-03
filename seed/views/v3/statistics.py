"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re
from copy import deepcopy

import django.core.exceptions
import numpy as np
import pandas as pd
from django.db import IntegrityError, models
from django.db.models.fields.json import KeyTransform
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.models.properties import PropertyView
from seed.models.statistics_setups import StatisticsSetup
from seed.serializers.statistics_setups import StatisticsSetupSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param


def _validate_data(data, org_id):
    error = False
    msgs = []

    #  Validate Columns
    column_names = ["gfa_column", "electricity_column", "natural_gas_column"]
    for item in column_names:
        c_id = data.get(item)
        if c_id:
            c_col = Column.objects.get(pk=c_id)

            if c_col.organization_id != org_id:
                # error, this column does not belong to this org
                error = True
                msgs.append("The selected column for " + item + " does not belong to this organization")

    return error, msgs


def _remove_nan(the_obj):
    """Convert all NaN values in a nested dictionary to None"""
    if isinstance(the_obj, dict):
        for key, value in the_obj.items():
            if isinstance(value, dict):
                _remove_nan(value)
            elif pd.isna(value):
                the_obj[key] = None
    else:
        for item in the_obj:
            if isinstance(item, dict):
                _remove_nan(item)
            elif pd.isna(item):
                the_obj[item] = None
    return the_obj


def _convert_to_numeric(df, exclude_cols=[]):
    """
    Convert all columns in a DataFrame to numeric types.
    For columns with text patterns like '2042.0 foot ** 2',
    extract the numeric value before conversion.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with mixed type columns

    Returns:
    --------
    pandas.DataFrame
        DataFrame with all columns converted to numeric types
    """
    # Create a copy to avoid modifying the original
    df_numeric = df.copy()

    for col in df_numeric.columns:
        # Skip columns in exclude_cols
        if col in exclude_cols:
            continue
        # Check if column is already numeric
        if pd.api.types.is_numeric_dtype(df_numeric[col]):
            continue

        # If it's an object type, try to extract numeric values
        if df_numeric[col].dtype == "object":
            # Function to extract numeric part from strings
            def extract_numeric(val):
                if pd.isna(val):
                    return np.nan
                if isinstance(val, (int, float)):
                    return val

                # Convert to string if not already
                val_str = str(val)

                # Extract the first number (including decimals)
                # This pattern matches numbers like 123, 123.45, .45
                match = re.search(r"([-+]?\d*\.?\d+)", val_str)
                if match:
                    return match.group(1)
                return val

            # Apply extraction and then convert to numeric
            df_numeric[col] = df_numeric[col].apply(extract_numeric)

        # Convert to numeric, with errors='coerce' to convert non-numerics to NaN
        df_numeric[col] = pd.to_numeric(df_numeric[col], errors="coerce")

    return df_numeric


class StastisticsSetupViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = StatisticsSetupSerializer
    model = StatisticsSetup

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def list(self, request):
        organization_id = self.get_organization(request)
        stats = StatisticsSetup.objects.filter(organization=organization_id)

        s_data = StatisticsSetupSerializer(stats, many=True).data

        return JsonResponse({"status": "success", "statistics": s_data}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def retrieve(self, request, pk=0):
        organization = self.get_organization(request)
        if pk == 0:
            try:
                return JsonResponse(
                    {
                        "status": "success",
                        "statistic": StatisticsSetupSerializer(StatisticsSetup.objects.filter(organization=organization).first()).data,
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception:
                return JsonResponse(
                    {"status": "error", "message": "No statistics setup exist with this identifier"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                data = StatisticsSetupSerializer(StatisticsSetup.objects.get(id=pk, organization=organization)).data
                return JsonResponse({"status": "success", "stastic": data}, status=status.HTTP_200_OK)
            except StatisticsSetup.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": f"Statistics Setup with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
                )

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            StatisticsSetup.objects.get(id=pk, organization=organization_id).delete()
        except StatisticsSetup.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"Statistics with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({"status": "success", "message": f"Successfully deleted Statistics ID {pk}"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "gfa_column": "integer",
                "gfa_units": "string",
                "electricity_column": "integer",
                "electricity_units": "string",
                "natural_gas_column": "integer",
                "natural_gas_units": "string",
                "electricity_eui_column": "integer",
                "electricity_eui_units": "string",
                "natural_gas_eui_column": "integer",
                "natural_gas_eui_units": "string",
            },
        ),
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def create(self, request):
        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "bad organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        data = deepcopy(request.data)
        data.update({"organization_id": org_id})

        error, msgs = _validate_data(data, org_id)
        if error is True:
            return JsonResponse({"status": "error", "message": ",".join(msgs)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StatisticsSetupSerializer(data=data)

        if not serializer.is_valid():
            error_response = {"status": "error", "message": "Data Validation Error", "errors": serializer.errors}
            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()

            return JsonResponse({"status": "success", "statistic": serializer.data}, status=status.HTTP_200_OK)
        except IntegrityError:
            return JsonResponse(
                {"status": "error", "message": "Only one statistics setup can be created per organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            return JsonResponse({"status": "error", "message": "Bad Request", "errors": message_dict}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "gfa_column": "integer",
                "gfa_units": "string",
                "electricity_column": "integer",
                "electricity_units": "string",
                "natural_gas_column": "integer",
                "natural_gas_units": "string",
                "electricity_eui_column": "integer",
                "electricity_eui_units": "string",
                "natural_gas_eui_column": "integer",
                "natural_gas_eui_units": "string",
            },
        ),
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def update(self, request, pk):
        org_id = self.get_organization(request)

        statistic = None
        try:
            statistic = StatisticsSetup.objects.get(id=pk, organization=org_id)
        except StatisticsSetup.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"Statistics with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        error, msgs = _validate_data(data, org_id)
        if error is True:
            return JsonResponse({"status": "error", "message": ",".join(msgs)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StatisticsSetupSerializer(statistic, data=data, partial=True)

        if not serializer.is_valid():
            return JsonResponse(
                {"status": "error", "message": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "statistic": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            # rename key __all__ to general to make it more user-friendly
            if "__all__" in message_dict:
                message_dict["general"] = message_dict.pop("__all__")

            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": message_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["POST"])
    def calculate(self, request, pk):
        org_id = self.get_organization(request)
        ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        # get statistic setup for this org
        try:
            statistic = StatisticsSetup.objects.get(id=pk, organization=org_id)
        except StatisticsSetup.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"Statistics with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        # get all cycles in this org
        cycles = Cycle.objects.filter(organization=org_id)

        # column ids we are interested in, only those non-null

        cols = {}
        extra_data_cols = {}
        if statistic.gfa_column:
            if statistic.gfa_column.is_extra_data:
                extra_data_cols["gfa"] = statistic.gfa_column.column_name
            else:
                cols["gfa"] = "state__" + statistic.gfa_column.column_name
        else:
            # if we don't have GFA column, we can't calculate anything
            return JsonResponse(
                {
                    "status": "error",
                    "message": "GFA column is required to calculate statistics",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # prefer EUI column over usage column
        if statistic.electricity_eui_column:
            if statistic.electricity_eui_column.is_extra_data:
                extra_data_cols["elec_eui"] = statistic.electricity_eui_column.column_name
            else:
                cols["elec_eui"] = "state__" + statistic.electricity_eui_column.column_name
        elif statistic.electricity_column:
            if statistic.electricity_column.is_extra_data:
                extra_data_cols["electricity"] = statistic.electricity_column.column_name
            else:
                cols["electricity"] = "state__" + statistic.electricity_column.column_name
        if statistic.natural_gas_eui_column:
            if statistic.natural_gas_eui_column.is_extra_data:
                extra_data_cols["gas_eui"] = statistic.natural_gas_eui_column.column_name
            else:
                cols["gas_eui"] = "state__" + statistic.natural_gas_eui_column.column_name
        elif statistic.natural_gas_column:
            if statistic.natural_gas_column.is_extra_data:
                extra_data_cols["natural_gas"] = statistic.natural_gas_column.column_name
            else:
                cols["natural_gas"] = "state__" + statistic.natural_gas_column.column_name

        # make sure we have at least electricity or gas here to calculate?
        if len(cols.keys()) + len(extra_data_cols.keys()) < 2:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "At least one of electricity or natural gas column is required to calculate statistics",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # reverse the cols dictionary to have the keys be the values
        # this is to make it easier to map the results back to the correct columns in df
        cols_reverse = {v: k for k, v in cols.items()}

        annotations: dict[str, models.Func] = {}
        for key, val in extra_data_cols.items():
            annotations[key] = KeyTransform(val, "state__extra_data")

        results = {}
        df_full = pd.DataFrame()
        # get all properties that fall in all cycles for this org
        for cycle in cycles:
            # get Property-Views for this Cycle
            property_views = (
                PropertyView.objects.select_related("state")
                .filter(
                    property__organization_id=org_id,
                    cycle_id=cycle.id,
                    property__access_level_instance__lft__gte=ali.lft,
                    property__access_level_instance__rgt__lte=ali.rgt,
                )
                .annotate(**annotations)
                .values("property_id", "state_id", *(list(cols.values())), *(list(extra_data_cols.keys())))
            )

            # dataframe column names will be:
            # property_id, state_id, electricity, natural_gas, cycle_id, gfa,
            # elec_eui, gas_eui

            df_temp = pd.DataFrame.from_records(list(property_views))
            df_temp["cycle"] = cycle.name  # or use ID and get name in frontend?
            df_full = pd.concat([df_full, df_temp])

        # remap the column names to the original column names
        df_full = df_full.rename(columns=cols_reverse)
        df_full = _convert_to_numeric(df_full, ["cycle"])

        # calculate the statistics
        # check if we have EUIs or Usage columns
        # electricity
        if "electricity" in df_full.columns:
            # we have usage, compute EUI
            df_full["elec_eui"] = (df_full["electricity"] / df_full["gfa"]).replace([np.inf, -np.inf], np.nan)
        # gas
        if "natural_gas" in df_full.columns:
            df_full["gas_eui"] = (df_full["natural_gas"] / df_full["gfa"]).replace([np.inf, -np.inf], np.nan)

        # reverse calculate electricity and/or natural gas from EUIs
        # electricity
        if "elec_eui" in df_full.columns:
            df_full["electricity"] = df_full["elec_eui"] * df_full["gfa"]
        # gas
        if "gas_eui" in df_full.columns:
            df_full["natural_gas"] = df_full["gas_eui"] * df_full["gfa"]

        # high-level counts:
        yearly_gfa = (
            df_full.dropna(subset=["gfa"])
            .groupby("cycle")
            .agg(num_records=("property_id", "count"), cycle=("cycle", "first"), GFA=("gfa", "sum"))
        )
        yearly_elec = (
            df_full.dropna(subset=["gfa", "elec_eui"])
            .groupby("cycle")
            .agg(num_records=("property_id", "count"), cycle=("cycle", "first"), GFA=("gfa", "sum"), Electricity_Use=("electricity", "sum"))
        )
        yearly_elec.style.format("{:,.0f}")
        # print(yearly_elec) # format numbers with commas

        yearly_gas = (
            df_full.dropna(subset=["gfa", "gas_eui"])
            .groupby("cycle")
            .agg(num_records=("property_id", "count"), cycle=("cycle", "first"), GFA=("gfa", "sum"), Natural_Gas_Use=("natural_gas", "sum"))
        )
        yearly_gas.style.format("{:,.0f}")
        # print(yearly_gas) # format numbers with commas

        # elec quartiles for each cycle (include cycle key)
        elec_eui_quantiles = df_full.groupby("cycle")["elec_eui"].quantile([0.05, 0.25, 0.50, 0.75, 0.95]).unstack()  # noqa: PD010

        # print(f"Elec Quantiles")
        # print(elec_eui_quantiles)

        # do the same for gas eui
        gas_eui_quantiles = df_full.groupby("cycle")["gas_eui"].quantile([0.05, 0.25, 0.50, 0.75, 0.95]).unstack()  # noqa: PD010
        # print(f"Gas Quantiles")
        # print(gas_eui_quantiles)

        df_return = df_full[["property_id", "cycle", "elec_eui", "gas_eui"]]

        # transform df_return to have a key for each cycle and an array of elec_eui
        chart_data_elec = {}
        chart_data_gas = {}
        for year_value in df_return["cycle"].unique():
            chart_data_elec[year_value] = df_return[df_return["cycle"] == year_value]["elec_eui"].dropna().tolist()
            chart_data_gas[year_value] = df_return[df_return["cycle"] == year_value]["gas_eui"].dropna().tolist()

        # return the results and convert NaN to None
        results["elec_quantiles"] = elec_eui_quantiles.to_dict(orient="index")
        results["gas_quantiles"] = gas_eui_quantiles.to_dict(orient="index")
        results["chart_data_elec"] = chart_data_elec
        results["chart_data_gas"] = chart_data_gas
        results["annual_gfa"] = _remove_nan(yearly_gfa.to_dict(orient="records"))
        results["annual_elec"] = _remove_nan(yearly_elec.to_dict(orient="records"))
        results["annual_gas"] = _remove_nan(yearly_gas.to_dict(orient="records"))

        return JsonResponse(
            {"status": "success", "data": results},
            status=status.HTTP_200_OK,
        )
