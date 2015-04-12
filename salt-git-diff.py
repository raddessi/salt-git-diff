#!/usr/bin/env python3
import yaml
import subprocess
import os
from dictdiffer import DictDiffer

TOP_FILE_NAME = os.getenv("TOP_FILE_NAME", "top.sls")
SALT_ENVIRONMENT = os.getenv("SALT_ENVIRONMENT", "base")


def get_environment_from_last_commit_top_file():
    top_file_contents = subprocess.check_output(["git", "show", "HEAD^:%s" % TOP_FILE_NAME])
    return yaml.load(top_file_contents)


def get_environment_from_top_file():
    with open(TOP_FILE_NAME, 'r') as stream:
        return yaml.load(stream)


def listdiff(current, previous):
    current_set = set(current)
    previous_set = set(previous)
    diff = {
               "added": list(current_set - previous_set),
               "removed": list(previous_set - current_set),
           }
    return diff


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output data in JSON format (default is YAML)"
    )
    args = parser.parse_args()

    current_top = get_environment_from_top_file()[SALT_ENVIRONMENT]
    previous_top = get_environment_from_last_commit_top_file()[SALT_ENVIRONMENT]

    topdiff = DictDiffer(current_top, previous_top)

    # For "changed" entries in top file, we go a level deeper.
    changediff = []
    for record in topdiff.changed():
        current_record = current_top[record]
        previous_record = previous_top[record]
        changediff.append({record: listdiff(current_record, previous_record)})

    output = {
                 "added": list(topdiff.added()),
                 "removed": list(topdiff.removed()),
                 "changed": changediff,
                 "unchanged": list(topdiff.unchanged()),
             }  # end output

    if args.json:
        import json
        print(json.dumps(output, sort_keys=True, indent=4))
    else:
        print(yaml.dump(output, default_flow_style=False).replace('- ', '  - '))
