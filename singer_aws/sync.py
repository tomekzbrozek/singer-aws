import boto3
import json
import logging
import os
import random
import shutil
import string
from subprocess import PIPE, Popen
import sys
import time
import yaml

logging.basicConfig(level = logging.INFO)

singer_home = os.getcwd()
states_in_path = os.path.join(singer_home, 'states_in')
states_out_path = os.path.join(singer_home, 'states_out')

def boto_resource(iam_role_arn):
    """
    Starts a boto resource from a IAM role
    """

    sts_client = boto3.client("sts")

    uid = "".join(random.choice(string.hexdigits) for n in range(8))
    response = sts_client.assume_role(RoleArn=iam_role_arn, RoleSessionName=f"singer_{uid}")

    credentials = response["Credentials"]
    params = {
        "aws_access_key_id": credentials["AccessKeyId"],
        "aws_secret_access_key": credentials["SecretAccessKey"],
        "aws_session_token": credentials["SessionToken"],
    }

    session = boto3.Session(**params)
    resource = session.resource('s3')

    return(resource)


def boto_client(iam_role_arn):
    """
    Starts a boto resource from a IAM role
    """

    sts_client = boto3.client("sts")

    uid = "".join(random.choice(string.hexdigits) for n in range(8))
    response = sts_client.assume_role(RoleArn=iam_role_arn, RoleSessionName=f"singer_{uid}")

    credentials = response["Credentials"]
    params = {
        "aws_access_key_id": credentials["AccessKeyId"],
        "aws_secret_access_key": credentials["SecretAccessKey"],
        "aws_session_token": credentials["SessionToken"],
    }

    session = boto3.Session(**params)
    client = session.client('s3')

    return(client)


def s3_client(project_config, aws_profile=None):
    """Create S3 client, sourced from AWS_PROFILE when run locally or from
    default session when run by Airflow."""
    if aws_profile is not None:
        session = boto3.Session(profile_name=aws_profile)
        client = session.client('s3')
    else:
        client = boto_client(project_config.get('redshift_iam_role'))
    return(client)


def s3_resource(project_config, aws_profile=None):
    """Create S3 resource, sourced from AWS_PROFILE when run locally or from
    default session when run by Airflow."""
    if aws_profile is not None:
        session = boto3.Session(profile_name=aws_profile)
        resource = session.resource('s3')
    else:
        resource = boto_resource(project_config.get('redshift_iam_role'))
    return(resource)


def get_state_filename(tap, project_config, bucket, aws_profile=None):
    """
    Get last Singer state file name for a given tap name and environment.
    """

    s3 = s3_client(project_config, aws_profile)
    prefix = f"singer/{tap}/states/"

    last_state = ''
    get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))
    paginator = s3.get_paginator("list_objects")
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    for page in page_iterator:
        if "Contents" in page:
            last_object = [obj['Key'] for obj in sorted(page["Contents"], key=get_last_modified)][-1]
            last_state = last_object if last_object != prefix else ''

    return(last_state)


def get_state(tap, project_config, bucket, aws_profile=None):
    """
    Download last Singer state file for a given tap name and environment.
    """
    s3 = s3_resource(project_config, aws_profile)
    state_filename = get_state_filename(tap, project_config, bucket, aws_profile)
    try:
        os.makedirs(states_in_path)
    except FileExistsError:
        pass

    try:
        s3.Bucket(bucket).download_file(state_filename, f"{states_in_path}/{tap}-state.json")
        logging.info(f"SUCCESS: Last state for {tap} has been fetched from s3://{bucket}/{state_filename}.")
    except:
        logging.error(f"ERROR: Last state for {tap} wasn't fetched from S3.")
        sys.exit(0)


def send_state(tap, project_config, bucket, aws_profile=None):
    """
    Upload last Singer state file to S3, for a given tap name and environment.
    """
    s3 = s3_resource(project_config, aws_profile)
    # get current timestamp in miliseconds to construct name of uploaded file
    t = str(int(time.time()*1000))
    state_filename = f"singer/{tap}/states/{t}-{tap}-state.json"

    try:
        s3.Bucket(bucket).upload_file(f"{states_out_path}/{tap}-state.json", state_filename)
        logging.info(f"SUCCESS: Last state for {tap} has been uploaded to s3://{bucket}/{state_filename}.")
    except:
        logging.error(f"ERROR: Last state for {tap} wasn't uploaded to S3.")
        sys.exit(0)


def sync(tap, target, project_config, bucket, ignore_state=False, aws_profile=None):
    """
    Invoke Singer Tap shell command.
    """

    tap = f"tap-{tap}"

    # make temporary directory for state files before they're uploaded to S3
    try:
        os.makedirs(states_out_path)
    except FileExistsError:
        pass

    catalog_arg = project_config['taps'].get(tap).get('catalog_arg')
    if catalog_arg is not None:
        catalog_arg = [catalog_arg, os.path.join(singer_home, f"taps/{tap}/catalog.json")]

    # construct state argument for tap execution, depending on existence of state file in S3
    # and presence/absence of --ignore-state flag passed to the command
    if ignore_state is True:
        # if an --ignore-state flag is passed to the executed command
        state_in_arg = None
    elif get_state_filename(tap, project_config, bucket, aws_profile) == '':
        # very first run of a tap, no previous state file found in S3
        state_in_arg = None
    else:
        # 2nd, 3rd, or next run of a tap, requiring to get state file from S3
        state_in_arg = ["--state", os.path.join(singer_home, f"states_in/{tap}-state.json")]
        # also download state file to feed to the tap
        get_state(tap, project_config, bucket, aws_profile)

    tap_module = project_config['taps'].get(tap).get('module') or tap
    target_module = project_config['targets'].get(f"target-{target}").get('module') or target

    cmd_tap = [
        os.path.join(singer_home, f"venv/{tap}/bin/{tap_module}"),
        "--config",
        os.path.join(singer_home, f"taps/{tap}/config.json")
        ]

    if catalog_arg is not None:
        cmd_tap += catalog_arg
    if state_in_arg is not None:
        cmd_tap += state_in_arg

    cmd_target = [
        os.path.join(singer_home, f"venv/target-{target}/bin/target-{target_module}"),
        "--config",
        os.path.join(singer_home, f"targets/target-{target}/config.json")
        ]

    path_state = os.path.join(singer_home, f"states_out/{tap}-state.json")

    cmd_to_print = cmd_tap + ['|'] + cmd_target + [">"] + [path_state]

    logging.info(f'RUNNING: {tap} shell command:\n{" ".join(cmd_to_print)}')
    proc_tap = Popen(cmd_tap, stdout=PIPE)
    proc_target = Popen(cmd_target, stdin=proc_tap.stdout, stdout=PIPE)

    out, err = proc_target.communicate()

    # write only last line of stdout into state file
    with open(path_state, "w") as state_file:
        if out not in [None, '']:
            # handle cases in which no state has been emitted -- e.g. if singer sync
            # only covered streams that do not emit state
            state_file.write(out.decode().splitlines()[-1])
            # send state after sync to S3
        else:
            # there is no state emitted
            pass

    if out not in [None, '']:
        send_state(tap, project_config, bucket, aws_profile)
    else:
        # there is no state emitted == no state to be sent to S3
        pass

    if proc_target.returncode != 0:
        raise ValueError(f"ERROR: {tap} Singer Tap shell command failed:\n{err.decode()}")
    else:
        logging.info(f"SUCCESS: {tap} Singer Tap shell command succeeded.")


def cleanup_tap(tap, clean_tap_config=True):
    """
    Cleanup temporary folders and sensitive config files after Singer Tap execution.
    """

    shutil.rmtree(states_in_path, ignore_errors=True)
    shutil.rmtree(states_out_path, ignore_errors=True)

    if clean_tap_config is True:
        try:
            os.remove(f"taps/tap-{tap}/config.json")
        except OSError:
            pass

    logging.info(f"SUCCESS: Temporary folders for {tap} cleaned up. Arrivederci.")


def cleanup_target(target, clean_target_config=True):
    """
    Cleanup temporary folders and sensitive config files after Singer Tap execution.
    """

    shutil.rmtree(states_in_path, ignore_errors=True)
    shutil.rmtree(states_out_path, ignore_errors=True)

    if clean_target_config:
        try:
            os.remove(f"targets/target-{target}/config.json")
        except OSError:
            pass

    logging.info(f"SUCCESS: Temporary folders for target-{target} cleaned up. Arrivederci.")
