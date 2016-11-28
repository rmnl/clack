import click
import ConfigParser
import keyring
import os
import re
import sys

from httpie.context import Environment as SysEnv
from httpie.plugins import ColorFormatter
from httpie.plugins import JSONFormatter

VERSION = '2.0.0-beta'
APP_NAME = 'Clack'
KEYRING_ID = 'com.github.rmnl.clack.'
TAB_SIZE = 4

API_DEFAULT_HOSTS = {
    'ms1': 'api.jwplatform.com',
    'ac2': 'api.jwplayer.com',
}

STYLES = {
    'heading': {
        'fg': 'black',
        'bg': 'yellow',
        'reverse': True,
    },
    'error': {
        'fg': 'white',
        'bg': 'red',
        'reverse': False,
    }
}


class Options(object):
    """ Simple class to manage values in a dictionary as class properties.
    """

    def __init__(self, initial={}, **kwargs):
        self.options = dict(initial.items() + kwargs.items())

    def __getattr__(self, name):
        return self.get(name)

    def __setattr___(self, name, value):
        self.options[name] = value

    def dict(self):
        return self.options

    def get(self, name, default=None):
        return self.options.get(name, default)


class Environment(object):
    """ Class contains miscellaneous functions for dealing with all settings
        user in- and output.
    """

    quiet = False

    def __init__(self, *args, **kwargs):
        self.sys_env = SysEnv()
        self.options = Options(**kwargs)
        # If the output is not to a terminal
        if not self.sys_env.stdout_isatty:
            self.quiet = True
            self.options.no_colors = True
        # Set quiet based on explicit verbosity setting
        if self.options.verbosity != 'auto':
            self.quiet = True if self.options.verbosity == 'quiet' else False
        # no_formatting implies no_colors
        if self.options.no_formatting:
            self.options.no_colors = True
        self.config = ConfigParser.RawConfigParser(allow_no_value=True)
        self.config.read([Environment.config_path()])

    # Config file management

    @property
    def default(self):
        """ Returns the set of API settings that was marked as default
        """
        fallback = self.sections[0] if len(self.sections) > 0 else None
        return self.get('etc', 'default', fallback)

    @property
    def sections(self):
        """ Returns a list of sections in the config file
        """
        return [s for s in self.config.sections() if not s == 'etc']

    @staticmethod
    def config_path():
        """ Returns the path of the config file.
        """
        return os.path.join(
            click.get_app_dir(APP_NAME, force_posix=True), 'config.ini'
        )

    def get(self, section, key, fallback=None):
        """ Get a value in the config file for `key` in `section` with
            `fallback` value if the `key` cannot be found.
        """
        if self.config.has_section(section) and self.config.has_option(section, key):
            return self.config.get(section, key)
        return fallback

    def save(self):
        """ Save the config file
        """
        with open(Environment.config_path(), 'wb') as cfp:
            self.config.write(cfp)

    def check(self):
        """ Check if the config file exists and create it if it doesn't
        """
        path = click.get_app_dir(APP_NAME, force_posix=True)
        if os.path.exists(path) and os.access(path, os.W_OK):
            return None
        elif os.path.exists(path):
            return self.abort(
                'Clack must be able to write to directory {!s}, if you want to use a config file.'.format(path)
            )
        # Check if the homedir is writable.
        if not os.access(os.path.dirname(path), os.W_OK):
            return self.abort(
                'Clack wants to create the directory {!s}. This directory is used to store the config file. '
                'You can also create it yourself.'.format(path)
            )
        # Create the directory.
        self.echo(
            "Creating clack's config directory: {!s} ".format(path)
        )
        os.mkdir(path)
        return None

    def set_default(self, name):
        """ Set the settings with name `name` as the default settings.
        """
        if not self.config.has_section('etc'):
            self.config.add_section('etc')
        self.config.set('etc', 'default', name)
        self.save()

    # Keyring management

    def _keyring_id(self, section_name):
        """ Returns the keyring id for a section/set of settings
        """
        return '{!s}{!s}'.format(KEYRING_ID, section_name)

    def get_secret(self, name, key):
        """ Get the secret for section `name` and key `key` from the user's keyring
        """
        return keyring.get_password('{!s}{!s}'.format(KEYRING_ID, name), key)

    def set_secret(self, name, key, secret):
        """ Set the secret for section `name` and key `key` in the user's keyring
        """
        keyring.set_password('{!s}{!s}'.format(KEYRING_ID, name), key, secret)

    def delete_secret(self, name, key, fail_silent=False):
        """ Delete the secret for section `name` and key `key` from the user's keyring
        """
        try:
            keyring.delete_password('{!s}{!s}'.format(KEYRING_ID, name), key)
        except keyring.errors.PasswordDeleteError as e:
            if not fail_silent:
                raise e

    # Terminal output

    def abort(self, msg, error=True):
        if error:
            self.echo("Error:", style='error', force=True)
        self.echo(msg, force=True)
        self.echo('Aborting.', force=True)
        sys.exit(1)

    def echo(self, msg, force=False, style=None, *args, **kwargs):
        """ Outputs a message `msg` to the the stdout
        """
        if self.quiet is True and not force:
            return
        # Stringify the message
        if isinstance(msg, list):
            for line in msg:
                self.echo(line, force=force, *args, **kwargs)
        else:
            if style is not None and STYLES.get(style) is not None:
                terminal_width, terminal_height = click.get_terminal_size()
                msg = ("{:<" + str(terminal_width) + "}").format(msg)
                msg = self.style(msg, fg=STYLES[style]['fg'], bg=STYLES[style]['bg'],
                                 reverse=STYLES[style]['reverse'])
            if not isinstance(msg, basestring):
                msg = "{!s}".format(msg)
            click.echo(msg, *args, **kwargs)

    def style(self, text, *args, **kwargs):
        """ Returns click.style function if colors are allowed.
        """
        return text if self.options.no_colors else click.style(text, *args, **kwargs)

    def create_table(self, columns, headers=None, max_width=80, div=":"):
        """ Create a table of key and value pairs based on a list of tuples or a
            dictionary
        """
        # determine max_length
        columns = [(k, columns[k]) for k in columns] if isinstance(columns, dict) else columns
        max_length = len(headers[0]) if headers is not None else 2
        for left, right in columns:
            max_length = len(left) if len(left) > max_length else max_length
        if headers is not None:
            columns.insert(0, (max_length * "-", (max_width - max_length - len(div) - 2) * "-"))
            columns.insert(0, headers)
        lines = ["", ]
        for left, right in columns:
            right = "********" if left == 'secret' else right
            lines.append(("{:<" + str(max_length + 1) + "}{!s} {!s}").format(left, div, right))
        lines.append("")
        return lines

    def prettify_json(self, data, mime="application/json"):
        """ Format the JSON so it's pretty readable
        """
        if self.options.no_formatting:
            return data
        jf = JSONFormatter(explicit_json=False)
        return jf.format_body(body=data, mime=mime)

    def colorize(self, data, mime="application/json", color_scheme="solarized"):
        """ Give the terminal output some nice colors
        """
        if self.options.no_colors:
            return data
        cf = ColorFormatter(env=self.sys_env, color_scheme=color_scheme)
        if isinstance(data, list):
            return [cf.format_headers(line) for line in data]
        else:
            return cf.format_body(data, mime)

    # User input

    def input(self, question, *args, **kwargs):
        """ Ask for user input
        """
        question = question if isinstance(question, basestring) else "{!s}".format(question)
        return click.prompt(question, *args, **kwargs)

    def validated_input(self, question, regex=None, options=None, error_msg=None, *args, **kwargs):
        """ Ask for user input and validate the input agains regular expression `regex`.
            Display error `error_msg if the regex does not match.
        """
        if options is not None and isinstance(options, list):
            options = [str(o) for o in options]
            question = "{!s}\n[{!s}]".format(question, "|".join(options))
        val = self.input(question, *args, **kwargs)
        if not val and kwargs.get('default'):
            return kwargs['default']
        if regex is None and options is None:
            return val
        elif options and isinstance(options, list) and val in options:
            return val
        elif regex and re.match(regex, val):
            return val
        if error_msg is not None:
            self.echo(error_msg)
        return self.validated_input(question, regex=regex, error_msg=error_msg, *args, **kwargs)

    # Settings commands

    def edit(self, update_for_name=None, *args, **kwargs):
        """ Edit a batch of settings.
            Invoked by: clack settings edit
        """
        if update_for_name is None:
            name = self.validated_input(
                "You should give a recognizable name for the api settings you're about to add. "
                "e.g. ms1-reseller for making calls as a reseller to the media services api",
                default=None,
                regex=r'^(?!etc)[a-zA-Z0-9-_]{1,16}$',
                error_msg="A name for a set of settings can only contain alphanumeric (and _ -) characters "
                          "and should be between 1 and 16 characters long (The name \"etc\" is not allowed).",
            )
            api = self.validated_input(
                "What type of API is this?\n"
                "- ms1 : media services api (aka botr, jwplatform)\n"
                "- ac2 : account api version 2 (as used by unified dashboard)\n",
                default=None,
                options=['ms1', 'ac2'],
                error_msg='Please choose a valid option and try again',
            )
            host = API_DEFAULT_HOSTS[api]
            key = None
            description = None
        else:
            name = update_for_name
            api = self.get(name, 'api')
            host = self.get(name, 'host', API_DEFAULT_HOSTS[api])
            key = self.get(name, 'key')
            description = self.get(name, 'description')
        host = self.validated_input(
            "What's the hostname for this api?",
            default=host,
            regex=r'^(http[s]{0,1}:\/\/)*[a-zA-Z0-9-.]+\.(jwplatform|jwplayer|longtailvideo|ltv)\.(com|dev)$',
            error_msg="The hostname is not correct, please try again",
        )
        verify_ssl = 'yes'
        if host.startswith('https://') and not click.confirm(
            'You have defined a https host. Do you wish to verify the SSL certificates'
        ):
            verify_ssl = 'no'
        if api == 'ac2':
            key = self.validated_input("What's the login/email for the user?", default=key)
            secret = self.validated_input(
                "What's the password? Please note that the password is stored in your system's keyring. "
                "You can also leave it empty and you will be prompted for your password with each api call",
                default="",
                hide_input=True,
            )
            is_admin = 'no'
            if key.find('@') < 0 and click.confirm(
                'Did you just enter credentials for making admin calls to the account api?'
            ):
                is_admin = 'yes'
        else:
            key = self.validated_input(
                "What's the API key for this user",
                default=key,
                regex=r'^[a-zA-Z0-9]{8,}$',
                error_msg="A API is alphanumeric and at least 8 characters long. "
                          "Please try again",
            )
            secret = self.validated_input(
                "What's API secret for this user? Please note that the secret is stored in your system's keyring. "
                "You can also leave this empty and you will be prompted for your secret with each api call.",
                default="",
                regex=r'^[a-zA-Z0-9]{20,}$|^$',
                error_msg="A API is alphanumeric and at least 20 characters long. "
                          "Please try again",
                hide_input=True,
            )
        description = self.validated_input(
            "You can add a description to make it easier to identify this set of api settings.",
            default=description,
        )
        if name and host and key and update_for_name is None:
            self.config.add_section(name)
        if name and host and key:
            self.config.set(name, 'key', key)
            self.config.set(name, 'host', host)
            self.config.set(name, 'description', description)
            self.config.set(name, 'api', api)
            self.config.set(name, 'verify_ssl', verify_ssl)
            if api == 'ac2':
                self.config.set(name, 'is_admin', is_admin)
        if name and key and secret:
            self.set_secret(name, key, secret)
        elif name and key and self.get_secret(name, key):
            self.delete_secret(name, key)
        if len(self.sections) <= 1 or click.confirm('Do you want to make these settings the default settings?'):
            self.set_default(name)

    def list(self):
        """ List all sets op API settings.
            Invoked by: clack settings list
        """
        if self.sections:
            headers = ('CONFIG NAME', 'API, DESCRIPTION')
            sections, columns = sorted(self.sections), []
            for i, section in enumerate(sections):
                marker = "+" if self.default == section else " "
                left = "{!s} {!s}".format(marker, section)
                sections[i] = left
                description = self.get(section, 'description', 'no description')
                api = api = self.get(section, 'api', 'ms1')
                right = "{!s}, {!s}".format(api, description)
                columns.append((left, right))
            self.echo("The following API settings are available:")
            table = self.create_table(columns, headers=headers)
            self.echo(table[:3] + self.colorize(table[3:]))
            self.echo("+ marks the default environment.")
            self.echo("")
        else:
            self.echo('No saved settings found, please run "clack settings add" to add settings.')

    def api_settings(self, name, secret=True):
        """ Show a specific set of settings.
            Invoked by: clack settings show
        """
        keys = ['description', 'api', 'host', 'key']
        columns = [(key, self.get(name, key)) for key in keys]
        # secret is a special case.
        columns.append((
            'secret',
            8 * '*' if secret or self.get_secret(name, self.get(name, 'secret')) else 'Input at runtime.',
        ))
        self.echo(self.create_table(columns))
