import json
import requests


class PortalAPIError(Exception):

    status_code = '---'
    message = 'API failed to return proper answer.'
    code = 'invalid_response'

    def __init__(self, resp=None, message=None, code=None):
        super(PortalAPIError, self).__init__()
        if resp is not None:
            self.status_code = resp.status_code
            try:
                resp = resp.json()
                self.message = resp['message']
                self.code = resp['code']
            except:
                self.message = 'Unknown Error'
        self.message = self.message if message is None else message
        self.code = self.code if code is None else code

    def __str__(self):
        return '{!s}, {!s}, {!s}'.format(self.status_code, self.code, self.message)


class PortalAPI(object):

    session_id = None
    verify = True
    tokens = {
        'account': None,
        'site': None,
        'user': None,
    }

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
            self.session_id = resp['return_value'].get('signature')
            return resp['return_value']
        else:
            raise PortalAPIError(resp=resp)

    def _url(self, endpoint):
        endpoint = endpoint.strip('/ ')
        if self.is_admin:
            return '{!s}/v2/admin/{!s}/'.format(self.api_url, endpoint)
        # Auto replace tokens for regular user calls.
        if self.session_id is not None:
            for token in self.tokens:
                endpoint = endpoint.replace('<{!s}Token>'.format(token), self.tokens[token])
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
            # Set useful tokens for autoreplacing.
            try:
                self.tokens['account'] = resp['accounts'].keys()[0]
                self.tokens['user'] = resp['user']['userToken']
                self.tokens['site'] = resp['accounts'][self.tokens['account']]['sites'].keys()[0]
            except (KeyError, IndexError):
                raise PortalAPIError(message="The default tokens for this user could not be found in the "
                                             "session start response.")
        return None

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
