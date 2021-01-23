#!/usr/bin/env python
import os
import subprocess
import yaml

def main():

    def install_venv(type, alias, module, env_vars):

        name = alias or module
        env_vars = env_vars or {}

        print(f"Installing virtual environment for {name}...")

        pip = os.path.join(f"venv/{name}/bin", "pip")

        commands = [
            ["rm", "-rf", f"venv/{name}"],
            ["python3", "-m", "venv", f"venv/{name}"],
            [pip, "install", "-U", "pip"],
            [pip, "install", "--no-cache-dir", "-r", f"{type}s/{name}/requirements.txt"]
        ]

        my_env = os.environ.copy()
        for key, value in env_vars.items():
            my_env[key] = value

        for cmd in commands:
            print(" ".join(cmd))
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env = my_env)
            out, err = process.communicate()
            print(out.decode(), err.decode())


    with open("singer_project_config.yml", 'r') as stream:
        try:
            project_config = yaml.safe_load(stream)

            for tap, config in project_config['taps'].items():
                install_venv('tap', tap, config.get('module'), config.get('env_vars'))

            for target, config in project_config['targets'].items():
                install_venv('target', target, config.get('module'), config.get('env_vars'))

        except yaml.YAMLError as exc:
            print(exc)

if __name__ == '__main__':
    main()
