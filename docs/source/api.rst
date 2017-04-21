API
===

Authentication
--------------
Authentication is handled via an authorization token set in an http header.
To request an API token, go to ``/app/#/profile/developer`` and click 'Get a New API Key'.

Every request must include an 'Authorization' http header made up of your username (email) and your
API key, separated with a ':'.  For example, with curl::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e https://seed-platform.org/api/v2/schema/
  
Or using the Python Requests library::

  headers = {'authorization': 'user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e'}
  result = requests.get('https://seed-platform.org/api/v2/schema/', headers=headers)
  print result.json()

If authentication fails, the response's status code will be 302, redirecting the user to ``/app/login``.


Payloads
--------

Many requests require a JSON-encoded payload and parameters in the query string of the url. A frequent
requirement is including the organization_id of the org you belong to. For example::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e \
    https://seed-platform.org/api/v2/organizations/12/

Or in a JSON payload::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e \
    -d '{"organization_id":6, "role": "viewer"}' \
    https://seed-platform.org/api/v2/users/12/update_role/
    
Using Python::

  headers = {'authorization': 'user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e'}
  params = json.dumps({'organization_id': 6, 'role': 'viewer'})
  result = requests.post('https://seed-platform.org/api/v2/users/12/update_role/',
                         data=params,
                         headers=headers)
  print result.json()  



Responses
---------

Responses from all requests will be JSON-encoded objects, as specified in each endpoint's documentation.
In the case of an error, most endpoints will return this instead of the expected payload (or an HTTP status code)::

.. code-block::

    {
        "status": "error",
        "message": "explanation of the error here"
    }
 

API-Endpoints
-------------

A list of interactive endpoints are available by accessing the API menu item on the left navigation
pane within you account on your SEED instance.

To view a list of non-interactive endpoints without an account, view swagger_ on the development server.

.. _swagger: https://seed-platform.org/app/api/swagger/
