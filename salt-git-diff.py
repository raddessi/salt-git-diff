#!/usr/bin/env python3
import yaml
import subprocess
import os
import re

TOP_FILE_NAME = os.getenv("TOP_FILE_NAME", "top.sls")
SALT_ENVIRONMENT = os.getenv("SALT_ENVIRONMENT", "base")


def git_changes():
    '''
    Returns a string consisting of changed files in last git commit
    '''
    gitdiff = subprocess.check_output(["git", "diff", "--name-only", "HEAD^..HEAD"])
    # Decode bytes to a string
    return gitdiff.decode('utf-8')


def changed_states():
    '''
    Parses list of files, returns top directory names and filenames in root
    with '.sls' stripped. That is coincidentally the same logic that a saltstack
    top file uses to find states.
    '''
    changes = git_changes()
    # Find non-whitespace between whitespace and a forward slash or '.sls'. Don't be greedy.
    r = re.compile('\s(\S+?)(?:/|.sls)')
    return r.findall(changes)


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


def added_dict_records(current_dict, past_dict):
    '''
    Return records which are in current_dict but not in past_dict
    '''
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    return current_key_set - intersection


def changed_dict_records(current_dict, past_dict):
    '''
    Return records which are in current_dict and in past_dict but with
    different values
    '''
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    return set(key for key in intersection if past_dict[key] != current_dict[key])


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
        # Skip records like 'match: grain'
        if ':' not in key:
            match = False
            for state in states:
                # Salt uses dot for traversing directories.
                # We're happy as long as first part matches.
                if state.split('.')[0] in match_states:
                    match = True
            # end for state in states
            if match:
                matching_records.append(key)
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

    current_top = current_top_file()[SALT_ENVIRONMENT]
    previous_top = previous_commit_top_file()[SALT_ENVIRONMENT]

    top_added_set = added_dict_records(current_top, previous_top)
    top_changed_set = changed_dict_records(current_top, previous_top)

    # We assume that a top level directory affected by git commit
    # has the same name as a salt state.
    top_state_changed_set = set(top_records_containing_states(current_top, changed_states()))

    # Union operation to get rid of duplicates
    all_changes = list(top_added_set | top_changed_set | top_state_changed_set)

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
