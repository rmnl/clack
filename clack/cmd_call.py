import ast
import csv
import jwplatform
import re

from environment import Environment
from environment import Options
from lib_portal_api import PortalAPI
from lib_portal_api import PortalAPIError


class CallCommands(object):
    """ All functions for making call commands
    """

    @staticmethod
    def _call_ac2(env, config, endpoint, params, batch=False):
        """ Call the JW Player account API and output the response.
        """
        if endpoint.startswith('v2/'):
            endpoint = endpoint[3:]
        if config.is_admin is False and endpoint.startswith('admin'):
            endpoint = endpoint[5:]
            config.is_admin = True
        ac2_api = PortalAPI(username=config.key, password=config.secret, api_url=config.host,
                            is_admin=config.is_admin, verify=config.verify_ssl)
        method = getattr(ac2_api, config.method)
        try:
            resp = method(endpoint, params=params, raw_response=True)
        except PortalAPIError as e:
            env.echo("Portal API Error:", style='error', err=True)
            env.echo("{!s}".format(e), err=True)
            return None
        resp_headers = CallCommands.normalize_headers(resp.headers)
        if batch and env.options.filter_response is None:
            return str(resp.status_code)
        elif batch:
            return CallCommands._filter_response(env.options.filter_response.split("."), resp)
        else:
            env.echo("Response headers: ", style='heading')
            env.echo(env.colorize(env.create_table(resp_headers)))
            if env.options.filter_response is None:
                env.echo("Response body:", style='heading')
                env.output_response(resp.json())
            else:
                env.echo("Return value: ", style="heading")
                env.output_response(CallCommands._filter_response(env.options.filter_response.split("."), resp))

    @staticmethod
    def _call_ms1(env, config, endpoint, params=None, batch=False):
        """ Call the JW Platform API and output the response
        """
        protocol, host = 'https', config.host
        if host.startswith('http'):
            protocol, host = host.split('://')
        jc = jwplatform.Client(config.key, config.secret, host=host, scheme=protocol, agent='clack')
        try:
            resp = getattr(jc, endpoint.replace('/', '.'))(**params)
            if batch and env.options.filter_response is None:
                return "success"
            elif batch:
                return CallCommands._filter_response(env.options.filter_response.split("."), resp)
            elif env.options.filter_response is None:
                env.echo("Response body:", style='heading')
                env.output_response(resp)
            else:
                env.echo("Return value: ", style="heading")
                env.output_response(CallCommands._filter_response(env.options.filter_response.split("."), resp))
        except jwplatform.errors.JWPlatformError as e:
            if batch:
                return "error"
            env.echo("Error response:", style='error', err=True)
            env.echo("{!s}".format(e), err=True)

    @staticmethod
    def _filter_response(keymap, resp, parse_int=True):
        """ Filter the return value(s) from the response.
        """
        # Exceptional case:
        if len(keymap) == 1 and not keymap[0]:
            return resp
        # Cleanup keymap and find integers
        if parse_int:
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
                return [CallCommands._filter_response(keymap[i:], j, parse_int=False) for j in resp]
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

    @staticmethod
    def _api_config(env):
        """ Collect the settings that we need for making the API calls
        """
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
        key = opts.key if opts.key else env.get(name, 'key')
        secret = None
        if name is not None:
            secret = env.get_secret(name, key)
        if secret is None:
            secret = env.input('Enter your password/secret', hide_input=True)
        host = opts.host if opts.host else env.get(name, 'host')
        api = opts.api if opts.api else env.get(name, 'api')
        config = {
            'env': name,
            'host': host if host.startswith('http') else "https://{!s}".format(host),
            'key': key,
            'secret': secret,
            'verify_ssl': env.get(name, 'verify_ssl', 'yes') == 'yes',
        }
        if api == 'ms1':
            config['format'] = opts.format if opts.format else 'py'
        elif api == 'ac2':
            config['is_admin'] = env.get(name, 'is_admin', 'no') == 'yes'
            config['method'] = opts.method.lower() if opts.method else 'get'
        return api, Options(config)

    @staticmethod
    def _parse_params(env, params):
        """ Check and prepare the parameters that are needed for this call.
        """
        if params is None:
            return {}
        try:
            params = ast.literal_eval(params)
        except:
            params = None
        if not isinstance(params, dict):
            params = None
        if params is None:
            return env.abort(
                "The params could not be parsed. Please make sure they are in the right "
                "format, e.g.: \"{'test': True, 'foo': 'bar'}\""
            )
        return params

    @staticmethod
    def _unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    @staticmethod
    def normalize_headers(headers):
        """ Set all headers to lowercase, so it's easier to find the right one.
        """
        return dict([(key.lower(), headers[key]) for key in headers])

    @staticmethod
    def call(endpoint, params_str, *args, **kwargs):
        """ The call command.
            Invoked by: clack call
        """
        env = Environment(command="call", *args, **kwargs)
        endpoint = endpoint.strip('/ ')
        api, config = CallCommands._api_config(env)
        env.echo("Call settings:", style='heading')
        env.echo(env.colorize(env.create_table(config.dict())))
        call_method = getattr(CallCommands, '_call_{!s}'.format(api))

        # SINGLE CALL
        # Make a single call if no csv file is present.
        if not env.options.csv_file:
            params = CallCommands._parse_params(env, params_str)
            return call_method(env, config, endpoint, params)

        # BATCH CALL
        # Else make a batch call.
        num_rows = sum(1 for line in open(env.options.csv_file, 'r')) - 1
        table = CallCommands._unicode_csv_reader(open(env.options.csv_file, 'r'))
        header_row, results = None, {}
        with env.progressbar(table, length=num_rows, label='Calling API') as bar:
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
                call_params = CallCommands._parse_params(env, call_params)
                call_endpoint = endpoint
                for search_for, name in re.findall(r'(<<(\w+)>>)', endpoint):
                    call_endpoint = (endpoint.replace(search_for, values.get(name))).strip('/ ')
                results[columns[0]] = call_method(env, config, call_endpoint, call_params, batch=True)
                bar.update(1)
        env.echo("")
        env.echo("Batch results: ", style='heading')
        env.output_response(results)
