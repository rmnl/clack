# -*- coding: utf-8 -*-

# botrlib/client.py
#
# Author:      Sergey Lashin
# Copyright:   (c) 2012 LongTail Ad Solutions. All rights reserved.
# License:     BSD 3-Clause License
#              See LICENSE file provided with this project for the
#              license terms.

import os
import re
import time
import pickle
import random
import urllib
import hashlib
import logging
from pprint import pformat
from types import DictType
from contrib import urllib3
from contrib.botrlib import __version__

_log = logging.getLogger(__name__)

urllib3.disable_warnings()

RESUMABLE_UPLOAD_RANGE = re.compile(r'^0-(?P<range_end>\d+)')


class Client(object):
    """BotR API Client"""

    def __init__(self, key, secret, protocol='http', host=None, port=None,
                 version='v1', client=None):
        """Initialize BotR API Client

        @type key: str
        @param key: API User key

        @type secret: str
        @param secret: API User secret

        @type protocol: str
        @param protocol: Connection protocol:
                         - 'http'
                         - 'https'
                         Default is 'http'.

        @type host: str
        @param host: API server host name, e.g.:
                     - 'api.jwplatform.com'
                     - '127.0.0.1'
                     Default is 'api.jwplatform.com'.

        @type port: str
        @param port: API server port. Default is '80'.

        @type version: str
        @param version: Version of the API to use. Default is 'v1'.

        @type client: str
        @param client: API client identification string.
        """

        if not host:
            host = "api.jwplatform.com"

        self._key = key
        self._secret = secret
        self._api_version = version
        self._kit_version = u"py-%s%s" % (__version__, '-%s' % client if client else '')
        self._connection_url = "%s://%s%s" % (protocol, host, ":%s" % port if port else '')
        self._connection = urllib3.connection_from_url(self._connection_url)
        self._upload_connections = urllib3.PoolManager(num_pools=7)
        self._request_method = 'GET'
        self._base_url = "%s/%s" % (self._connection_url, self._api_version)
        self._url = None
        self._response_format = None

    def _get_request_method(self):
        """Get default request method."""
        return self._request_method

    def _set_request_method(self, method):
        """Set default request method."""
        self._request_method = method

    request_method = property(_get_request_method, _set_request_method)

    @property
    def base_url(self):
        """Get base request URL."""
        return self._base_url

    @property
    def request_url(self):
        """Get last request URL."""
        return self._url

    def request(self, path, query_params=dict()):
        """Make an API request."""

        if query_params is not None:
            if not isinstance(query_params, DictType):
                raise TypeError("'query_params' argument must be a dict, not %s" \
                        % type(query_params).__name__)
            query_params = query_params.copy()
        else:
            query_params = dict()

        # Add required API parameters
        query_params['api_nonce'] = str(random.randint(0, 999999999)).zfill(9)
        query_params['api_timestamp'] = int(time.time())
        query_params['api_key'] = self._key
        query_params['api_kit'] = self._kit_version

        if 'api_format' not in query_params:
            # Use serialised Python format for the API output,
            # otherwise use format specified in the request() query_params.
            query_params['api_format'] = 'py'
        self._response_format = query_params['api_format']

        # Construct Signature Base String
        sbs = self._dict2query_string(query_params, sort=True)

        # Generate signature
        query_params['api_signature'] = hashlib.sha1(sbs + self._secret).hexdigest()

        self._url = "%s://%s/%s%s" % (self._connection.scheme, self._connection.host,
                self._api_version, path if path else '')

        headers = {
            'User-Agent': 'python-botrlib/%s' % __version__
        }

        if self._request_method.upper() in ('GET', 'HEAD', 'DELETE'):
            self._url += "?%s&api_signature=%s" % (sbs, query_params['api_signature'])

            _log.debug("\nRequest: \'%s %s\'\nRequest headers:\n%s\n" \
                    % (self._request_method, self._url, pformat(headers)))

            response = self._request(True,
                    self._connection.request_encode_url,
                    self._request_method,
                    self._url,
                    headers=headers)
        else: # POST, PUT, PATCH
            _log.debug("\nRequest: \'%s %s\'\nRequest headers:\n%s\nRequest fields:" \
                    "\n%s\n" % (self._request_method, self._url, pformat(headers),
                        pformat(query_params)))

            response = self._request(True,
                    self._connection.request_encode_body,
                    self._request_method,
                    self._url,
                    headers=headers,
                    fields=query_params)

        return response

    def upload(self, query_params, file_path):
        """Upload a file"""

        if not isinstance(query_params, DictType):
            raise TypeError("'query_params' argument must be a dict, not %s" \
                    % type(query_params).__name__)

        query_params = query_params.copy()

        query_params['query']['api_kit'] = self._kit_version
        if ('api_format' not in query_params['query']):
            # Use serialised Python format for the API output,
            # otherwise use format specified in the query_params.
            query_params['query']['api_format'] = 'py'
        self._response_format = query_params['query']['api_format']

        self._url = "%s://%s%s" % (query_params['protocol'],
                query_params['address'],
                query_params['path'])

        query_params['query']['file'] = (os.path.split(file_path)[1],
                open(file_path, 'rb').read())

        headers = {
            'User-Agent': 'python-botrlib/%s' % __version__
        }

        if _log.level == logging.DEBUG:
            request_fields = dict()
            for key, value in query_params['query'].iteritems():
                if key == 'file':
                    request_fields[key] = (value[0], "<data with length %s bytes>" \
                            % len(value[1]))
                else:
                    request_fields[key] = value
            _log.debug("\nRequest: \'POST %s\'\nRequest headers:\n%s\nRequest fields:" \
                    "\n%s\n" % (self._url, pformat(headers), pformat(request_fields)))

        response = self._request(True,
                self._upload_connections.request_encode_body,
                'POST',
                self._url,
                fields=query_params['query'],
                headers=headers,
                redirect=False)

        return response

    def resumable_upload(self, query_params, file_path, session_id,
            chunk_size=None, on_progress=None):
        """Upload a file using resumable protocol"""

        if not isinstance(query_params, DictType):
            raise TypeError("'query_params' argument must be a dict, not %s" \
                    % type(query_params).__name__)

        query_params = query_params.copy()

        query_params['query']['api_kit'] = self._kit_version
        if ('api_format' not in query_params['query']):
            # Use serialised Python format for the API output,
            # otherwise use format specified in the query_params.
            query_params['query']['api_format'] = 'py'
        self._response_format = query_params['query']['api_format']

        self._url = "%s://%s%s?%s" % (query_params['protocol'],
                query_params['address'],
                query_params['path'],
                self._dict2query_string(query_params['query']))

        file_name = os.path.split(file_path)[1]
        file_size = os.path.getsize(file_path)
        file_handle = open(file_path, 'rb')

        if chunk_size is None:
            chunk_size = 1000 * 1000 # 1 MB

        range_start = 0L
        last_range_end = file_size - 1

        while range_start < last_range_end:

            if range_start == 0:
                # Upload only 2 bytes in the first chunk.
                # This is useful when resuming file upload as the first chunk
                # upload is basically used to get already uploaded byte range.
                range_end = 1
            else:
                range_end = range_start + chunk_size - 1

            if range_end > last_range_end:
                range_end = last_range_end

            headers = {
                'User-Agent': 'python-botrlib/%s' % __version__,
                'Content-Type': 'application/octet-stream',
                'Content-Disposition': 'attachment; filename="%s"' % file_name,
                'X-Content-Range': "bytes %d-%d/%d" % (range_start, range_end, file_size),
                'Session-ID': session_id,
            }

            file_handle.seek(range_start)
            file_chunk = file_handle.read(range_end - range_start + 1)

            _log.debug("\nRequest: \'POST %s\'\nRequest headers:\n%s\n" \
                    "Request body:\n<data with length %s bytes>\n" \
                    % (self._url, pformat(headers), len(file_chunk)))

            try:
                response = self._request(False,
                        self._upload_connections.urlopen,
                        'POST',
                        self._url,
                        body=file_chunk,
                        headers=headers,
                        redirect=False)
            except Exception, e:
                file_handle.close()
                return self._render_error_response("CallFailed",
                        "API Call Failed",
                        str(e))

            if (_log.level == logging.DEBUG) and \
               (response.getheader('content-type') != 'application/python'):
                _log.debug("\nResponse status: %s\nResponse headers:\n%s" \
                        "\nResponse data:\n%s\n" \
                        % (response.status, pformat(response.headers),
                            pformat(response.data)))

            if response.status == 201:
                uploaded_range = response.getheader('range')
                match = RESUMABLE_UPLOAD_RANGE.match(uploaded_range)
                if match is None:
                    _log.error("Resetting range_start to 0. Received range " \
                            "`%s` is not recognized" % uploaded_range)
                    range_start = 0L
                else:
                    range_start = long(match.group('range_end')) + 1
            elif response.status in (200, 302):
                range_start += chunk_size
            else:
                _log.error("Unexpected status: %s for response: %s" \
                        % (response.status, response.data))
                break

            if on_progress:
                uploaded = range_start
                if uploaded > file_size:
                    uploaded = file_size
                on_progress(uploaded, file_size)

        file_handle.close()

        return self._process_response(response)

    def _request(self, process_response, request_func, *args, **kwargs):
        """Make and process response using specified request function."""

        response = None

        try:
            response = request_func(*args, **kwargs)
            if process_response == True:
                response = self._process_response(response)
        except urllib3.exceptions.MaxRetryError, e:
            _log.error("Max connection retries exceeded for the request: %s\n" \
                    "Exception: %s" % (self._url, str(e)))
            if process_response == True:
                response = self._render_error_response("CallFailed",
                        "API Call Failed",
                        "Max connection retries exceeded")
            else:
                raise
        except urllib3.exceptions.TimeoutError, e:
            _log.error("Connection socket timeout for the request: %s\n" \
                    "Exception: %s" % (self._url, str(e)))
            if process_response == True:
                response = self._render_error_response("CallFailed",
                        "API Call Failed",
                        "Connection socket timeout")
            else:
                raise
        except Exception, e:
            _log.error("API call failed for the request: %s\n" \
                    "Exception: %s" % (self._url, str(e)))
            if process_response == True:
                response = self._render_error_response("CallFailed",
                        "API Call Failed",
                        str(e))
            else:
                raise

        return response

    def _process_response(self, response):
        """Get and process response data."""

        response_data = response.data

        if len(response_data) > 0:
            if self._response_format == 'py':
                try:
                    response_data = pickle.loads(response_data)
                    _log.debug("\nResponse status: %s\nResponse headers:\n%s" \
                            "\nResponse data:\n%s\n" \
                            % (response.status, pformat(response.headers), pformat(response_data)))
                except Exception, e:
                    if (response.getheader('content-type') == 'application/python'):
                        # Error while parsing response in pickle format
                        _log.debug("\nResponse status: %s\nResponse headers:\n%s" \
                                "\nResponse data:\n%s\n" \
                                % (response.status, pformat(response.headers), pformat(response.data)))
                        _log.error("An error has occurred while parsing API " \
                                "response in pickle format. Response data:\n%s" \
                                % pformat(response.data))
                        response_data = self._render_error_response("ParsingError",
                                "Parsing Error",
                                "An error has occurred while parsing API response")
                    else:
                        # API server response is not in pickle format
                        _log.debug("\nResponse status: %s\nResponse headers:\n%s" \
                                "\nResponse data:\n%s\n" \
                                % (response.status, pformat(response.headers), pformat(response.data)))
                        _log.error("API server response is not in pickle format." \
                                "Response data:\n%s" % pformat(response.data))
                        response_data = self._render_error_response("FormatError",
                                "Format Error",
                                "Unsupported API response format")
        else:
            _log.debug("\nResponse status: %s\nResponse headers:\n%s" \
                    "\nResponse data:\n%s\n" \
                    % (response.status, pformat(response.headers), pformat(response.data)))
            _log.error("Empty response from the API server.\nResponse status: %s" \
                    "\nResponse headers:\n%s" % (response.status, pformat(response.headers)))
            response_data = self._render_error_response("EmptyResponse",
                    "Empty Response",
                    "API response is empty")

        return response_data

    def _render_error_response(self, code, title, message):
        """Render an error response."""

        if self._response_format == 'py':
            response = {'status': 'error',
                        'code': code,
                        'title': title,
                        'message': message}
        elif self._response_format == 'json':
            response = '{"status": "error", ' \
                       '"code": "%s", ' \
                       '"title": "%s", ' \
                       '"message": "%s"}' % (code, title, message)
        elif self._response_format == 'xml':
            response = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                       '<response>\n' \
                       '  <status>error</status>\n' \
                       '  <code>%s</code>\n' \
                       '  <title>%s</title>\n' \
                       '  <message>%s</message>\n' \
                       '</response>' % (code, title, message)
        else:
            response = 'status: error\n' \
                       'code: %s\n' \
                       'title: %s\n' \
                       'message: %s' % (code, title, message)

        return response

    @staticmethod
    def _dict2query_string(query_params, sort=False):
        """Convert parameters dictionary to a query string."""

        query_params = query_params.copy()

        # Convert parameters names and values to UTF-8 and escape them
        for key, value in query_params.items():
            del query_params[key]
            key = urllib.quote((unicode(key).encode("utf-8")), safe='~')
            value = urllib.quote((unicode(value).encode("utf-8")), safe='~')
            query_params[key] = value

        if sort:
            return '&'.join(['%s=%s' % (key, value) for key, value \
                    in sorted(query_params.items())])
        else:
            return '&'.join(['%s=%s' % (key, value) for key, value \
                    in query_params.items()])
