import argparse
from datetime import datetime
import os
from singer_aws.prep_config import fetch_tap_config
from subprocess import PIPE, Popen
from singer_aws.sync import cleanup_tap
import yaml

def main():

    # 1. parse shell arguments
    parser = argparse.ArgumentParser(description='Arguments for Singer Tap execution.')
    parser.add_argument('-t', '--tap', help='Name of Singer Tap to run,', required=True)
    args = parser.parse_args()
    tap = args.tap

    singer_home = os.getcwd()

    # read singer project configuration file
    with open("singer_project_config.yml", 'r') as stream:
        try:
            project_config = yaml.safe_load(stream)

        except yaml.YAMLError as exc:
            print(f"ERROR occurred when reading singer_project_config.yml file: {exc}")

    def discover(tap, project_config):
        """
        Invoke Singer Discover shell command. Currently intended to be done only locally.
        After generating catalogs with this script, try this utility:
        https://github.com/chrisgoddard/singer-discover to mark streams/fields for
        replication in a fast & interactive way.
        """

        tap = f"tap-{tap}"
        tap_module = project_config['taps'].get(tap).get('module') or tap

        cmd = [
            os.path.join(singer_home, f"venv/{tap}/bin/{tap_module}"),
            "-c",
            os.path.join(singer_home, f"taps/{tap}/config.json"),
            "-d"
            ]

        path_catalog = os.path.join(singer_home, f"taps/{tap}/catalog.json")

        cmd_to_print = cmd + [">"] + [path_catalog]
        print(f'RUNNING: {tap} Discovery shell command:\n{" ".join(cmd_to_print)}')
        proc = Popen(cmd, stdout=PIPE)

        out, err = proc.communicate()
        with open(path_catalog, "w") as catalog_file:
            catalog_file.write(out.decode())

        if proc.returncode != 0:
            raise ValueError(f"ERROR: {tap} Singer Tap Discovery shell command failed:\n{err.decode()}")
        else:
            print(f"SUCCESS: {tap} Singer Tap Discovery shell command succeeded.")

    # 2. get parameters for the tap from AWS Parameter Store
    clean_tap_config = fetch_tap_config(tap, project_config)

    # 3. run Singer discover to generate catalog file
    discover(tap, project_config)

    # 4. cleanup temporary folders
    cleanup_tap(tap, clean_tap_config)

if __name__ == '__main__':
    main()
