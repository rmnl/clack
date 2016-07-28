# -*- coding: utf-8 -*-

import ast
import calendar
import click
import ConfigParser
import csv
import hashlib
import httplib2
import json
import keyring
import os
import pprint
import re
import shutil
import sys
import textwrap
import time

from botrlib import Client as BotrClient
from distutils.version import StrictVersion

VERSION = '0.5.0'
APP_NAME = 'Clack'
DEFAULTS = {
    'key': '',
    'host': 'api.jwplatform.com',
    'port': None,
    'method': 'post',
}
KEYRING_ID = 'com.github.rmnl.clack.'
DELEGATE_LOGIN_URL = '/delegate_login/'

QUIET = False


class AliasedGroup(click.Group):

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: {!s}'.format(', '.join(sorted(matches))))


def edit_environment(config, update=None, *args, **kwargs):
    defaults = {
        'api': 'ms1',
        'host': 'api.jwplatform.com',
        'key': None,
        'secret': '',
        'description': None,
    }
    if update is None:
        name = user_input(
            "First give a good name for the environment you're going to add. "
            "e.g. ms1-reseller for making calls as a reseller to the media "
            "services api",
            None,
            r'^[a-zA-Z0-9-_]{1,16}$',
            "Please note an environment name needs to consist only "
            "alphanumeric (and _ -) characters and be between 1 and 16 "
            "characters long. Please try again",
        )
    else:
        name = update
        for var in defaults:
            if not var == 'secret':
                try:
                    defaults[var] = config.get(name, var)
                except ConfigParser.NoOptionError:
                    pass
    api = user_input(
        "What type of API is this?\n"
        "  ms1 : media services api (aka botr, jwplatform)\n"
        "  ac2 : account api version 2 (as used by unified dashboard)\n",
        defaults['api'],
        r'^ms1|ac2$',
        'Please choose a valid option and try again',
        wrap=False,
    )
    host = user_input(
        "Please provide the hostname for this environment",
        defaults['host'],
        r'^(http[s]{0,1}:\/\/)*[a-zA-Z0-9-.]+\.(jwplatform|jwplayer|longtailvideo)\.com$',
        "The hostname is not correct, please try again",
    )
    if api == 'ac2':
        key = user_input(
            "Please provide your login/email",
            defaults['key'],
            r'^.*$',
            "",
        )
        secret = user_input(
            "Please provide your password for this user. The password is "
            "stored in your system's password keyring. Leave empty to input "
            "the password with each call",
            defaults['secret'],
            r'^.*$',
            "",
            hide_input=True,
        )
    else:
        key = user_input(
            "Please provide the API key for this user",
            defaults['key'],
            r'^[a-zA-Z0-9]{8,}$',
            "A API is alphanumeric and at least 8 characters long. "
            "Please try again",
        )
        secret = user_input(
            "Please provide the API secret for this user. The secret is "
            "stored in your system's password keyring. Leave empty to input "
            "the secret with each call",
            defaults['secret'],
            r'^[a-zA-Z0-9]{20,}$|^$',
            "A API is alphanumeric and at least 20 characters long. "
            "Please try again",
            hide_input=True,
        )
    description = user_input(
        "Please add a description for this environment",
        defaults['description'],
    )
    if name and host and key and update is None:
        config.add_section(name)
    if name and host and key:
        config.set(name, 'key', key)
        config.set(name, 'host', host)
        config.set(name, 'description', description)
        config.set(name, 'api', api)
    if name and key and secret:
        keyring.set_password(keyring_id(name), key, secret)
    elif name and key and keyring.get_password(keyring_id(name), key):
        keyring.delete_password(keyring_id(name), key)
    return config


def _ac2_get_session(login, password, protocol, host, as_admin=False):
    if as_admin:
        params = {'login': login, 'password': password, }
        resp = call_ac2(protocol, host, '/admin/sessions/', 'POST', params,
                        show_output=False)
        if resp and resp.get('return_value', None) is not None:
            return resp['return_value'].get('id', None)
    else:
        params = {'userEmail': login, 'userPassword': password, }
        resp = call_ac2(protocol, host, '/account/sessions/start/', 'POST',
                        params, show_output=False)
        if resp and resp.get('return_value', None) is not None:
            return resp['return_value'].get('signature', None)
    return None


def _ac2_request_summary(url, method, body, headers):
    return "\n".join([
        "url: {!s}".format(url),
        "method: {!s}".format(method),
        "headers: \n - {!s}".format("\n - ".join([
            "{!s}: {!s}".format(name, headers[name]) for name in headers
        ])),
        "body: \n{!s}".format(body),
    ])


def call_ac2(protocol, host, apicall, method, params, login=None, password=None,
             show_output=True, dry_run=False):
    as_admin = True if apicall.startswith('/admin/') else False
    api = httplib2.Http(disable_ssl_certificate_validation=True)
    url = "{!s}://{!s}/v2{!s}".format(protocol, host, apicall)
    if not url.endswith('/'):
        url = "{!s}/".format(url)
    headers = {'Content-type': 'application/json', }
    if login and password:
        session = _ac2_get_session(login, password, protocol, host, as_admin)
        if session is None:
            sys.exit('Unable to initiate session.')
        headers['Authorization'] = session
    body = json.dumps(params)
    if dry_run:
        return _ac2_request_summary(url, method.upper(), body, headers)
    (response, content) = api.request(
        url, method.upper(), body=body, headers=headers
    )
    try:
        content = json.loads(content)
        if show_output:
            pprint.pprint(content, indent=4)
        return content
    except ValueError:
        e("Response: {!s}".format(response), force=show_output)
        e("Content: {!s}".format(content), force=show_output)
        sys.exit('ValueError trying to decode API response content.')
        return False


def call_ms1(key, secret, protocol, host, port, apicall, params,
             show_output=True, dry_run=False):
    msa = BotrClient(
        key,
        secret,
        host=host,
        port=port,
        protocol=protocol,
        client='clack',
    )
    if dry_run:
        params['api_format'] = 'json'
        return msa.request(apicall, params, url_only=True)
    resp = msa.request(apicall, params)
    if params['api_format'] == 'py':
        if show_output:
            pprint.pprint(resp, indent=4)
        if resp['status'] == 'ok':
            return True
        else:
            return False
            e("\nCALL FAILED PLEASE CHECK OUTPUT ABOVE!")
    else:
        e("{!s}".format(resp), force=show_output, wrap=False)
        return True


def config_path():
    return os.path.join(
        click.get_app_dir(APP_NAME, force_posix=True), 'config.ini'
    )


def e(m, force=False, wrap=True):
    """
    Shorthand for the click.echo function. Also checks if output is allowed.
    """
    if not QUIET or force:
        if isinstance(m, list) and len(m) == 2:
            if wrap:
                m[1] = "\n                          "\
                    .join(textwrap.wrap(m[1], 54))
            click.echo("{!s}: {!s}".format(
                '{:<19}'.format(m[0]), m[1]))
        else:
            if wrap:
                m = textwrap.fill(m, 80)
            click.echo(m)


def list_configs(config):
    try:
        default = config.get('etc', 'default')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        default = None
    e("The following environments are available:\n")
    sections = [s for s in config.sections() if not s == 'etc']
    if sections:
        e(['  CONFIG NAME', 'API, DESCRIPTION'])
        e([
            '------------------',
            '------------------------------------------------------'
        ])
        for i, section in enumerate(sections):
            description = 'no description'
            if section == default or (default is None and i < 1):
                section_str = "+ {!s}".format(section)
            else:
                section_str = "  {!s}".format(section)
            if config.has_option(section, 'description'):
                description = config.get(section, 'description')
            api = 'ms1'
            if config.has_option(section, 'api'):
                api = config.get(section, 'api')
            e([section_str, api + ", " + description])
        e("\nThe + marks the default environment.\n")
        return True
    else:
        e(
            "\n        NO CONFIGURATIONS FOUND\n"
            "\nPlease run 'clack add' to add configurations.",
            wrap=False
        )
        return False


def p(m, default=None, wrap=True, hide_input=False):
    """
    Shorthand for click.prompt, but with textwrapping.
    """
    if wrap:
        return click.prompt(textwrap.fill(m, 80), default=default,
                            hide_input=hide_input)
    return click.prompt(m, default=default, hide_input=hide_input)


def keyring_id(section_name):
    return '{!s}{!s}'.format(KEYRING_ID, section_name)


def ask_secret():
    return user_input(
        'Enter the secret/password for to make the call',
        None,
        None,
        hide_input=True,
    )


def read_config():
    cfg_file = config_path()
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read([cfg_file])
    return config


def save_config(config):
    with open(config_path(), 'wb') as cfp:
        config.write(cfp)


def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def user_input(question, default=None, regex=None, error=None, wrap=True,
               hide_input=False):
    val = p(question, default=default, wrap=wrap, hide_input=hide_input)
    if not val and default:
        return default
    if regex is None:
        return val
    elif re.match(regex, val):
        return val
    if error is not None:
        e(error)
    return user_input(question, default, regex, error, wrap)


@click.group(
    cls=AliasedGroup,
    help="Clack is a Command Line Api Calling Kit based on Click",
    short_help="Clack is a Command Line Api Calling Kit based on Click",
    epilog="If this is your first time using clack, please run 'clack init' "
    "to initialize a config file. If you're comfortable enough you can edit "
    "this file directly. The location of the config file is:\n{!s}".format(
        config_path(),
    )
    # invoke_without_command=True,
)
@click.version_option(
    version=VERSION,
    message='Clack-%(version)s',
)
def clack():
    pass


@click.command(help="Add another environment/user combo")
def add(*args, **kwargs):
    config = read_config()
    e(
        'Answer the following questions to add a new '
        'environment/user combo'
    )
    config = edit_environment(config, *args, **kwargs)
    save_config(config)


clack.add_command(add)


@click.command(help="Make an api call")
@click.option(
    '--env', '-e',
    default="default",
    metavar="ENVIRONMENT",
    help='Choose your environment',
)
@click.option(
    '--api', '-a',
    help='Choose the api you want to make calls to',
    type=click.Choice(['ms1', 'ac2']),
    envvar='CLACK_API',
)
@click.option(
    '--key', '-k',
    help='Set a custom key for API Calls',
    metavar='KEY',
    envvar='CLACK_KEY',
)
@click.option(
    '--secret', '-s',
    help='Prompt for the secret/password',
    is_flag=True,
)
@click.option(
    '--host', '-h',
    help='Set a custom host for making API Calls',
    metavar='HOSTNAME',
    envvar='CLACK_HOST',
)
@click.option(
    '--format', '-f',
    help="Choose the format for the output. (Only works with ms1 api calls)",
    envvar='CLACK_FORMAT',
    default='py',
    type=click.Choice(['py', 'json', 'xml', 'php'])
)
@click.option(
    '--method', '-m',
    help="Choose the HTTP method for your call. "
    "(Only works with ac2 api calls)",
    envvar='CLACK_METHOD',
    default='post',
    type=click.Choice(['delete', 'get', 'post', 'put'])
)
@click.option(
    '--quiet', '-q',
    help='Make the script shut up, only ouputs result of call',
    is_flag=True,
)
@click.option(
    '--dry-run',
    help='Do all but making the actual call',
    is_flag=True,
)
@click.argument('apicall', required=True)
@click.argument('params', required=False)
def call(apicall=None, params=None, *args, **kwargs):
    global QUIET
    QUIET = kwargs.get('quiet', False)
    config = read_config()
    return _call(config, apicall, params, *args, **kwargs)

clack.add_command(call)


@click.command(help="Make a batch of api calls.")
@click.option(
    '--env', '-e',
    default="default",
    metavar="ENVIRONMENT",
    help='Choose your environment',
)
@click.option(
    '--api', '-a',
    help='Choose the api you want to make calls to',
    type=click.Choice(['ms1', 'ac2']),
    envvar='CLACK_API',
)
@click.option(
    '--key', '-k',
    help='Set a custom key for API Calls',
    metavar='KEY',
    envvar='CLACK_KEY',
)
@click.option(
    '--secret', '-s',
    help='Prompt for the secret/password',
    is_flag=True,
)
@click.option(
    '--host', '-h',
    help='Set a custom host for making API Calls',
    metavar='HOSTNAME',
    envvar='CLACK_HOST',
)
@click.option(
    '--method', '-m',
    help="Choose the HTTP method for your call. "
    "(Only works with ac2 api calls)",
    envvar='CLACK_METHOD',
    default='post',
    type=click.Choice(['delete', 'get', 'post', 'put'])
)
@click.option(
    '--verbose', '-v',
    help="Make the output more verbose and return the complete response of "
    "each API call. By default only a success status will be returned.",
    is_flag=True,
)
@click.option(
    '--dry-run',
    help='Do all but making the actual call',
    is_flag=True,
)
@click.argument(
    'csvfile',
    required=True,
    type=click.Path()  # encoding='utf-8')
)
@click.argument('apicall', required=True)
@click.argument('params', required=True)
def batch(csvfile=None, apicall=None, params=None, *args, **kwargs):
    global QUIET
    QUIET = not kwargs.get('verbose', False)
    if kwargs.get('secret', False):
        kwargs['batch_secret'] = ask_secret()
    config = read_config()
    variables = re.findall(r'(<<(\w+)>>)', params)
    num_rows = sum(1 for line in open(csvfile, 'r')) - 1
    table = unicode_csv_reader(open(csvfile, 'r'))
    header, failed, current_row, current_row_id = [], [], 0, None

    def _current_row_id(current_item):
        return "{!s}: {!s}".format(
            ('{:<{!s}}'.format(len(str(num_rows)))).format(current_row),
            current_row_id
        )

    with click.progressbar(
        length=num_rows,
        label='Making the calls',
        item_show_func=_current_row_id
    ) as bar:
        for columns in table:
            if not header:
                header = columns
                continue
            current_row += 1
            current_row_id = columns[0]
            prms = params
            values = {}
            for i, val in enumerate(columns):
                values[header[i]] = val
            for search_for, name in variables:
                replace_with = values.get(name, False)
                if replace_with:
                    prms = prms.replace(search_for, replace_with)
            if not _call(config, apicall, prms, True, *args, **kwargs):
                failed.append("{!s}".format(current_row))
            bar.update(1)
    # Print a summary on failure:
    if failed:
        e("PLEASE NOTE:", True)
        e(
            "{!s} of the {!s} calls you made failed.".format(len(failed), num_rows),
            True
        )
        e("The following row numbers failed:\n")
        e(", ".join(failed), True)
    else:
        e("All went well! You're done now.", True)

clack.add_command(batch)


def _call(config, apicall=None, params=None, resp=False, *args, **kwargs):
    env = kwargs.get('env', 'default')

    if env == 'default':
        try:
            env = config.get('etc', 'default')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            try:
                env = config.sections()[0]
            except IndexError:
                pass

    def _get(name):
        val = kwargs.get(name, None)
        if val is not None:
            return val
        if config.has_option(env, name):
            return config.get(env, name)
        return DEFAULTS.get(name, None)

    api = _get('api')
    key = _get('key')
    host = _get('host')

    protocol = 'https'
    if host.startswith('http'):
        protocol, host = host.split('://')

    if config.has_option(env, 'secret'):
        e(
            "You still have secrets stored in your config file. Please run "
            "`clack upgrade` to move secrets from your config file to your "
            "system's password storage."
        )
        return

    if not api or not key or not host:
        e(
            "There is not enough information to make an API call."
            "Setup your configuration correctly or provide the correct "
            "command line options. Run 'clack --help' for more info. "
            "Aborting now.",
            force=True
        )
        return

    secret = kwargs.get('batch_secret', None)
    if not secret and not kwargs.get('secret', False):
        secret = keyring.get_password(keyring_id(env), key) if key else None
    if not secret:
        secret = ask_secret()

    if params is not None:
        try:
            params = ast.literal_eval(params)
        except:
            e('We failed interpreting your params')
            e("{!s}".format(params))
            return
        if not isinstance(params, dict):
            e("Your params where malformatted. Aborting now", force=True)
            return
    else:
        params = {}

    if api == 'ms1':
        params['api_format'] = kwargs.get('format', 'py')

    e("Environment is {!s}".format(env))

    e('\n---------------------------------------------\n', wrap=False)
    e(['api', api])
    e(['key', key])
    e(['secret', len(secret) * '*'])
    e(['protocol', protocol])
    e(['host', host])
    e(['call', apicall])
    if api == 'ac2':
        method = _get('method')
        e(['method', method])
    e(['params', "{!s}".format(params)])
    e('\n---------------------------------------------\n', wrap=False)

    dry_run = kwargs.get('dry_run', False)
    verbose = kwargs.get('verbose', True)
    if api == 'ac2':
        ok = call_ac2(protocol, host, apicall, method, params, login=key,
                      password=secret, show_output=verbose,
                      dry_run=dry_run)
    else:
        ok = call_ms1(key, secret, protocol, host, _get('port'), apicall,
                      params, show_output=verbose, dry_run=dry_run)

    if kwargs.get('dry_run', False):
        e("DRY RUN ONLY.")
        e("The following request would have been made: ", force=True)
        e("{!s}".format(ok), force=True, wrap=False)
        return

    e('\n---------------------------------------------\n', wrap=False)
    e('Done.')
    if resp:
        return ok
    return


@click.command(help="Edit an existing environment/user combo")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def edit(name=None, *args, **kwargs):
    config = read_config()
    if not name:
        list_configs(config)
        name = p(
            "\nPlease give the name of the config you want to update"
        )
    if not config.has_section(name):
        e(
            'The config you selected ({!s}) does not exist. Please try again'.format(name)
        )
        return
    config = edit_environment(config, name)
    save_config(config)
    e('Config "{!s}" has been updated'.format(name))


clack.add_command(edit)


@click.command(help="Initialize your config file")
@click.option(
    '--force',
    is_flag=True,
)
def init(force, *args, **kwargs):
    e("Initializing your config file")
    path = click.get_app_dir(APP_NAME, force_posix=True)
    if os.path.exists(path):
        if force:
            try:
                shutil.rmtree(path)
            except:
                e(
                    "There already is a config and the script cannot remove "
                    "it. Please do so manually and rerun this command. You "
                    "need to delete the directory {!s}".format(path)
                )
                return
        else:
            e(
                'There already is a config. Please use the "--force" option '
                'to force a new config setup'
            )
            return
    os.mkdir(path)
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    e(
        'Please answer the following question to add your first '
        'environment/user combo'
    )
    config = edit_environment(config, *args, **kwargs)
    save_config(config)


clack.add_command(init)


@click.command("ls", help="List all available environment/user combos")
def ls():
    config = read_config()
    return list_configs(config)


clack.add_command(ls)


@click.command(
    "rm",
    help="Remove an existing environment/user combo"
)
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def remove(name=None, *args, **kwargs):
    config = read_config()
    if not name:
        if list_configs(config):
            name = p(
                "\nPlease give the name of the config you want to delete"
            )
        else:
            e(
                'In other words there are no configurations to remove. '
                'Aborting now.'
            )
            return
    if not config.has_section(name):
        e(
            'The config you selected ({!s}) does not exist. Please try again'.format(name)
        )
        return
    if click.confirm('You are about to delete "{!s}". Are you sure?'.format(name)):
        if config.has_option(name, 'key'):
            key = config.get(name, 'key')
            if keyring.get_password(keyring_id(name), key):
                keyring.delete_password(keyring_id(name), key)
        config.remove_section(name)
        save_config(config)
        e('Config "{!s}" has been successfully deleted'.format(name))
    else:
        e('Aborted')
    return


clack.add_command(remove)


@click.command(
    "set",
    help="Set the config you want to use by default"
)
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def set_default(name=None, *args, **kwargs):
    config = read_config()
    if not name:
        if list_configs(config):
            name = p(
                "\nPlease give the name of the config you want to set as "
                "default"
            )
        else:
            e('You cannot set a default configuration this way.')
            return
    if not config.has_section(name):
        e(
            'The config you selected ({!s}) does not exist. Please try again'.format(name)
        )
        return
    if not config.has_section('etc'):
        config.add_section('etc')
    config.set('etc', 'default', name)
    save_config(config)
    e('Config "{!s}" has been set as the default config'.format(name))

clack.add_command(set_default)


@click.command(
    "delegate",
    help="Create a deferred login link for JW Platform",
)
@click.option(
    '--host', '-h',
    help='Set a custom host for making API Calls',
    metavar='HOSTNAME',
    envvar='CLACK_HOST',
    default='dashboard.jwplatform.com',
)
@click.argument(
    "key",
    metavar='KEY',
    required=True,
    # help="The API key for this user",
)
@click.argument(
    "secret",
    metavar='SECRET',
    required=True,
    # help="The API secret for this user",
)
@click.argument(
    "duration",
    metavar='SECS',
    required=False,
    # help="The the validity of the key in seconds.",
    type=click.INT,
    default=300,
)
def delegate(key, secret, duration, host):
    """
        This function creates a delegate login url to
        automatically log users into the platform dashboard.
    """
    timestamp = calendar.timegm(time.gmtime()) + duration
    query_string = "account_key={!s}&auth_key={!s}".format(key, key)

    timestamp_query = "&timestamp={!s}".format(timestamp)
    signature = hashlib.sha1(query_string + timestamp_query + secret)\
        .hexdigest()

    query_string += "&signature={!s}".format(signature)
    query_string += timestamp_query

    e("http://{!s}{!s}?{!s}".format(host, DELEGATE_LOGIN_URL, query_string))

clack.add_command(delegate)


# Upgrade command.
@click.command(
    help="Upgrade your config file to the latest version.",
)
def upgrade(*args, **kwargs):
    config = read_config()
    upgraded = False
    try:
        version = config.get('etc', 'version')
    except ConfigParser.NoSectionError:
        config.add_section('etc')
        version = '0.0.1'
    except ConfigParser.NoOptionError:
        version = '0.0.1'

    if StrictVersion(version) < StrictVersion('0.4.0'):
        e('Moving secrets/passwords from config file to keyring for:')
        sections = [s for s in config.sections() if not s == 'etc']
        for section in sections:
            key, secret = None, None
            if config.has_option(section, 'key'):
                key = config.get(section, 'key')
            if config.has_option(section, 'secret'):
                secret = config.get(section, 'secret')
            if key and secret:
                keyring.set_password(keyring_id(section), key, secret)
                config.remove_option(section, 'secret')
                e('- {!s}'.format(section))
        upgraded = True

    if StrictVersion(version) < StrictVersion('0.5.0'):
        e('Removing ac1 configurations because that API no longer exists')
        for section in sections:
            api, key = None, None
            if config.has_option(section, 'api'):
                key = config.get(section, 'api')
            if not api == 'ac1':
                continue
            if config.has_option(section, 'key'):
                key = config.get(section, 'key')
            config.remove_section(section)
            if key:
                keyring.remove_password(keyring_id(section), key)
            e('- Removed: {!s}'.format(section))
        upgraded = True

    config.set('etc', 'version', VERSION)
    save_config(config)
    if upgraded:
        e('Upgrade completed.')
    else:
        e('Nothing to upgrade.')

clack.add_command(upgrade)
