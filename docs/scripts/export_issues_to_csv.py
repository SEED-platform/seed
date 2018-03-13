# pip install --pre github3.py

import argparse
import csv

import github3

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--github-key', required=True, help='Github API Key')
parser.add_argument('--csv', action='store_true', help='Download CSV of Issues')
# parser.add_argument('--diff', action='store_true', help='Download CSV of Issues')
args = parser.parse_args()

# Connect to github
gh = github3.login(token=args.github_key)
repo = gh.repository('SEED-platform', 'seed')
print(repo)

# Initialize some data
header = ["Order", "Title", "Category", "Priority", "Impact", "Estimate", "Weighted Priority", "Note", "Github ID",
          "Type/Labels", "Github URL", "Pivotal URL"]
lines = []
ids_added = []


def add_issue_to_csv(issue):
    # import json
    # print(json.dumps(issue.as_dict(), indent=2))
    print("Adding Issue %s : %s" % (issue.number, issue.title))
    labels = [l.name for l in issue.labels()]
    ids_added.append(issue.number)
    line = []
    line.append(len(lines))  # Order
    line.append(issue.title)  # Title
    line.append("")  # category
    # nrel priority
    if 'P-1' in labels:
        line.append(1)
    elif 'P-2' in labels:
        line.append(2)
    elif 'P-3' in labels:
        line.append(3)
    else:
        line.append("")

    # nrel impact
    if 'Impact-1' in labels:
        line.append(1)
    elif 'Impact-2' in labels:
        line.append(2)
    elif 'Impact-3' in labels:
        line.append(3)
    else:
        line.append("")

    # estimate
    if '1 Point' in labels:
        line.append(1)
    elif '2 Points' in labels:
        line.append(2)
    elif '3 Points' in labels:
        line.append(3)
    elif '5 Points' in labels:
        line.append(5)
    elif '8 Points' in labels:
        line.append(8)
    else:
        line.append("")
    # line.append("") # lbnl priority
    # line.append("") # lbnl impact
    line.append("")  # weighted impact
    line.append("")  # Notes
    line.append(issue.number)  # Github ID
    line.append(",".join(labels))  # Type / Labels
    line.append(issue.html_url)  # Github URL
    line.append("")  # Pivotal URL

    lines.append(line)


if args.csv:
    print("There are %s open issues" % repo.open_issues_count)

    print("Finding P-1 Issues")
    for issue in repo.issues(state='open', labels='P-1'):
        add_issue_to_csv(issue)

    print("Finding P-2 Issues")
    for issue in repo.issues(state='open', labels='P-2'):
        add_issue_to_csv(issue)

    print("Finding P-3 Issues")
    for issue in repo.issues(state='open', labels='P-3'):
        add_issue_to_csv(issue)

    print("Finding All Other Issues")
    for issue in repo.issues(state='open'):
        if issue.number not in ids_added:
            add_issue_to_csv(issue)

    # write out the lines
    with open('seed_issues.csv', 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(header)

        for line in lines:
            writer.writerow(line)
