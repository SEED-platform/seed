"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import os
import pathlib
import zipfile

import requests
from django.conf import settings

from seed.building_sync.building_sync import BuildingSync

VALIDATION_API_URL = "https://buildingsync.net/api/validate"
DEFAULT_SCHEMA_VERSION = settings.BUILDINGSYNC_VERSION
DEFAULT_USE_CASE = "SEED"


class ValidationClientError(Exception):
    pass


def _validation_api_post(file_, schema_version, use_case_name):
    if zipfile.is_zipfile(file_.name):
        files = [("file", file_)]
    else:
        files = {"file": (file_.name, pathlib.Path(file_.name).read_text(), "application/xml")}

    return requests.request(
        "POST",
        VALIDATION_API_URL,
        data={"schema_version": schema_version},
        files=files,
        timeout=60 * 2,  # timeout after two minutes (it can take a long time for zips)
    )


def validate_use_case(file_, filename=None, schema_version=DEFAULT_SCHEMA_VERSION, use_case_name=DEFAULT_USE_CASE):
    """calls Selection Tool's validation API

    :param file_: File, the file to validate; can be single xml or zip
    :param filename: string, (optional) name of the file, useful if file_.name is not user friendly (e.g., a Django SimpleUploadedFile). Not used if file_ is a zip
    :param schema_version: string
    :param use_case_name: string
    :return: tuple, (bool, list), bool indicates if the file passes validation,
             the list is a collection of files and their errors, warnings, and infos
    """
    if schema_version == BuildingSync.BUILDINGSYNC_V2_0:
        schema_version = BuildingSync.BUILDINGSYNC_V2_0_0

    try:
        response = _validation_api_post(file_, schema_version, use_case_name)
    except requests.exceptions.Timeout:
        raise ValidationClientError(
            "Request to Selection Tool timed out. SEED may need to increase the timeout",
        )
    except Exception as e:
        raise ValidationClientError(
            f"Failed to make request to selection tool: {e}",
        )

    if response.status_code != 200:
        raise ValidationClientError(
            f"Received bad response from Selection Tool: {response.text}",
        )

    try:
        response_body = response.json()
    except ValueError:
        raise ValidationClientError(
            f"Expected JSON response from Selection Tool: {response.text}",
        )

    if response_body.get("success", False) is not True:
        raise ValidationClientError(
            f"Selection Tool request was not successful: {response.text}",
        )

    response_schema_version = response_body.get("schema_version")
    if response_schema_version != schema_version:
        raise ValidationClientError(
            f"Expected schema_version to be '{schema_version}' but it was '{response_schema_version}'",
        )

    _, file_extension = os.path.splitext(file_.name)
    validation_results = response_body.get("validation_results")
    # check the returned type and make validation_results a list if it's not already
    if file_extension == ".zip":
        if not isinstance(validation_results, list):
            raise ValidationClientError(
                f"Expected response validation_results to be list for zip file: {response.text}",
            )
    else:
        if not isinstance(validation_results, dict):
            raise ValidationClientError(
                f"Expected response validation_results to be dict for single xml file: {response.text}",
            )
        # turn the single file result into the same structure as zip file result
        if filename is None:
            filename = os.path.basename(file_.name)
        validation_results = [
            {
                "file": filename,
                "results": validation_results,
            }
        ]

    # check that the schema and use case is valid for every file
    file_summaries = []
    all_files_valid = True
    for validation_result in validation_results:
        results = validation_result["results"]
        filename = validation_result["file"]

        # it's possible there's no use_cases key - occurs when schema validation fails
        if results["schema"]["valid"] is False:
            use_case_result = {}
        else:
            if use_case_name not in results.get("use_cases", []):
                raise ValidationClientError(
                    f'Expected use case "{use_case_name}" to exist in result\'s uses cases.',
                )
            use_case_result = results["use_cases"][use_case_name]

        file_summary = {
            "file": filename,
            "schema_errors": results["schema"].get("errors", []),
            "use_case_errors": use_case_result.get("errors", []),
            "use_case_warnings": use_case_result.get("warnings", []),
        }

        file_has_errors = len(file_summary["schema_errors"]) > 0 or len(file_summary["use_case_errors"]) > 0
        if file_has_errors:
            all_files_valid = False

        file_has_errors_or_warnings = file_has_errors or len(file_summary["use_case_warnings"]) > 0
        if file_has_errors_or_warnings:
            file_summaries.append(file_summary)

    return all_files_valid, file_summaries
