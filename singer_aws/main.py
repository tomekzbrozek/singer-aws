import argparse
from datetime import datetime
import os
from singer_aws.prep_config import fetch_tap_config, fetch_target_config
from singer_aws.sync import sync, send_state, cleanup_tap, cleanup_target
from subprocess import PIPE, run
import yaml

def main():

    # 1. parse shell arguments
    parser = argparse.ArgumentParser(description='Arguments for Singer Tap execution.')
    parser.add_argument('--tap', help='Name of Singer Tap to run,', required=True)
    parser.add_argument('--target', help='Name of Singer Tap target to run into.', required=True)
    parser.add_argument('--ignore-state',  action='store_true', help='If passed, this flag makes \
        singer tap execution ignore the state file, starting replication from the start_date (== epoch) \
        as defined in config file.')
    args = parser.parse_args()

    # read singer project configuration file
    with open("singer_project_config.yml", 'r') as stream:
        try:
            project_config = yaml.safe_load(stream)

        except yaml.YAMLError as exc:
            print(f"ERROR occurred when reading singer_project_config.yml file: {exc}")

    tap = args.tap
    target = args.target
    aws_profile = project_config.get('redshift_aws_profile')
    ignore_state = args.ignore_state

    # 2. get tap config from env variable or AWS Parameter Store
    clean_tap_config = fetch_tap_config(tap, project_config)

    # 3. get target parameters from AWS Parameter Store, enrich with arg input
    # current day, month, year to construct S3 prefix
    d = str('{:02d}'.format(datetime.now().day))
    m = str('{:02d}'.format(datetime.now().month))
    y = str('{:04d}'.format(datetime.now().year))
    s3_key_prefix = f"singer/{args.tap}/{y}/{m}/{d}/"
    clean_target_config = fetch_target_config(target, project_config, tap, s3_key_prefix)

    # 4. sync Singer Tap (runs the "venv/tap | venv/target" command)
    bucket = project_config.get('data_bucket')
    sync(tap, target, project_config, bucket, ignore_state, aws_profile)

    # 5. cleanup temporary folders
    cleanup_tap(tap, clean_tap_config)
    cleanup_target(target, clean_target_config)

if __name__ == '__main__':
    main()
