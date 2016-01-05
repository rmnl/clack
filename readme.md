# CLACK

Clack is a Command Line API Calling Kit based on [Click][1].

Clack works with the following API's

- [JW Platform API](http://apidocs.jwplayer.com/)¹
- [JW Player](http://www.jwplayer.com) Account API v1²
- [JW Player](http://www.jwplayer.com) Account API v2²


¹: The JW Platform API can be _accessed by all JW Platform users and resellers_and JW Player users with valid API credentials.

²: The JW Player Account API is at this moment __not accessible__ for customers.

[1]: http://click.pocoo.org/

## Installation

Starting with version 0.3.0 Clack supports installation through pip. This gives you a more “*pythonic*” way to install the script.  It's suggested to  install **clack** in a [virtualenv](https://virtualenv.pypa.io/en/latest/) to get a cleaner install.

``` bash
pip install clack-cli
```



## Usage

Simply run `clack` in your terminal to see more info.

### Initialization

The first time you should run `clack init` to initialize the configuration file and to add the first environment configuration. The configuration file is created in your home directory `/Users/<your_username>/.clack/config.ini`.

Clack will ask you for the following information:

2. A **name** for the environment you're trying to set up. Use a short but easy to remember name. E.g. _ms1-reseller_ for a configuration that will use the reseller account for with the JW Platform api.
   
3. The **api** type you're saving. Currently there are three options:
   
   1. `ms1`: Media Services (aka JW Platform) API version 1.
   2. `ac1`: Player Account API version 1.e
   3. `ac2`: Player Account API version 2.
   
4. The **host** of the api. E.g. _api.jwplatform.com_. Do not add slashes or a protocol.
   
5. The API **key** of the user you want to save.
   
6. The API **secret** of the user you want to save. This secret is stored in your system's password storage with [keyring](https://github.com/jaraco/keyring).
   
7. A short **description** (optional) to explain the short name you chose above. E.g. _Reseller  user on JW Platform API_


You can add or edit configurations with `clack add` or `clack edit` respectively. Removing them goes with `clack rm`.

### Manually editing the config file.

You can also manually add configurations to the config file. They look like:

``` ini
[ms1-reseller]
api = ms1
key = a1S2d3F4
host = api.jwplatform.com
description = reseller on jw platform api
```

### Calling an API.

Let's assume you have a configuration named _ms1-username_ which stores credentials for a regular user with `username` on JW Platform. To get this user's videos you would do:

``` bash
clack c /videos/list
```

Adding parameters can be done by adding a second argument as a Python dict in string.

``` bash
clack c /videos/list "{'result_limit': 10}"
```

## Switching a default configuration

By default the first configuration is the default, but a lot of times you will be making multiple calls as the same user because you are doing a specific call. Clack makes it easy to set and change the default config. Just run `clack set ms1-reseller` or `clack set` and give the configuration on the prompt.

## Short commands

You can abbreviate all the subcommands as much as you like as long as it will match one subcommand only. At this moment all subcommands begin with a different letter and this means you can use the first letter of the command only. E.g. Listing all your environments is simply `clack l`, making an API call will be `clack c`.

## Batch Calls

Clack 0.3.0 introduces the `clack batch` command which allows you to make batch calls to the api with input from a csv file. The basic usage is like this.

``` bash
clack batch /some/dir/input.csv /accounts/update "{'account_key': '<<account_key>>', 'storage_limit': '<<new_limit>>'}"
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

## Environment Variables

Clack accepts Environment variables for most parameters to the `clack call` command. This can come in handy if you e.g. want to set a different format for the Media Services API. In this case you would do:

``` bash
# Set a format for the Media Services API
export CLACK_FORMAT='json'
clack c /videos/list
```

Available Environment vars are:

- `CLACK_API`
- `CLACK_FORMAT`
- `CLACK_HOST`
- `CLACK_KEY`
- `CLACK_METHOD`
  ​
