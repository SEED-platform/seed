API
===

Authentication
--------------
Authentication is handled via an encoded authorization token set in a HTTP header.
To request an API token, go to ``/app/#/profile/developer`` and click 'Get a New API Key'.

Authenticate every API request with your username (email, all lowercase) and the API key via `Basic Auth`_.
The header is sent in the form of ``Authorization: Basic <credentials>``, where credentials is the base64 encoding of the email and key joined by a single colon ``:``.

.. _Basic Auth: https://en.wikipedia.org/wiki/Basic_access_authentication

Using Python, use the requests library::

    import requests

    result = requests.get('https://seed-platform.org/api/version/', auth=(user_email, api_key))
    print result.json()

Using curl, pass the username and API key as follows::

  curl -u user_email:api_key http://seed-platform.org/api/version/

If authentication fails, the response's status code will be 302, redirecting the user to ``/app/login``.

Payloads
--------

Many requests require a JSON-encoded payload and parameters in the query string of the url. A frequent
requirement is including the organization_id of the org you belong to. For example::

  curl -u user_email:api_key https://seed-platform.org/api/v2/organizations/12/

Or in a JSON payload::

  curl -u user_email:api_key \
    -d '{"organization_id":6, "role": "viewer"}' \
    https://seed-platform.org/api/v2/users/12/update_role/

Using Python::

  params = {'organization_id': 6, 'role': 'viewer'}
  result = requests.post('https://seed-platform.org/api/v2/users/12/update_role/',
                         data=json.dumps(params),
                         auth=(user_email, api_key))
  print result.json()

Responses
---------

Responses from all requests will be JSON-encoded objects, as specified in each endpoint's documentation.
In the case of an error, most endpoints will return this instead of the expected payload (or an HTTP status code)::

    {
        "status": "error",
        "message": "explanation of the error here"
    }

API Endpoints
-------------

A list of interactive endpoints are available by accessing the API menu item on the left navigation
pane within you account on your SEED instance.

To view a list of non-interactive endpoints without an account, view swagger_ on the development server.

.. _swagger: https://seed-platform.org/api/swagger/
