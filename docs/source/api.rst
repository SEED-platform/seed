API
===

Authentication
--------------
Authentication is handled via an authorization token set in an HTTP header.
To request an API token, go to ``/app/#/profile/developer`` and click 'Get a New API Key'.

Every request must include an 'Authorization' HTTP header made up of your username (email) and your
API key, separated with a ':'.  The string must be base 64 encoded per the Basic Auth requirement.

Using Python, use the requests and base 64 library::

    import requests
    import base64

    auth_string = base64.urlsafe_b64encode('{}:{}'.format(user_email, api_key)
    auth_string = 'Basic {}'.format(auth_string)
    header = {
        'Authorization': auth_string,
    }

    >>> header
    >>> {'Authorization': 'Basic dXNlckBzZWVkLXBsYXRmb3JtLm9yZzpiNThmMTJjMzU4NjA2MTYzYzdmZjFlNTUxMjJjNzUxN2ZkMzJhZjRi'}

    result = requests.get('https://seed-platform.org/api/v2/version/', headers=header)
    print result.json()

Using curl, pass the header information in the request (use base64 result from above)::

  curl -H Authorization:"Basic bmljaG9sYXMubG9uZ0BucmVsLmdvdjpiNThmMTJjMzU4NjA2MTYzYzdmZjFlNTUxMjJjNzUxN2ZkMzJhZjRi" http://seed-platform.org/api/v2/version/

If authentication fails, the response's status code will be 302, redirecting the user to ``/app/login``.

Payloads
--------

Many requests require a JSON-encoded payload and parameters in the query string of the url. A frequent
requirement is including the organization_id of the org you belong to. For example::

  curl -H <auth-header> https://seed-platform.org/api/v2/organizations/12/

Or in a JSON payload::

  curl -H <auth-header> \
    -d '{"organization_id":6, "role": "viewer"}' \
    https://seed-platform.org/api/v2/users/12/update_role/

Using Python::

  params = {'organization_id': 6, 'role': 'viewer'}
  result = requests.post('https://seed-platform.org/api/v2/users/12/update_role/',
                         data=json.dumps(params),
                         headers=header)
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
