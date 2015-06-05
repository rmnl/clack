
import hashlib
import httplib2
import random
import time
import json
import urllib


class UnifiedAPI(object):
    
    def __init__(self, key, secret, host=None, protocol="https"):
        if not host:
            host = "api.jwplayer.com/v2"
        self._url = '%s://%s' % (protocol, host)
        self._secret = secret
        self._key = key
        self.api = httplib2.Http(disable_ssl_certificate_validation=True)

    def call(self, endpoint, http_method, params=None):
        http_method = http_method.upper()
        if params is None:
            params = {}
        if http_method in ["PUT", "POST"]:
            json_params = urllib.quote_plus(json.dumps(params))
            params = { 'post_data': json_params }
        headers = { 'Content-type': 'text/plain;charset=UTF-8' }
        body = None
        request_url = "%s%s?%s" % (self._url, endpoint, self._build_query_string(params))
        response, content = self.api.request(request_url, http_method, body=body, headers=headers)
        return content

    def _build_query_string(self, params):
        params['api_nonce'] = str(random.randint(0, 99999999)).zfill(8)
        params['api_timestamp'] = int(time.time())
        params['api_key'] = self._key
        params['api_format'] = "json"
        sbs = ""
        for key in sorted(params.keys()):
            if sbs != "":
                sbs += "&"
            sbs += key + "=" + str(params[key])
        api_signature = hashlib.sha1(sbs + self._secret)
        return sbs + '&api_signature=' + api_signature.hexdigest()

