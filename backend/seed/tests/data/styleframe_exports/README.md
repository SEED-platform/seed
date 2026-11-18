# StyleFrame Export References

These workbooks were generated with StyleFrame 4.2, pandas 3.0.6 and openpyxl
3.1.5 before removing StyleFrame. They capture the previous CTS facility and
facilities-plan exports, including formatting, for both empty and populated
data. The input DataFrames are defined in `seed/tests/test_excel_templates.py`.

The facility references used
`StyleFrame.read_excel_as_template(..., sheet_name="Facility Upload Template")`
followed by `to_excel(..., row_to_add_filters=1)` with its default output sheet
name, `Sheet1`. The facilities-plan references applied StyleFrame to the
`How To Guide` and `3. ECM Data Dictionary` sheets, and ordinary pandas
`to_excel(..., index=False)` to the two data sheets, matching the original view.

Tests compare cell values and types, resolved formatting, row and column
dimensions, filters, sheet settings, and workbook themes. ZIP timestamps and
StyleFrame's randomized named-style identifiers are intentionally not compared.
Do not regenerate these fixtures with the replacement writer: they are the
independent compatibility baseline.
