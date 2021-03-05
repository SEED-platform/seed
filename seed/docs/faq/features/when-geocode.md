---
question: When and how does SEED geocode my data?
tags: [features, geocoding]
---
SEED will attempt to geocode your data with latitude and longitude values only if the following are true:

1. Your organization has a MapQuest API key. You can register for one through MapQuest's website and apply it on your organization settings page.
2. The records being geocoded have address values that can be read by SEED. In your organization column settings page, you can specify which fields and in what order SEED will use to build the full address that will be geocoded by MapQuest.
3. The records being geocoded do not already have latitude and longitude populated. SEED won't override these values, but you can edit and remove these values if you want SEED to attempt to generate them with MapQuest.

SEED will make this attempt in the following cases:

- During the file import process, after you've mapped columns, SEED will automatically attempt geocoding on records.

- On either the properties page or the tax lots page, you can select records and use the "Geocode Selected" button under the Actions menu.

Note: Valid UBID (properties) or ULID (tax lots) values can be parsed to provide a latitude and longitude value. On import, UBID/ULID is used instead of MapQuest if available. On the inventory pages, there's a separate Action menu button to "Decode UBID/ULID for Selected".
