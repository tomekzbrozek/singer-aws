# singer-aws

CLI tool for easy execution of Singer Taps, managing module dependencies and persistence of state files and config files in AWS.

# ToDo:
* package the whole project as Docker image
* create infrastructure: S3 buckets, SSM parameter store items (manually), `SingerTap` IAM role tied to S3 bucket and allowed to access Redshift
* store logs in logs/ folder

# install singer-aws module

Currently this module can be installed only by running `pip install .` at the root of the project, locally.

# Add new tap (or target) integration

1. Add item to the list in `singer_project_config.yml`. You may give that item a custom name (different from tap module name), just remember to add `module: ...` parameter with the valid name of a tap. This can be useful e.g. if you want to maintain two tap integrations based on the same tap library (e.g. one integration tied to release `0.9.1` and the other tied to `1.0.0`), you would assign two different aliases.
2. add folder in `./taps/...` with name corresponding to tap alias
3. add a file with all modules needed to tap installation, by creating `./taps/tap-alias/requirements.txt` file
4. create virtual environment for the tap by running: `singer-aws-install`
5. if you want to store tap config in the project folder, add config.json to `.taps/tap-alias/config.json`. Otherwise make sure that tap configuration is available as environment variable or AWS Parameter Store. Check [Tap and target config files](#Tap-and-target-config-files) section.

Same steps can be performed for adding target integration, just replace `tap` with `target` when following the instructions.

# Tap and target config files

The order of proceeding when preparing singer config file (applies to both tap and target):

1. Use `config.json` file found in `taps/tap-alias/` (`targets/target-name/`) directory
2. Create `config.json` file based on `TAP_TAPNAME_CONFIG` or `TARGET_TARGETNAME_CONFIG` env variables
3. Create `config.json` file based on SSM parameter with a path like `/ssm_prefix/TAP_TAPNAME_CONFIG` or `/ssm_prefix/TARGET_TARGETNAME_CONFIG`. Value of ssm_prefix is configurable from singer_project_config.yml file, e.g. `/acme_singer_project/`

# Schema discovery

1. in the command line, export AWS_PROFILE that has permissions to read from SSM and read/write to S3:
```
export AWS_PROFILE=your_profile
```

2. run
```
singer-aws-discover --tap adwords
```

## Inspecting singer catalogs for subsequent discoveries

Subsequent schema discoveries, e.g. updates or selecting new fields for replication may be annoying because the `schema-discovery` utility (see credits below) only shows what's available, without showing what's already selected (i.e. you kind of start catalog selection form the scratch with each discovery). To allow for more seamless workflow, there's a `singer-aws-inspect` command that can be used to inspect current state of catalog of a given tap. For instance:

```
singer-aws-inspect --tap adwords
```

would print:

```
...
inspecting stream: ads...
    ❌ stream is NOT SELECTED
    • found 6 available properties
    • found 0 selected properties
    • selected properties: []
inspecting stream: accounts...
    ❌ stream is NOT SELECTED
    • found 6 available properties
    • found 0 selected properties
    • selected properties: []
inspecting stream: KEYWORDS_PERFORMANCE_REPORT...
    ✅ stream is SELECTED
    • found 139 available properties
    • found 12 selected properties
    • selected properties: ['account', 'campaignID', 'campaign', 'clicks', 'conversions', 'cost', 'keyword', 'day', 'device', 'customerID', 'keywordID', 'impressions']
...
```

## Credits

`singer-aws-discover` command leverages an amazing utility: [singer-discover](https://github.com/chrisgoddard/singer-discover). Thank you @chrisgoddard!


# Running tap | target

1. in the command line, export AWS_PROFILE that has permissions to read from SSM and read/write to S3:
```
export AWS_PROFILE=your_profile
```

2. run

```
export AWS_PROFILE=your_profile_name
singer-aws-sync --tap adwords --target redshift
```

which will run a command identical to:

```
venv/tap-adwords/bin/tap-adwords --config taps/tap-adwords/config.json | venv/target-redshift/bin/target-redshift --config targets/target-redshift/config.json > state.json
```

or, if there is any state file existing for a given tap (state file must exist in a remote S3 bucket), the following command will be executed:

```
venv/tap-adwords/bin/tap-adwords --config taps/tap-adwords/config.json --properties taps/tap-adwords/catalog.json --state states_in/tap-adwords-state.json | venv/target-redshift/bin/target-redshift --config targets/target-redshift/config.json > /Users/tomaszzbrozek/singer-aws/states_out/tap-adwords-state.json
```

:point_up: state file (in `states_in/` directory) is fetched on the fly before executing the `tap | target`. Specify S3 bucket name and prefix in the `states_bucket` parameter inside `singer_project_config.yml` file.

You can pass `--ignore-state` to ignore previous state files when executing the tap and use `start_date` as specified in tap's config to replicate all streams:

```
singer-aws-sync --tap adwords --target redshift --ignore-state
```


# What this project is not intended for

* this project will not create schemas in your target data warehouse. You still need to do it as you would need when working with singer tap directly.
