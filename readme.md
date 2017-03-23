# CLACK

Clack is a Command Line API Calling Kit based on [Click][1].

Clack works with the following API's

- `ms1`: [JW Platform API](http://apidocs.jwplayer.com/)¹
- `ac2`: [JW Player](http://www.jwplayer.com) Account API v2²
- `adm`: [JW Player](http://www.jwplayer.com) Account API v2 Admin endpoints²


¹: The JW Platform API can be _accessed by all JW Platform users and resellers_and JW Player users with valid API credentials.

²: The JW Player Account API is at this moment __not accessible__ for customers.

[1]: http://click.pocoo.org/

## What's new:

Clack Version 2 brings some new features:

- Colored terminal output using [pygments](http://pygments.org/).
- [Filter response output](https://github.com/rmnl/clack#filter-response-output) in regular and batch calls.
- Admin enabled users can [make calls as another user](https://github.com/rmnl/clack#make-calls-as-another-user).
- Different way to [manage settings](https://github.com/rmnl/clack#managing-api-settings) with [default call settings](https://github.com/rmnl/clack#managing-api-settings).
- Use of [jwplatform](https://pypi.python.org/pypi/jwplatform) module and the excellent [requests](https://pypi.python.org/pypi/requests) module.
- Complete rewrite.

## Installation

Starting with version 0.3.0 Clack supports installation through pip. This gives you a more “*pythonic*” way to install the script.  It's suggested to  install **clack** in a [virtualenv](https://virtualenv.pypa.io/en/latest/) to get a cleaner install.

``` bash
pip install --upgrade clack-cli
```

Please note for pre-releases you must specify the exact version. E.g.:

```bash
pip install --upgrade clack-cli==2.0.0b9
```


## Usage

Simply run `clack` in your terminal to see more info.

### Managing API settings

Clack can manage different API settings. It stores settings inside a config file and passwords/secrets inside your OS's keyring/keychain. Use of the config file is not necessary but it makes calling the API's easier, because otherwise you'll have to provide all details with each call. If you want to use the config file, you should start with `clack settings add`.

The configuration file is created in your home directory `/Users/<your_username>/.clack/config.ini`.

#### Available settings commands:

- `clack settings add`: Add new API settings to the config file/keyring.
- `clack settings defaults`: Show and set defaults for generic call settings.
- `clack settings edit`: Edit and change existing API settings.
- `clack settings ls`: List all saved settings.
- `clack settings show`: Show specific settings (secret is not shown)
- `clack settings set`: Shorthand for `clack settings defaults --env`. Might be deprecated.
- `clack settings rm`: Remove settings from the config file.
- `clack settings purge`: Purge all settings and delete the configuration file and directory.

PS. You can see all these options by running `clack settings --help`

#### Adding or editing settings

Clack will ask you for the following information when you add or edit a setting:

1. A **name** for the environment you're trying to set up. Use a short but easy to remember name. E.g. _ms1-reseller_ for a configuration that will use the reseller account for with the JW Platform api.
2. The **api** type you're saving. Currently there are three options:

   1. `ms1`: Media Services (aka JW Platform) API version 1.
   2. `ac2`: Player Account API version 2.
3. The **host** of the api. E.g. _api.jwplatform.com_. You can add `https://` or `http://` to force a protocol.
4. The API **key** of the user you want to save.
5. The API **secret** of the user you want to save. This secret is stored in your system's password storage with [keyring](https://github.com/jaraco/keyring).
6. A short **description** (optional) to explain the short name you chose above. E.g. _Reseller  user on JW Platform API_
7. Clack wil finally ask you if you want to set the added/edited settings as the default settings.

#### Manually editing the config file.

If you feel comfortable enough you can also manually add configurations to the config file. :

``` ini
[ms1-reseller]
api = ms1
key = a1S2d3F4
host = api.jwplatform.com
description = reseller on jw platform api
```



## Calling the API.

Assuming that you already added settings for the _ms1_ API to the config file call and marked those settings as the default, all you need to do is:

``` bash
clack call /videos/list
```

Adding parameters can be done by adding a second argument as a Python dict in string.

``` bash
clack call /videos/list "{'result_limit': 10}"
```

If you want to use different settings from the config file you can use the `--env` flag.

```bash
clack call --env ms1-different /videos/list "{'result_limit': 10}"
```

If you don't want to used stored settings you can specify all of them with flags.

```bash
clack call --api ms1 --host api.jwplatform.com --key 1q2w3e4r --secret /videos/list "{'result_limit': 10}"
```



### Batch Calls

Clack 0.3.0 introduced a _batch_ command which allows you to make batch calls to the api with input from a csv file. The basic usage is like this.

``` bash
clack call --csv-file /some/dir/input.csv /accounts/update "{'account_key': '<<account_key>>', 'storage_limit': '<<new_limit>>'}"
```

With this command the csv file would have content like this:

| account_key | new_limit | unused_column |
| ----------- | --------- | ------------- |
| qweRTY      | 1000000   | foo           |
| ASDfgh      | 5000000   | bar           |

This means the csv file **must have a header row**. The names of the columns in the header row will be used for replacing the parameter string template with values.

In the above example the `<<account_key>>` will be replaced by the value of the account_key in the row. The above csv would result in the following regular api calls with clack.

``` bash
clack call /accounts/update "{'account_key': 'qweRTY', 'storage_limit': '1000000'}"
clack call /accounts/update "{'account_key': 'ASDfgh', 'storage_limit': '5000000'}"
```

As you can see the *unused_column* is ignored.



### Filter response output

Clack v2 introduces the option to filter the output of responses you receive from the api. This is handy if you're interested in specific things. To use this filter you need to set the `--filter-response` (or `-f`) flag with a _"map"_ of the response you wish to see.  For example:

```bash
# Fetch key of the first video from the /videos/list response
clack call -e ms1-account -f "videos.0.key" /videos/list
# Or simply fetch all keys:
clack call -e ms1-account -f "videos.*.key" /videos/list
```



### Make calls as another user

Clack v2 introduces the option to make calls as another user.  You can only make calls as another user if you are authorized to use the admin endpoints of the `ac2` API.  There are three settings that need to be added to the call:

1. `--as-user` or `-u` : The _"identifier"_ for the user.
2. `--find-user-by` or `-b` : The type of _"identifier"_ you are using. Options are:
   - `email` The user's JW Player account email.
   - `license_key` : The JW Player user license.
   - `ms1_key` : The MS1 API key.
   - `analytics_token` : The token used for the analytics service.
   - `payment_id` : Does this need explaining?
   - `account_token` : The token for this account.
3. `--use-ms1` : Use the ms1 api for this user. This will be done through the ac2 proxy and has some limitation, but you should be able to do most of the things you want to do for a user.

Here is an example:

```bash
# List videos for an account.
clack call -e admin-account -u someone@example.com -b email --use-ms1 /videos/list
```



### Default call parameters

You can set defaults for the following call settings:

- `--env` / `-e`  : The default settings to use (all your settings `clack settings ls`)
- `--output` / `-o` : The default output format (`py`  or `json`)
- `--color-scheme` / `-c` : The default colorscheme ([all available pygments styles](http://pygments.org/docs/styles/#getting-a-list-of-available-styles))
- `--verbosity` / `-v` : The verbosity of the script. Default is `auto` which will be verbose when outputting to the terminal, and quiet when outputting to a file. Set to `quiet` to always be quiet and to `verbose` to always be verbose.

An example:

```bash
# "Resetting" the default settings:
clack settings defaults \
	--env your-settings \
	--output json \
	--color-scheme monokai \
	--verbosity auto
```



## Environment Variables

Clack accepts Environment variables for most parameters to the `clack call` command. This can come in handy if you e.g. want to set a different format for the Media Services API. In this case you would do:

``` bash
# Set a format for the Media Services API
export CLACK_KEY='1q2w3e4r'
clack call /videos/list
```

Available Environment vars are:

- `CLACK_ENV`
- `CLACK_API`
- `CLACK_HOST`
- `CLACK_KEY`
- `CLACK_METHOD`
- `CLACK_OUTPUT`
- `CLACK_COLOR_SCHEME`
- `CLACK_VERBOSITY`
- `CLACK_NO_FORMATTING`

