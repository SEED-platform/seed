# pip install github3.py

# Read in a CSV and have it update an issue's priority, impact, and estimate.
# Column order is important, 0 is ID, then 3-5 are the fields to update.
#
# e.g., python docs/scripts/set_github_issue_priorities.py -k <key> -i in.csv

import argparse
import csv
import os

import github3

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--github-key', required=True, help='Github API Key')
parser.add_argument('-i', '--infile', required=True, help='Input file to parse')
args = parser.parse_args()

# Connect to github
gh = github3.login(token=args.github_key)
repo = gh.repository('SEED-platform', 'seed')
print(repo)

# Read in the CSV
if not os.path.exists(args.infile):
    print(f"Could not find input file to parse {args.infile}")

# column 3 is priority
# column 4 is user impact
# column 5 is estimate
priority_labels = ['P-1', 'P-2', 'P-3']
impact_labels = ['Impact-1', 'Impact-2', 'Impact-3']
estimate_impact = ['1 Point', '2 Points', '3 Points', '5 Points', '8 Points']
points_map = {
    1: '1 Point',
    2: '2 Points',
    3: '3 Points',
    5: '5 Points',
    8: '8 Points'
}

with open(args.infile) as csvfile:
    reader = csv.reader(csvfile)
    for index, row in enumerate(reader):
        if index >= 1:  # skip header row
            print(row)
            issue = repo.issue(row[0])
            labels = [label.name for label in issue.labels()]

            # remove any of the labels that we are setting that may
            # already be on the issue
            labels = list(set(labels) - set(priority_labels))
            labels = list(set(labels) - set(impact_labels))
            labels = list(set(labels) - set(estimate_impact))

            # add the new labels to the list
            labels.append(priority_labels[int(row[3]) - 1])
            labels.append(impact_labels[int(row[4]) - 1])
            labels.append(points_map[int(row[5])])

            # save the labels to github
            issue.edit(labels=labels)
