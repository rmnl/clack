# -*- coding: utf-8 -*-

import click

from cmd_call import CallCommands
from cmd_settings import SettingsCommands
from environment import COMMON_SETTINGS
from environment import FIND_USERS_BY
from environment import Environment
from version import VERSION

env = Environment()


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
    "If this is your first time using clack, please run 'clack settings add' "
    "to initialize a config file and to add your first settings. "
    "If you're comfortable enough you can edit the config file directly. "
    "The location of the config file is:\n{!s}".format(
        env.config_path(),
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
    "call",
    help="Make api calls",
    epilog="Params are defined as a python dictionary e.g. \"{'test': True, 'foo': 'bar'}\"\n\n"
           "Color scheme options are: " + ", ".join(COMMON_SETTINGS['color_scheme']['options']) + "\n\n"
           "Env (settings) names are: " + ", ".join(env.sections),
)
@click.option(
    '--env', '-e',
    metavar="NAME",
    type=click.Choice(env.sections),
    help='Choose your api settings. See below for all available settings.',
    envvar="CLACK_ENV",
)
@click.option(
    '--api', '-a',
    help='*) Set the api type.',
    type=click.Choice(['ms1', 'ac2', 'adm']),
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
    type=click.Choice(['delete', 'get', 'post', 'put']),
)
@click.option(
    '--csv-file', '-c',
    help="Provide a CSV file to make a batch call. Check the README for more information. "
         "on making batch calls.",
    type=click.Path(readable=True, dir_okay=False, resolve_path=True),
    metavar="CSV_FILE",
)
@click.option(
    '--filter-response', '-f',
    help="Filter api response for a specific value. Use dotted notation for index. E.g. videos.0.key "
         "for the first key from a list of videos. You can also use videos.*.key, to get all keys for "
         "all videos in the list or use and empty string to get everything.",
    metavar="INDEX",
)
@click.option(
    '--as-user', '-u',
    help="If have ac2 admin credentials, you can find a user and makes calls as that user.",
    metavar="USER",
)
@click.option(
    '--find-user-by', '-b',
    help="What type of input did you give for the --as-user parameter. "
         "Default: email",
    metavar="FIND_BY",
    default="email",
    type=click.Choice([o for o in FIND_USERS_BY]),
)
@click.option(
    '-1', '--use-ms1',
    help="Make calls as another user and use the MS1 api through the proxy of AC2.",
    is_flag=True,
)
@click.option(
    '--output', '-o',
    help="Choose the output format",
    envvar='FORMAT',
    type=click.Choice(COMMON_SETTINGS['output']['options']),
)
@click.option(
    '--verbosity', '-v',
    help="Verbose output is the default terminal output and clack is quiet with non terminal output. "
         "Use this flag to change this default behavior.",
    metavar='TYPE',
    envvar='CLACK_VERBOSITY',
    type=click.Choice(COMMON_SETTINGS['verbosity']['options'])
)
@click.option(
    '--color-scheme', '-c',
    help="Choose the color style you want to use. Set to \"no-colors\" to disable colors. "
         "See below for all color schemes.",
    type=click.Choice(COMMON_SETTINGS['color_scheme']['options']),
    metavar="NAME",
    envvar='CLACK_COLOR_SCHEME',
)
@click.option(
    '--no-formatting',
    help="Return the response body as is. No formatting to make it more readable. Also implies --no-colors",
    is_flag=True,
    envvar="CLACK_NO_FORMATTING",
)
@click.argument('apicall', required=True)
@click.argument('params', required=False)
def call(apicall=None, params=None, *args, **kwargs):
    env.init(command="call", *args, **kwargs)
    return CallCommands(env).call(apicall, params)

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
    env.init(*args, **kwargs)
    return SettingsCommands.add(env)

settings_group.add_command(settings_add)


@click.command(
    "defaults",
    help="Set the defaults for shared settings.",
    epilog="Color scheme options are: " + ", ".join(COMMON_SETTINGS['color_scheme']['options']) + "\n\n"
           "Env names are: " + ", ".join(env.sections),
)
@click.option(
    '--color-scheme', '-c',
    help="Set your default color scheme. See below for all available color schemes.",
    metavar="NAME",
    type=click.Choice(COMMON_SETTINGS['color_scheme']['options'])
)
@click.option(
    '--env', '-e',
    help="Set your default settings. See below for all available settings.",
    metavar="NAME",
    type=click.Choice(env.sections),
)
@click.option(
    '--output', '-o',
    help="Set the default output format.",
    type=click.Choice(COMMON_SETTINGS['output']['options']),
)
@click.option(
    '--verbosity', '-v',
    help="Set the default verbosity.",
    type=click.Choice(COMMON_SETTINGS['verbosity']['options']),
)
@click.option(
    '--reset', '-r',
    help="Reset a default value.",
    type=click.Choice([key.replace('_', '-') for key in COMMON_SETTINGS.keys()]),
    multiple=True,
)
def settings_defaults(*args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.defaults(env)

settings_group.add_command(settings_defaults)


@click.command('edit', help="Edit existing API settings.")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_edit(name=None, *args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.edit(env)

settings_group.add_command(settings_edit)


@click.command("ls", help="List all API settings in the config file.")
def settings_list(*args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.list(env)

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
    env.init(*args, **kwargs)
    return SettingsCommands.remove(env, name=name)

settings_group.add_command(settings_remove)


@click.command(
    "set",
    help='Set default API settings. Short for "clack settings defaults --env CONFIG_NAME". '
         'Might be deprecated in the future.'
)
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_set(name=None, *args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.set(env, name=name)

settings_group.add_command(settings_set)


@click.command("show", help="Show API settings.")
@click.argument(
    'name',
    metavar='CONFIG_NAME',
    required=False,
)
def settings_show(name=None, *args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.show(env, name=name)

settings_group.add_command(settings_show)


@click.command("purge", help="Purge all settings and delete config file.")
def settings_purge(*args, **kwargs):
    env.init(*args, **kwargs)
    return SettingsCommands.purge()

settings_group.add_command(settings_purge)
