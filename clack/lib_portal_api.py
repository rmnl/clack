import json
import requests


class PortalAPIError(Exception):

    status_code = '---'
    message = 'Unknown Error'
    code = 'unknown'

    def __init__(self, resp=None):
        super(PortalAPIError, self).__init__()
        if resp is None:
            self.message = 'API failed to return proper answer.'
        else:
            self.status_code = resp.status_code
            try:
                resp = resp.json()
                self.message = resp['message']
                self.code = resp['code']
            except:
                self.message = 'Unknown Error'

    def __str__(self):
        return '{!s}, {!s}, {!s}'.format(self.status_code, self.code, self.message)


class PortalAPI(object):

    session_id = None
    verify = True

    def __init__(self, username=None, password=None, api_url='https://api.jwplayer.com', is_admin=False, verify=True):
        self.username = username
        self.password = password
        self.api_url = api_url[:-1] if api_url.endswith('/') else api_url
        self.is_admin = is_admin
        self.verify = verify
        if not self.verify:
            # Suppress InsecureRequestWarnings
            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    def _call(self, method, endpoint, params=None, data=None, headers={}, auth=True, raw_response=False):
        if auth:
            if self.session_id is None:
                self.init_session()
            headers['Authorization'] = self.session_id
        headers['content-type'] = 'application/json'
        resp = requests.request(
            method.upper(),
            self._url(endpoint),
            data=data,
            params=params,
            headers=headers,
            verify=self.verify,
        )
        if raw_response:
            return resp
        elif resp.status_code == 200:
            resp = resp.json()
            self.session_id = resp.get('signature', None)
            return resp['return_value']
        else:
            raise PortalAPIError(resp=resp)

    def _url(self, endpoint):
        endpoint = endpoint.strip('/ ')
        if self.is_admin:
            return '{!s}/v2/admin/{!s}/'.format(self.api_url, endpoint)
        return '{!s}/v2/{!s}/'.format(self.api_url, endpoint)

    def init_session(self):
        if self.is_admin:
            resp = self.post('sessions', params={
                'login': self.username,
                'password': self.password,
            }, auth=False)
            # Admin session has param in a different place.
            self.session_id = resp['id']
        else:
            resp = self.post('account/sessions/start', params={
                'userEmail': self.username,
                'userPassword': self.password,
            }, auth=False)
        return resp

    def delete(self, endpoint, params=None, **kwargs):
        return self._call('delete', endpoint, params=params, **kwargs)

    def get(self, endpoint, params=None, **kwargs):
        return self._call('get', endpoint, params=params, **kwargs)

    def post(self, endpoint, params=None, **kwargs):
        data = None if params is None else json.dumps(params)
        return self._call('post', endpoint, data=data, params=None, **kwargs)

    def put(self, endpoint, params=None, **kwargs):
        data = None if params is None else json.dumps(params)
        return self._call('put', endpoint, data=data, params=None, **kwargs)
