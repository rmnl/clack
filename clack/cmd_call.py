import ast
import csv
import jwplatform
import re

from environment import FIND_USERS_BY
from lib_portal_api import PortalAPI
from lib_portal_api import PortalAPIError


class CallCommands(object):
    """ All functions for making call commands
    """
    # Api settings
    api = 'ac2'
    key = None
    secret = None
    host = None
    method = 'get'
    verify_ssl = True
    output_format = 'json'

    # Stores site token for making botr proxy calls
    botr = None

    # Calltypes
    batch = False
    call_as_user = False
    user_signature = None

    @staticmethod
    def _unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    @staticmethod
    def _normalize_headers(headers):
        """ Set all headers to lowercase, so it's easier to find the right one.
        """
        return dict([(key.lower(), headers[key]) for key in headers])

    def __init__(self, env):
        self.env = env
        opts = env.options
        # Get the environment name
        name = env.default if opts.env is None else opts.env
        # If the name is not set and there is no default we need to
        # check that all other connections params have been set.
        if name is None and (not opts.host or not opts.key or not opts.api):
            return env.abort(
                'You need to setup one configuration with "clack settings add" first or '
                'specify --host, --api, --key and --secret.'
            )
        # Now let's get the rest of the api settings.
        self.api = opts.api if opts.api else env.get(name, 'api')
        self.host = opts.host if opts.host else env.get(name, 'host')
        self.host = self.host if self.host.startswith('http') else "https://{!s}".format(self.host)
        self.verify_ssl = env.get(name, 'verify_ssl', 'yes') == 'yes'
        self.key = opts.key if opts.key else env.get(name, 'key')
        self.secret = None if name is None else env.get_secret(name, self.key)
        # If we don't have a secret, we need to ask for it.
        if self.secret is None:
            self.secret = env.input('Enter your password/secret', hide_input=True)
        # Api type specific settings.
        if self.api == 'ms1':
            self.output_format = opts.format if opts.format else 'py'
        else:  # adm and ac2
            self.method = opts.method.lower() if opts.method else 'get'

    def _pretty_config_map(self, endpoint, params_str):
        config = [
            ('api type', self.api),
            ('api host', self.host),
            ('verify ssl', self.verify_ssl if self.host.startswith('https://') else None),
            ('endpoint', endpoint),
            ('request method', None if self.api == 'ms1' else self.method),
            ('params', params_str),
            ('key/username', self.key),
            ('secret', '********'),
            ('output format', self.output_format),
            ('batch csv file', self.env.options.csv_file),
            ('calling as user', self.env.options.as_user),
            ('find user by', self.env.options.find_user_by if self.env.options.as_user else None),
        ]
        # Filter out None values and return
        return [c for c in config if c[1] is not None]

    def _parse_params(self, params):
        """ Check and prepare the parameters that are needed for this call.
        """
        if params is not None:
            try:
                params = ast.literal_eval(params)
            except:
                return self.env.abort(
                    "The params could not be parsed. Please make sure they are in the right "
                    "format, e.g.: \"{'test': True, 'foo': 'bar'}\""
                )
        if self.botr and params is None:
            params = {'site_token': self.botr}
        elif self.botr:
            params['site_token'] = self.botr
        return params

    def _call_adm(self, endpoint, params):
        if not self.env.has_vpn_access():
            self.env.abort('No VPN Access: Please connect to the VPN first and try again.')
        return self._call_ac2(endpoint, params, admin=True)

    def _call_ac2(self, endpoint, params, admin=False):
        """ Call the JW Player account API and output the response.
        """
        # Set the endpoint
        # Initiate the Portal API.
        ac2_api = PortalAPI(
            username=self.key,
            password=self.secret,
            api_url=self.host,
            is_admin=admin,
            signature=self.user_signature,
            verify=self.verify_ssl,
        )
        # Get the method.
        method = getattr(ac2_api, self.method)
        try:
            resp = method(endpoint, params=params, raw_response=True)
            if resp.status_code == 200:
                return True, resp
            return False, resp
        except PortalAPIError as e:
            return False, e

    def _call_ms1(self, endpoint, params=None):
        """ Call the JW Platform API and output the response
        """
        protocol = 'https'
        if self.host.startswith('http'):
            protocol, self.host = self.host.split('://')
        ms1_api = jwplatform.Client(self.key, self.secret, host=self.host, scheme=protocol, agent='clack')
        try:
            resp = getattr(ms1_api, endpoint.replace('/', '.'))(**params)
            return True, resp
        except jwplatform.errors.JWPlatformError as e:
            return False, e

    def _setup_call_as_user(self, endpoint, params_str=None):
        admin_api = PortalAPI(username=self.key, password=self.secret, api_url=self.host,
                              is_admin=True, verify=self.verify_ssl)
        resp = admin_api.get(
            'v2/admin/accounts',
            params={FIND_USERS_BY[self.env.options.find_user_by]['search_param']: self.env.options.as_user},
            raw_response=True
        )
        if resp.status_code != 200:
            self.env.echo("Error finding user:", style='error', err=True)
            self.env.output_response(resp.json())
            return None

        data = resp.json()
        # The account is always the first account.
        # There should be no exceptions (yet).
        account = data['return_value']['accounts'][0]

        # The user is either the first ADMIN user in the list or the
        # user specified by the email address.
        user = None
        if self.env.options.find_user_by == 'email':
            for u in account['accountUsers']:
                if u['userEmail'] == self.env.options.as_user:
                    user = u
                    break
        else:
            for u in account['accountUsers']:
                if u['role']['roleName'] == 'ADMIN':
                    user = u
                    break
        if user is None:
            user = account['accountUsers'][0]

        # Now let's initiate a session for the user.
        resp = admin_api.post("v2/admin/users/{!s}/session".format(user['userToken']), raw_response=True)
        if resp.status_code == 200:
            data = resp.json()
            self.user_signature = data['return_value']['signature']
            self.key = user['userEmail']
            self.secret = None
            self.api = 'ac2'
        else:
            self.env.echo("Error initiating user sessios:", style='error', err=True)
            return None

        # If we have to make a call to the ms1 api.
        if self.env.options.use_ms1:
            site = None
            # If there's just one site, we use that site/property:
            if len(account['sites']) == 1:
                site = account['sites'][0]
            # If there ar more sites, it depends.
            # If the as_user param belongs to a property we should use
            # that specific property otherwise we use the first
            elif FIND_USERS_BY[self.env.options.find_user_by]['belongs_to'] == 'property':
                for s in account['sites']:
                    if (
                        self.env.options.find_user_by == 'ms1_key' and
                        s['subSystemAccounts'][0]['subSystemToken'] == self.env.options.as_user
                    ) or (
                        self.env.options.find_user_by == 'analytics_token' and
                        s['analyticsToken'] == self.env.options.as_user
                    ):
                        site = s
                        break
            # Otherwise if this is terminal window, we can ask.
            elif self.env.stdout_isatty and self.env.verbose:
                sites = []
                for i, site in enumerate(account['sites'], start=1):
                    sites.append(('{!s}: {!s}'.format(i, site['siteName']), site))
                self.env.echo("This account has multiple sites, please select the one you want to use:")
                self.env.echo("\n".join([s[0] for s in sites]))
                site_nr = self.env.validated_input(
                    'Select a number:',
                    options=["{!s}".format(i) for i in range(1, len(account['sites']) + 1)],
                    error_msg="Please select a number from the list",
                )
                site = sites[int(site_nr) - 1][1]
            # Just use the first site.
            else:
                site = account['sites'][0]
            self.botr = site['siteToken']
            self.method = 'post'
        self.env.options.as_user = None
        return self.call(endpoint, params_str)

    def _filter_response(self, resp, keymap=None):
        """ Filter the return value(s) from the response.
        """
        # Exceptional case:
        if self.env.options.filter_response == "":
            return resp
        # Cleanup keymap and find integers
        if keymap is None:
            keymap = self.env.options.filter_response.split(".")
            for i, key in enumerate(keymap):
                try:
                    intval = int(key)
                    if "{!s}".format(intval) == key:
                        keymap[i] = intval
                except ValueError:
                    continue
        # Find the return value
        for i, key in enumerate(keymap, start=1):
            if key == "*" and isinstance(resp, (list, tuple)):
                return [self._filter_response(j, keymap=keymap[i:]) for j in resp]
            elif isinstance(key, basestring) and isinstance(resp, dict) and resp.get(key) is not None:
                resp = resp.get(key)
            elif isinstance(key, int) and isinstance(resp, (list, tuple)) and len(resp) > key:
                resp = resp[key]
            else:
                return "Error filtering {} at {}".format(
                    ".".join(["{!s}".format(j) for j in keymap]),
                    ".".join(["{!s}".format(j) for j in keymap[:i]])
                )
        return resp

    def _single_call(self, call_method, endpoint, params_str):
        params = self._parse_params(params_str)
        success, resp = call_method(endpoint, params)
        if hasattr(resp, 'headers'):
            self.env.echo("Response headers:", style='heading')
            headers = CallCommands._normalize_headers(resp.headers)
            self.env.echo(self.env.colorize(self.env.create_table(headers)))
        if success:
            title = "Response: "
            if hasattr(resp, 'json'):
                resp = resp.json()
            if self.env.options.filter_response:
                resp = self._filter_response(resp)
                title = "Filtered " + title
            self.env.echo(title, style="heading")
            self.env.output_response(resp)
        else:
            self.env.echo("Error response:", style='error', err=True)
            if hasattr(resp, 'status_code'):
                self.env.echo(self.env.colorize(self.env.create_table({'status code': resp.status_code})))
            if hasattr(resp, 'code') and hasattr(resp, 'message'):
                resp = "{!s}: {!s}".format(resp.code, resp.message)
            elif hasattr(resp, 'content'):
                resp = resp.content if resp.content else "Clack: No response content."
            self.env.echo("{!s}".format(resp), err=True)
        return None

    def _batch_call(self, call_method, endpoint, params_str):
        # Get the number of rows in the csv file. We need that for the progressbar.
        num_rows = sum(1 for line in open(self.env.options.csv_file, 'r')) - 1 if self.env.verbose else 1
        # Now let's process that CSV file.
        table = CallCommands._unicode_csv_reader(open(self.env.options.csv_file, 'r'))
        header_row, results = None, {}
        with self.env.progressbar(table, length=num_rows, label='Calling API') as bar:
            for columns in bar:
                if header_row is None:
                    header_row = columns
                    continue
                values = {}
                for i, val in enumerate(columns):
                    values[header_row[i]] = val
                call_params = params_str
                for search_for, name in re.findall(r'(<<(\w+)>>)', params_str):
                    call_params = params_str.replace(search_for, values.get(name))
                call_params = self._parse_params(call_params)
                call_endpoint = endpoint
                for search_for, name in re.findall(r'(<<(\w+)>>)', endpoint):
                    call_endpoint = (endpoint.replace(search_for, values.get(name))).strip('/ ')
                success, resp = call_method(call_endpoint, call_params)
                if success and self.env.options.filter_response:
                    results[columns[0]] = self._filter_response(resp)
                elif success:
                    results[columns[0]] = "success"
                else:
                    results[columns[0]] = "Error: {!s}".format(resp)
                bar.update(1)
        # Output the results
        self.env.echo("Call output: ", style='heading')
        self.env.output_response(results)

    def call(self, endpoint, params_str):
        """ The call command.
            Invoked by: clack call
        """
        # The call is made on behalf of another user, that we need to
        # get to know first.
        if self.env.options.as_user:
            return self._setup_call_as_user(endpoint, params_str)

        # Format the endpoint nicely
        endpoint = endpoint.strip('/ ')
        if not endpoint.startswith('v2/'):
            endpoint = 'v2/' + endpoint
        if self.api == 'adm' and not endpoint.startswith('v2/admin/'):
            endpoint = 'v2/admin/' + endpoint[3:]
        if self.api == 'ac2' and self.botr and not endpoint.startswith('v2/proxy/botr/'):
            endpoint = 'v2/proxy/botr/' + endpoint[3:]

        # Let's show what settings we will be using for the call
        self.env.echo("Call settings:", style='heading')
        self.env.echo(self.env.colorize(self.env.create_table(self._pretty_config_map(endpoint, params_str))))
        call_method = getattr(self, '_call_{!s}'.format(self.api))

        # SINGLE CALL
        if self.env.options.csv_file:
            return self._batch_call(call_method, endpoint, params_str)
        else:
            return self._single_call(call_method, endpoint, params_str)
