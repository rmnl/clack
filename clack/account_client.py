# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Python API kit for the Bits on the Run System API
#
# Author:      Sergey Lashin
# Copyright:   (c) 2010 - 2011 LongTail Ad Solutions
# License:     GNU Lesser General Public License, version 3
#              http://www.gnu.org/licenses/lgpl-3.0.txt
#
# Updated:     Thu Mar 31 09:09:20 CEST 2011
#
# For the documentation see http://developer.longtailvideo.com/botr/system-api/
#------------------------------------------------------------------------------

__version__ = '1.3'

import types
import hashlib
import pickle
import random
import StringIO
import time
import urllib

try:
    import pycurl as url_lib
except ImportError:
    import urllib2 as url_lib

class ApiClientException(Exception):

    def __init__(self, *args):
        self.args = args

    def __str__(self):
        if len(self.args) == 1:
            return str(self.args[0])
        else:
            return str(self.args)

    def __repr__(self):
        return "%s(*%s)" % (self.__class__.__name__, repr(self.args) if self.args else "")

class API(object):
    """
    API
    ===
    An interface to the Bits on the Run API
    """

    def __init__(self, key, secret, protocol='http', host=None, port=None,
                 version='v1', client=None):
        """Initialize BotR API

           @type key: str
           @param key: API User key

           @type secret: str
           @param secret: API User secret

           @type protocol: str
           @param protocol: API server protocol. Default is 'http'.

           @type host: str
           @param host: API server host name, e.g.:
                        - 'api.bitsontherun.com' or
                        - '127.0.0.1'
                        Default is 'api.bitsontherun.com'.

           @type port: str
           @param port: API server port. Default is '80'.

           @type version: str
           @param version: Version of the API to use. Default is 'v1'.

           @type client: str
           @param client: API client identification string.
        """

        if not host:
            host = "api.bitsontherun.com"

        self._key = key
        self._secret = secret
        self._url = '%s://%s%s/%s' % (protocol, host, ':%s' % port if port else '', version)
        self._kit_version = u'py-%s%s' % (__version__, '-%s' % client if client else '')

    def call(self, api_call, params=dict(), verbose=False):
        """Prepare an API call"""

        if params is None:
            params = dict()

        if not isinstance(params, types.DictType):
            raise TypeError("'params' argument must be a dict, not %s" % type(params).__name__)

        params = params.copy()

        url = self.call_url(api_call, params)

        if 'api_format' not in params:
            params['api_format'] = 'py'

        return self._execute(url, response_format=params['api_format'], verbose=verbose)

    def call_url(self, api_call, params=dict()):
        """Construct call URL"""

        if not isinstance(params, types.DictType):
            raise TypeError("'params' argument must be a dict, not %s" % type(params).__name__)

        params = params.copy()

        url = str(self._url + (api_call if api_call else ''))
        query = self._signed_query_string(params)
        url = url + '?' + query
        return url

    def upload(self, params, file_path, verbose=False):
        """Prepare an upload API call"""

        if not isinstance(params, types.DictType):
            raise TypeError("'params' argument must be a dict, not %s" % type(params).__name__)

        params = params.copy()

        params['query']['api_kit'] = self._kit_version
        if ('api_format' not in params['query']):
            # Use serialised Python format for the API output,
            # otherwise use format specified in the params.
            params['query']['api_format'] = 'py'

        url = self.upload_url(params)

        return self._execute(url, file_path, response_format=params['query']['api_format'],
                             verbose=verbose)

    def upload_url(self, params):
        """Construct upload URL"""

        if not isinstance(params, types.DictType):
            raise TypeError("'params' argument must be a dict, not %s" % type(params).__name__)

        params = params.copy()

        url = params['protocol'] + u"://" + params['address'] + params['path']
        query = self.query_string(params['query'])
        url = url + '?' + query

        return url

    def _execute(self, request_url, file_path=None, response_format='py', verbose=False):
        """Execute an API call

           Returns a Python dictionary if response format is 'py' or a string for other formats.
        """

        call_failed = False
        response = str()
        response_content_type = str()
        response_redirect_url = None

        request_url = str(request_url)

        if url_lib.__name__ == 'pycurl':
            curl = url_lib.Curl()

            curl.setopt(curl.URL, request_url)

            if file_path:
                post = [('file', (curl.FORM_FILE, str(file_path)))]
                curl.setopt(curl.HTTPPOST, post)
                if verbose:
                    # Show upload progress
                    curl.setopt(curl.NOPROGRESS, False)
                    curl.setopt(curl.PROGRESSFUNCTION, self._progress)
            else:
                curl.setopt(curl.HTTPGET, True)

            if verbose:
                # Enable verbose output
                curl.setopt(curl.VERBOSE, True)

            # Do not verify that the host name used in the server's certificate
            # matches the API host name
            curl.setopt(curl.SSL_VERIFYHOST, False)

            # Write response to a string
            output = StringIO.StringIO()
            curl.setopt(curl.WRITEFUNCTION, output.write)

            try:
                curl.perform()
                response_content_type = curl.getinfo(curl.CONTENT_TYPE)
                response_redirect_url = curl.getinfo(curl.REDIRECT_URL)
                curl.close()

                response = output.getvalue()
            except Exception, e:
                call_failed = True
                response = curl.errstr()
                if verbose:
                    raise ApiClientException(response)

        elif url_lib.__name__ == 'urllib2':
            if file_path:
                raise NotImplementedError("File upload is not supported when using %s library" \
                                          % url_lib.__name__)
            urllib2 = url_lib
            output = None

            try:
                output = urllib2.urlopen(request_url)
            except urllib2.HTTPError, e:
                # In most cases response with HTTP status code >= 400 is a
                # valid error response from the API server.
                output = e
            except urllib2.URLError, e:
                print str(e)
                call_failed = True
                response = e.reason.args[1]
                if verbose:
                    raise ApiClientException(response)
            except Exception, e:
                call_failed = True
                response = str(e)
                if verbose:
                    raise ApiClientException(response)

            if not call_failed:
                response = output.read()
                response_content_type = output.info().type
                response_redirect_url = output.geturl() \
                                        if (output.geturl() != request_url) \
                                        else None

        if len(response) <= 0:
            if verbose:
                raise ApiClientException("API response is empty")
            else:
                response = {'status': 'error',
                            'code': 'EmptyResponse',
                            'title': 'Empty Response',
                            'message': 'API response is empty'}
        elif response_format == 'py':
            if call_failed:
                response = {'status': 'error',
                            'code': 'CallFailed',
                            'title': 'API Call Failed',
                            'message': response}
            else:
                try:
                    response = pickle.loads(response)
                    if response_redirect_url:
                        response['redirect_url'] = response_redirect_url
                except Exception, e:
                    if verbose:
                        raise ApiClientException(("Failed to parse response", response))
                    else:
                        if (response_content_type.find('application/python') >= 0):
                            # Error while parsing response in pickle format
                            response = {'status': 'error',
                                        'code': 'ParsingError',
                                        'title': 'Parsing Error',
                                        'message': 'An error has occurred while parsing API response'}
                        else:
                            # API server response is not in pickle format
                            response = {'status': 'error',
                                        'code': 'FormatError',
                                        'title': 'Format Error',
                                        'message': 'Unsupported API response format'}

        return response

    def _signed_query_string(self, params):
        """Convert params dict to a query string and sign it"""

        if not isinstance(params, types.DictType):
            raise TypeError("'params' argument must be a dict, not %s" % type(params).__name__)

        params = params.copy()

        # Add required API parameters
        params['api_nonce'] = str(random.randint(0, 99999999)).zfill(8)
        params['api_timestamp'] = int(time.time())
        params['api_key'] = self._key
        params['api_kit'] = self._kit_version

        if 'api_format' not in params:
            # Use serialised Python format for the API output,
            # otherwise use format specified in the call() params.
            params['api_format'] = 'py'

        # Construct Signature Base String
        sbs = self.query_string(params, sort=True)

        # Generate signature
        api_signature = hashlib.sha1(sbs + self._secret).hexdigest()

        return sbs + '&api_signature=' + api_signature

    @staticmethod
    def query_string(params, sort=False):
        """Convert parameters dictionary to a query string"""

        params = params.copy()

        # Convert parameters names and values to UTF-8 and escape them
        for key, value in params.items():
            del params[key]
            key = urllib.quote((unicode(key).encode("utf-8")), safe='~')
            value = urllib.quote((unicode(value).encode("utf-8")), safe='~')
            params[key] = value

        if sort:
            return '&'.join(['%s=%s' % (key, value) for key, value in sorted(params.items())])
        else:
            return '&'.join(['%s=%s' % (key, value) for key, value in params.items()])

    def _progress(self, download_t, download_d, upload_t, upload_d):
        """On download/upload progress callback function"""

        import sys
        uploaded = 0
        if upload_t:
            uploaded = upload_d * 100 / upload_t
        sys.stdout.write(chr(27) + '[2K' + chr(27)+'[G')
        sys.stdout.write("Uploaded: %.2f%%" % uploaded)
