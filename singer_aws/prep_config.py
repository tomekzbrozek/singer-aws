import boto3
import json
import logging
import os
import yaml

# LOGGER = logging.getLogger('singer_logger')
# logging.setLevel(getattr(logging, 'INFO'))
logging.basicConfig(level = logging.INFO)

"""
The order of proceeding when preparing singer config file (applies to both tap and target):

1. Use config.json file found in taps/tap-name/ (targets/target-name/)
    directory
2. Create config.json file based on `TAP_TAPNAME_CONFIG` or
    `TARGET_TARGETNAME_CONFIG` env variables
3. Create config.json file based on SSM parameter with a path like
    `/ssm_prefix/TAP_TAPNAME_CONFIG` or `/ssm_prefix/TARGET_TARGETNAME_CONFIG`.
    Value of ssm_prefix is configurable from singer_project_config.yml file, e.g.
    `/acme_singer_project/`
"""

def fetch_tap_config(tap, project_config):
    """
    Fetches credentials of all Singer Taps from AWS Parameter Store.
    """

    ssm_prefix = project_config.get('ssm_prefix')
    tap_name_upper = tap.upper()
    tap_name_upper_env_var = tap.upper().replace('-', '_')
    tap_name_lower = tap.lower()
    tap_config_path = f"taps/tap-{tap_name_lower}/config.json"

    if os.path.exists(tap_config_path):
        clean_tap_config = False # if tap config was already there and not created by singer-aws, keep it
        logging.info(f"using existing config file for tap-{tap}.")

    elif os.getenv(f"TAP_{tap_name_upper_env_var}_CONFIG") is not None:

        tap_config = os.getenv(f"TAP_{tap_name_upper_env_var}_CONFIG")
        tap_config_json = json.loads(tap_config)
        clean_tap_config = True
        logging.info(f"config for tap-{tap} fetched successfully from local environment variables.")

    else:

        ssm = boto3.client('ssm')
        # paginator = ssm.get_paginator('get_parameters_by_path')

        # for params in paginator.paginate(Path=ssm_prefix, WithDecryption=True):
        #     for elem in params.get('Parameters'):
        #         if f"TAP_{tap_name_upper_env_var}_CONFIG" in elem.get('Name'):
        #             tap_config = json.loads(elem.get('Value'))
        #             clean_tap_config = True
        #             print(f"config for tap-{tap} fetched successfully from SSM.")
        #         else:
        #             print(f"ERROR: config for tap-{tap} not provided as file, env var or SSM parameter.")

        try:
            elem = ssm.get_parameter(Name=f"{ssm_prefix}/TAP_{tap_name_upper_env_var}_CONFIG", WithDecryption=True)['Parameter']
            tap_config_json = json.loads(elem.get('Value'))
            clean_tap_config = True
            logging.info(f"config for tap-{tap} fetched successfully from SSM.")
        except:
            logging.error(f"ERROR: config for tap-{tap} not provided as file, env var or SSM parameter.")

    with open(tap_config_path,'w') as fh:
        fh.write(json.dumps(tap_config_json))
        logging.info(f"SUCCESS: tap-{tap_name_lower} parameters have been fetched.")

    return(clean_tap_config)

def fetch_target_config(target, project_config, tap=None, s3_key_prefix=None):
    """
    Fetches Redshift Singer Target credentials from AWS Parameter Store.
    Can be extended with more targets (e.g. CSV, BigQuery) in the future.
    """

    ssm_prefix = project_config.get('ssm_prefix')
    target_name_upper = target.upper()
    target_name_upper_env_var = target.upper().replace('-', '_')
    target_name_lower = target.lower()
    target_config_path = f"targets/target-{target_name_lower}/config.json"

    target_module = project_config['targets'].get(f"target-{target}").get('module_name') or f"target-{target}"

    if os.path.exists(target_config_path):

        with open(target_config_path) as target_config:
            target_config_json = json.load(target_config)

        clean_target_config = False # if target config was already there and not created by singer-aws, keep it
        logging.info(f"using existing config file for target-{target}.")

    elif target_module in ['target-redshift']:

        target_config = os.getenv(f"TARGET_{target_name_upper_env_var}_CONFIG")
        target_config_json = json.loads(target_config)
        clean_target_config = True
        logging.info(f"config for target-{target} fetched successfully from local environment variables.")

    else:

        ssm = boto3.client('ssm')
        paginator = ssm.get_paginator('get_parameters_by_path')

        for params in paginator.paginate(Path=ssm_prefix, WithDecryption=True):
            for elem in params.get('Parameters'):
                if f"TARGET_{target_name_upper_env_var}_CONFIG" in elem.get('Name'):
                    target_config_json = json.loads(elem.get('Value'))
                    clean_target_config = True
                    logging.info(f"config for target-{target} fetched successfully from SSM.")
                else:
                    logging.error(f"ERROR: config for target-{target} not provided as file, env var or SSM parameter.")

    try:
        tap_schema = project_config['taps'].get(f"tap-{tap}")['schema']
    except:
        logging.error(f"ERROR: no schema parameter for processed tap: tap-{tap} (required to prep config.json of a target-{target})")

    target_config_json['redshift_schema'] = tap_schema
    target_config_json['target_s3']['key_prefix'] = s3_key_prefix

    with open(f"targets/target-{target_name_lower}/config.json",'w') as fh:
        fh.write(json.dumps(target_config_json))
        logging.info(f"SUCCESS: target-{target_name_lower} parameters have been fetched.")

    return(clean_target_config)
