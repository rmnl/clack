# -*- coding: utf-8 -*-

import click

from environment import Environment
from environment import OUTPUT_OPTIONS
from environment import VERSION
from cmd_call import CallCommands
from cmd_settings import SettingsCommands
from pygments.styles import STYLE_MAP


# Aliased Group Class #########################################################

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


# CLACK - Main group ##########################################################

@click.group(
    cls=AliasedGroup,
    help="Clack is a Command Line Api Calling Kit based on Click",
    short_help="Clack is a Command Line Api Calling Kit based on Click",
    epilog="Use \"clack COMMAND --help\" for help with subcommands.\n"
    "If this is your first time using clack, please run 'clack init' "
    "to initialize a config file. If you're comfortable enough you can edit "
    "this file directly. The location of the config file is:\n{!s}".format(
        Environment.config_path(),
    )
)
@click.version_option(
    version=VERSION,
    message='Clack-%(version)s',
)
def clack():
    pass


# CLACK - Call ################################################################

@click.command(
    help="Make api calls",
    epilog="Params are defined as a python dictionary e.g. \"{'test': True, 'foo': 'bar'}\"\n\n"
           "Color scheme options are: " + ", ".join(STYLE_MAP.keys())
)
@click.option(
    '--env', '-e',
    default="default",
    metavar="ENV",
    help='Choose your api settings',
)
@click.option(
    '--api', '-a',
    help='*) Set the api type.',
    type=click.Choice(['ms1', 'ac2']),
    envvar='CLACK_API',
)
@click.option(
    '--host', '-h',
    help='*) Set a custom host for the API.',
    metavar='HOSTNAME',
    envvar='CLACK_HOST',
)
@click.option(
    '--key', '-k',
    help='*) Set the key or username for authentication.',
    metavar='KEY',
    envvar='CLACK_KEY',
)
@click.option(
    '--secret', '-s',
    help='Prompt for the secret/password',
    is_flag=True,
)
@click.option(
    '--method', '-m',
    help="Set the HTTP method/verb (only ac2). ",
    envvar='CLACK_METHOD',
    default='post',
    type=click.Choice(['delete', 'get', 'post', 'put'])
)
@click.option(
    '--csv-file', '-c',
    help="Provide a CSV file to make a batch call. Check the README for more information. "
         "on making batch calls.",
    type=click.Path(readable=True, dir_okay=False, resolve_path=True),
    metavar="CSV_FILE",
)
@click.option(
    '--output', '-o',
    help="Choose the output type",
    envvar='CLACK_OUTPUT',
    default='json',
    type=click.Choice(OUTPUT_OPTIONS),
)
@click.option(
    '--verbosity', '-v',
    help="Verbose output is the default terminal output and clack is quiet with non terminal output. "
         "Use this flag to change this default behavior.",
    metavar='TYPE',
    envvar='CLACK_VERBOSITY',
    default='auto',
    type=click.Choice(['auto', 'quiet', 'verbose'])
)
@click.option(
    '--color-scheme', '-c',
    help="Choose the color style you want to use. Set to \"no-colors\" to disable colors. "
         "The default color scheme is \"monokai\". See below for other options.",
    default='monokai',
    type=click.Choice(['no-colors', ] + STYLE_MAP.keys()),
    metavar="NAME",
    envvar='CLACK_COLOR_SCHEME',
)
@click.option(
    '--no-formatting',
    help="Return the response body as is. No formatting to make it more readable. Also implies --no-colors",
    is_flag=True,
)
@click.argument('apicall', required=True)
@click.argument('params', required=False)
def call(apicall=None, params=None, *args, **kwargs):
    env = Environment(**kwargs)
    return CallCommands.call(env, apicall, params)

clack.add_command(call)


# CLACK - Settings ############################################################

@click.group(
    'settings',
    cls=AliasedGroup,
    help="Manage API settings stored in the config file.",
    epilog="Use \"clack settings COMMAND --help\" for help with subcommands.\n"
)
def settings_group(*args, **kwargs):
    pass

clack.add_command(settings_group)


@click.command('add', help="Add new API settings.")
def settings_add(*args, **kwargs):
    return SettingsCommands.add(*args, **kwargs)

settings_group.add_command(settings_add)


@click.command("set", help="Choose the default API settings.")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_default(name=None, *args, **kwargs):
    return SettingsCommands.default(name=name, *args, **kwargs)

settings_group.add_command(settings_default)


@click.command('edit', help="Edit existing API settings.")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_edit(name=None, *args, **kwargs):
    return SettingsCommands.edit(name=name, *args, **kwargs)

settings_group.add_command(settings_edit)


@click.command("ls", help="List all API settings in the config file.")
def settings_list(*args, **kwargs):
    return SettingsCommands.list(*args, **kwargs)

settings_group.add_command(settings_list)


@click.command("rm", help="Remove API settings.")
@click.option(
    '-y', '--yes',
    help="Do not ask for confirmation, but assume yes.",
    is_flag=True,
)
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_remove(name=None, *args, **kwargs):
    return SettingsCommands.remove(name=name, *args, **kwargs)

settings_group.add_command(settings_remove)


@click.command("show", help="Show API settings.")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_show(name=None, *args, **kwargs):
    return SettingsCommands.show(name=name, *args, **kwargs)

settings_group.add_command(settings_show)


@click.command("purge", help="Purge all settings and delete config file.")
def settings_purge(*args, **kwargs):
    return SettingsCommands.purge(*args, **kwargs)

settings_group.add_command(settings_purge)
