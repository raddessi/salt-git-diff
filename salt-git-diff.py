#!/usr/bin/env python3
import yaml
import subprocess
import os
import re
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
TOP_FILE_NAME = os.getenv("TOP_FILE_NAME", "top.sls")
SALT_ENVIRONMENT = os.getenv("SALT_ENVIRONMENT", "base")


def git_changes():
    '''
    Returns a string consisting of changed files in last git commit
    '''
    gitdiff = subprocess.check_output(["git", "diff", "--name-only", "HEAD^..HEAD"])
    # Decode bytes to a string
    decoded_gitdiff = gitdiff.decode('utf-8')
    logger.debug('Changes in last commit: {}'.format(decoded_gitdiff))
    return decoded_gitdiff


def changed_states():
    '''
    Parses list of files, returns top directory names and filenames in root
    with '.sls' stripped. That is coincidentally the same logic that a saltstack
    top file uses to find states.
    '''
    changes = git_changes()
    # Find non-whitespace between whitespace and a forward slash or '.sls'. Don't be greedy.
    r = re.compile('^(\S+?)(?:/|.sls)', re.MULTILINE)
    changed_states = r.findall(changes)
    logger.debug('Changed states: {}'.format(changed_states))
    return changed_states


def previous_commit_top_file():
    '''
    Parses saltstack top file from before the last commit
    '''
    top_file_contents = subprocess.check_output(["git", "show", "HEAD^:%s" % TOP_FILE_NAME])
    return yaml.load(top_file_contents)


def current_top_file():
    '''
    Parses saltstack top file from current codebase
    '''
    with open(TOP_FILE_NAME, 'r') as stream:
        return yaml.load(stream)


def comma_split_records_in_set(nonsplit_set):
    '''
    Turn {'foo,bar', 'baz'} into {'foo', 'bar', 'baz'}
    '''
    split_set = set()
    for record in nonsplit_set:
        for item in record.split(sep=','):
            split_set.add(item)
    return split_set


def added_dict_records(current_dict, past_dict):
    '''
    Return records which are in current_dict but not in past_dict
    '''
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    added_dict_records = current_key_set - intersection
    return comma_split_records_in_set(added_dict_records)


def changed_dict_records(current_dict, past_dict):
    '''
    Return records which are in current_dict and in past_dict but with
    different values
    '''
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    changed_dict_records = set(key for key in intersection if past_dict[key] != current_dict[key])
    return comma_split_records_in_set(changed_dict_records)


def top_records_containing_states(top, match_states):
    '''
    Returns saltstack top file records that contain a state in match_states.

    With following top file contents, 'hostname.example.com' will be returned
    if 'app' is in match_states:

    'hostname.example.com':
      - app.server

    '''
    matching_records = []
    for key, states in top.items():
        # Skip records like 'os:CentOS'
        if ':' not in key:
            match = False
            for state in states:
                # Skip states like 'match: grain'
                if not isinstance(state, dict):
                    # Salt uses dot for traversing directories.
                    # We're happy as long as first part matches.
                    if state.split('.')[0] in match_states:
                        match = True
            # end for state in states
            if match:
                # A top file match can be a comma separated list of hostnames
                records = key.split(sep=',')
                matching_records.extend(records)
    # end for key, states in top
    return matching_records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        choices=["yaml", "json", "text"],
        default="yaml",
        help="Output data format (default is yaml)"
    )
    parser.add_argument(
        "--replace-asterisks",
        metavar="REPLACEMENT",
        dest="asterisk_replacement",
        help="Replace all asterisks with provided string"
    )
    args = parser.parse_args()

    changed_states = changed_states()
    current_top = current_top_file()[SALT_ENVIRONMENT]

    top_added_set = set()
    top_changed_set = set()
    if 'top' in changed_states:
        logger.info('Top file was changed. Reading changes.')

        previous_top = previous_commit_top_file()[SALT_ENVIRONMENT]

        top_added_set = added_dict_records(current_top, previous_top)
        logger.debug('Added records in top file: {}'.format(top_added_set))
        top_changed_set = changed_dict_records(current_top, previous_top)
        logger.debug('Changed records in top file: {}'.format(top_changed_set))

    # We assume that a top level directory affected by git commit
    # has the same name as a salt state.
    hostnames_containing_changed_states = set(top_records_containing_states(current_top, changed_states))
    logger.debug('Top file records containing changed states: {}'.format(hostnames_containing_changed_states))

    # Union operation to get rid of duplicates
    all_changes = list(top_added_set | top_changed_set | hostnames_containing_changed_states)

    # Filter out non-hostname matches like "os:CentOS"
    output = [x for x in all_changes if ':' not in x]

    if args.asterisk_replacement:
        output = [o.replace('*', args.asterisk_replacement) for o in output]

    if args.output == 'json':
        import json
        print(json.dumps(output, sort_keys=True, indent=4))
    elif args.output == 'text':
        for line in output:
            print(line)
    elif args.output == 'yaml':
        print(yaml.dump(output, default_flow_style=False).replace('- ', '  - '))
