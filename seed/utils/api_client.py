"""
Demo and testing features for interacting with a SEED API.
"""
import requests
import simplejson as json
from datetime import datetime, timedelta
from calendar import timegm
import os


class APIClient(object):
    """
    Implementation of a demonstration client for using SEED's API.

    Example Usage::

        client = APIClient('http://seeddomain.com',
                           api_key='your_key_here',
                           email_address='youremail@address.com')

        #get all orgs user belongs to
        client.get_organizations()

        #organization id 17 will now be used for most requests
        client.set_organization(17)

        #create a dataset
        client.create_dataset('dataset name here')
        >>> {u'id': 34, u'name': u'test_data_set2', u'status': u'success'}

        #upload a file
        client.upload_file('/path/to/file', 34, 'Assessed Raw')
        >>> {'import_file_id': 54,
             'success': true,
             'filename': 'DataforSEED_dos15.csv'}

        # save the file's to the DB as raw buildings
        client.save_raw_data(payload={'file_id': 54})
        >>> {u'progress_key': u':1:SEED:save_raw_data:PROG:54',
             u'status': u'success'}

        # check the progress of the saving
        client.progress(
            payload={'progress_key':':1:SEED:save_raw_data:PROG:54'}
        )
        >>> {u'progress': 78,
             u'progress_key': u':1:SEED:save_raw_data:PROG:54'}

    For nearly all endpoints, functions named for the endpoint are created
    from the get_api_schema endpoint.  If an endpoint requires a payload
    it can be provided as a dictionary to the keyword 'payload'::

        client.update_project(
            payload={'project':
                {'project_slug': 'myproject',
                 'name': 'My Project',
                 'description': 'My description here',
                 'end_date': 1407231741,
                 'deadline_date': 1407200000
                 }
            }
        >>> {'status': 'success'}

    If an endpoint requires a GET query string, provide those parameters as
    a dict to the keyword 'params'::

        client.get_import_file(params={'import_file_id': 54})
        >>> {'status': 'success',
             'import_file': {<snip>}
            }
    """

    def __init__(self, base_url, api_key="", email_address=""):
        """
        Creates a client.  API endpoints are loaded from the API and
        added as dynamic methods on this object at instantiation.
        See get_schema().

        Args::
            base_url: The base domain for the SEED instance.
            api_key: The user's api key (can be retrieved from
                /app/#/profile/developer
            email_address: The user's email address.
        """
        self.base_url = base_url
        self.email_address = email_address
        self.no_org_uris = []  # start with none for initial schema request
        self.org_id = None

        if api_key and email_address:
            self.authorization = "%s:%s" % (email_address, api_key)
        else:
            self.authorization = None
        self.schema = self._request('/app/api/get_api_schema')
        self.schema_uri_by_name = {e['name']: k
                                   for k, e in self.schema.iteritems()}

        #list of endpoint uris which should not have organization_id passed
        self.no_org_uris = [self.schema_uri_by_name['sign_policy_document']]

        for name in self.schema_uri_by_name:
            if hasattr(APIClient, name):
                continue

            def make_function(name):
                fn = lambda obj, **args: obj._request(name=name, **args)
                endpoint = self._get_endpoint_by_name(name)
                fn.__doc__ = endpoint['description']
                fn.__name__ = str(endpoint['name'])  # de-unicode it
                return fn

            setattr(APIClient, name, make_function(name))

    def _get_endpoint_by_name(self, name):
        """
        Retrieve an endpoint's full details, given its name.
        """
        uri = self.schema_uri_by_name[name]
        endpoint = self.schema[uri]
        endpoint['uri'] = uri
        return endpoint

    def get_schema(self):
        """
        Retrieves all of the API endpoints for this SEED instance.
        """
        return self.schema

    def describe(self, what):
        """
        Provides a human-readable description of an endpoint, specified
        either by name or URI.
        E.g.::

            client.describe('save_match')
            >>> save_match
            >>> /app/save_match/
            >>> Adds or removes a match between two BuildingSnapshots[...]

        """
        if what in self.schema_uri_by_name:
            endpoint = self._get_endpoint_by_name(what)
            uri = endpoint['uri']
        elif what in self.schema:
            uri = what
            endpoint = self.schema[what]
        else:
            print "Endpoint matching %s not found" % what
            return

        print endpoint['name']
        print uri
        print endpoint['description']

    def set_organization_id(self, org_id):
        """
        Sets the client's organization_id.  As this is needed for most
        requests, you can set it once and include it in all requests.

        Args:
          org_id: An ID of an org the user belongs to.  Will validate against
              the API.
        """
        orgs = self.get_organizations()
        orgs_by_id = {org['id']: org
                      for org in orgs}

        if org_id not in orgs_by_id:
            msg = "User %s is not in org with id %s" % (
                self.email_address, org_id
            )
            raise RuntimeError(msg)
        self.org_id = org_id

    def _request(
        self, uri=None, name=None, method=None, payload=None, headers=None,
        params=None
    ):
        """
        Wrapper for making a request to an API endpoint, either by name or uri.

        Args:
            uri: The path to the endpoint (sans domain). Optional if name used.
            name: The name of the endpoint. Optional if uri used.
            method: The http method to use. Generally optional.
            payload: A json-encodable object to include in the request body
            headers: Additional headers to provide for request. Optional;
                Authorization header will automatically be included.
            params: A dict of parameters to include in the GET query string.

        Returns:
            Either the json from the response body, if possible, or the
            full response if no json-decodable body is returned.
        """

        if uri is None and name is not None:
            uri = self.schema_uri_by_name[name]
            if method is None and name.startswith('get_'):
                method = 'get'

        if method is None:
            if payload is not None:
                method = 'post'
            else:
                method = 'get'
        method = method.lower()  # in case one was passed in uppercase

        if headers is None:
            headers = {}
        if self.authorization:
            headers['authorization'] = self.authorization

        if params is None:
            params = {}

        if payload is None:
            payload = {}

        #if we have an org id, try to include it in the params or payload
        if self.org_id and uri not in self.no_org_uris:
            if method == 'get':
                if 'organization_id' not in params:
                    params['organization_id'] = self.org_id
            else:
                if 'organization_id' not in payload:
                    payload['organization_id'] = self.org_id

        # json serialization of payload
        if payload:
            if not isinstance(payload, basestring):
                payload = json.dumps(payload)

        fn = getattr(requests, method)
        _url = self.base_url + uri

        response = fn(_url, data=payload, params=params, headers=headers)

        try:
            return response.json()
        except json.JSONDecodeError:
            return response

    def get_organizations(self):
        """
        Example method for overriding the autogenerated methods.

        Returns:
            All organizations the user belongs to.
            See ``seed.views.accounts.get_organizations()''
        """
        return self._request(name='get_organizations')['organizations']

    def create_dataset(self, name):
        """
        Example method including a payload.

        Args:
            name: The name of the new dataset.
        Returns:
            {'id': 34, 'name': name, 'status': 'success'}
        """
        payload = {'name': name}
        return self._request(name='create_dataset',
                             payload=payload)

    def upload_file(
        self, filepath, import_record_id, source_type
    ):
        """
        Determines the correct method to upload a file (S3 or direct)
        and does so.  Makes use of several endpoints in the process,
        depending on where the SEED instance stores files.

        Args:
            filepath: Full path to file on local filesystem.
            import_record_id: ID of the dataset to associate file with.
            source_type: Usually one of 'Assessed Raw' or 'Portfolio Raw'

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
        """
        upload_details = self._request(name='get_upload_details')
        if upload_details['upload_mode'] == 'S3':
            return self._upload_file_to_s3(
                filepath, upload_details, import_record_id, source_type
            )
        elif upload_details['upload_mode'] == 'filesystem':
            return self._upload_file_to_filesystem(
                filepath, upload_details, import_record_id, source_type
            )
        else:
            raise RuntimeError("Upload mode unknown: %s" %
                               upload_details['upload_mode'])

    def _upload_file_to_filesystem(
        self, filepath, upload_details, import_record_id, source_type
    ):
        """
        Implements uploading to SEED's filesystem. Used by
        upload_file if SEED in configured for local file storage.

        Args:
            filepath: full path to file
            upload_details: Results from 'get_upload_details' endpoint;
                contains details about where to send file and how.
            import_record_id: What ImportRecord to associate file with.
            source_type: Type of data in file (Assessed Raw, Portfolio Raw)

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
        """
        filename = os.path.basename(filepath)
        upload_url = "%s%s" % (self.base_url, upload_details['upload_path'])
        params = {
            'qqfile': filename,
            'import_record': import_record_id,
            'source_type': source_type
        }
        headers = {'authorization': self.authorization}
        return requests.post(upload_url,
                             params=params,
                             files={'filename': open(filepath, 'rb')},
                             headers=headers)

    def _upload_file_to_s3(
        self, filepath, upload_details, import_record_id, source_type
    ):
        """
        Implements uploading a data file to S3 directly.
        This is a 3-step process:
        1. SEED instance signs the upload request.
        2. File is uploaded to S3 with signature included.
        3. Client notifies SEED instance when upload completed.
        @TODO: Currently can only upload to s3.amazonaws.com, though there are
            other S3-compatible services that could be drop-in replacements.

        Args:
            filepath: full path to file
            upload_details: Results from 'get_upload_details' endpoint;
                contains details about where to send file and how.
            import_record_id: What ImportRecord to associate file with.
            source_type: Type of data in file (Assessed Raw, Portfolio Raw)

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
        """
        filename = os.path.basename(filepath)
        #step 1: get the request signed
        sig_uri = upload_details['signature']

        payload = {}
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)
        now_ts = timegm(now.timetuple())
        key = 'data_imports/%s.%s' % (filename, now_ts)

        payload['expiration'] = expires.isoformat() + 'Z'
        payload['conditions'] = [
            {'bucket': upload_details['aws_bucket_name']},
            {'Content-Type': 'text/csv'},
            {'acl': 'private'},
            {'success_action_status': '200'},
            {'key': key}
        ]

        sig = self._request(sig_uri, payload=payload)

        #step2: upload the file to S3
        upload_url = "http://%s.s3.amazonaws.com/" % (
            upload_details['aws_bucket_name']
        )

        #s3 expects multipart form encoding with files at the end, so this
        #payload needs to be a list of tuples; the requests library will encode
        #it property if sent as the 'files' parameter.
        s3_payload = [
            ('key', key),
            ('AWSAccessKeyId', upload_details['aws_client_key']),
            ('Content-Type', 'text/csv'),
            ('success_action_status', '200'),
            ('acl', 'private'),
            ('policy', sig['policy']),
            ('signature', sig['signature']),
            ('file', open(filepath, 'rb'))
        ]

        res = requests.post(upload_url, files=s3_payload)

        if res.status_code != 200:
            msg = "Something went wrong with the S3 upload: %s" % res.content
            raise RuntimeError(msg)

        #Step 3: Notify SEED about the upload
        completion_uri = upload_details['upload_complete']
        completion_payload = {
            'import_record': import_record_id,
            'key': key,
            'source_type': source_type
        }
        return self._request(completion_uri,
                             params=completion_payload,
                             method='get')
