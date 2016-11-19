API
===

Authentication
--------------
Authentication is handled via an authorization token set in an http header.
To request an API token, go to ``/app/#/profile/developer`` and click 'Get a New API Key'.

Every request must include an 'Authorization' http header made up of your username (email) and your API key,
separated with a ':'.  For example, with curl::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e https://seeddomain.com/api/v2/schema/
  
Or using the Python Requests library::

  headers = {'authorization': 'user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e'}
  result = requests.get('https://seeddomain.com/api/v2/schema/', headers=headers)
  print result.json()

If authentication fails, the response's status code will be 302, redirecting the user to ``/app/login``.


Payloads
--------

Many requests require a JSON-encoded payload and/or parameters in the query string of the url.  A frequent
requirement is including the organization_id of the org you belong to.  E.g.::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e \
    https://seeddomain.com/app/accounts/get_organization?organization_id={your org id here}

Or in a JSON payload::

  curl -H Authorization:user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e \
    -d '{"organization_id":6, "user_id": 12, "role": "viewer"}' \
    https://seeddomain/app/accounts/update_role/
    
Using Python::

  headers = {'authorization': 'user@email_address.com:5edfd7f1f0696d4139118f8b95ab1f05d0dd418e'}
  params = json.dumps({'organization_id': 6, 'user_id': 12, 'role': 'viewer'})
  result = requests.post('https://seeddomain.com/app/accounts/update_role/',
                         data=params,
                         headers=headers)
  print result.json()  


Responses
---------

Responses from all requests will be JSON-encoded objects, as specified in each endpoint's documentation.
In the case of an error, most endpoints will return this instead of the expected payload (or an HTTP status code)::

    {
        'status': 'error',
        'message': 'explanation of the error here'
    }
 

API-related Endpoints
---------------------

A PDF of the endpoints is available here :download:`pdf <API_endpoints.pdf>`.

.. note::

    The PDF is slightly out-of-date and swagger will be replacing its use
    in the upcoming release.

.. automodule:: seed.views.api
    :members:
    :undoc-members:

Account Management Endpoints
----------------------------

.. automodule:: seed.views.users
    :members:
    :undoc-members:

File Upload Endpoints
---------------------

These endpoints behave drastically differently depending on whether the system is configured to upload files to S3 or
to the local file system.

.. automodule:: seed.data_importer.views
    :members: handle_s3_upload_complete, local_uploader, get_upload_details, sign_policy_document


SEED (Building and Project) Endpoints
-------------------------------------

.. automodule:: seed.views.main
    :members:
    :undoc-members:
