#!/usr/bin/env python3
import yaml
import subprocess
import os
import re

TOP_FILE_NAME = os.getenv("TOP_FILE_NAME", "top.sls")
SALT_ENVIRONMENT = os.getenv("SALT_ENVIRONMENT", "base")


def changed_directories():
    dirstat = subprocess.check_output(["git", "diff", "HEAD^..HEAD", "--dirstat=files"])
    # Decode bytes to a string
    dirstat = dirstat.decode('utf-8')
    # Find non-whitespace between whitespace and a forward slash. Don't be greedy.
    dirname = re.compile('\s(\S+?)/')
    return dirname.findall(dirstat)


def previous_commit_top_file():
    top_file_contents = subprocess.check_output(["git", "show", "HEAD^:%s" % TOP_FILE_NAME])
    return yaml.load(top_file_contents)


def current_top_file():
    with open(TOP_FILE_NAME, 'r') as stream:
        return yaml.load(stream)


def added_dict_records(current_dict, past_dict):
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    return current_key_set - intersection


def changed_dict_records(current_dict, past_dict):
    current_key_set, past_key_set = [set(d.keys()) for d in (current_dict, past_dict)]
    intersection = current_key_set.intersection(past_key_set)
    return set(key for key in intersection if past_dict[key] != current_dict[key])


def top_records_containing_states(top, match_states):
    matching_records = []
    for key, states in top.items():
        # Skip grains matches
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
        # end if ':' not in key
    # end for key, states in top
    return matching_records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output data in JSON format (default is YAML)"
    )
    args = parser.parse_args()

    current_top = current_top_file()[SALT_ENVIRONMENT]
    previous_top = previous_commit_top_file()[SALT_ENVIRONMENT]

    top_added_set = added_dict_records(current_top, previous_top)
    top_changed_set = changed_dict_records(current_top, previous_top)

    # We assume that a top level directory affected by git commit
    # has the same name as a salt state.
    changed_states = changed_directories()
    top_state_changed_set = set(top_records_containing_states(current_top, changed_states))

    # Union operation to get rid of duplicates
    output = list(top_added_set | top_changed_set | top_state_changed_set)

    if args.json:
        import json
        print(json.dumps(output, sort_keys=True, indent=4))
    else:
        print(yaml.dump(output, default_flow_style=False).replace('- ', '  - '))
