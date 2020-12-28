# Instructions:
#   Get a token from github's settings (https://github.com/settings/tokens)
#   Install github3 using pip (pip install --pre github3.py)
#
# Example:
#   python change_log.py -k abcdefghijklmnopqrstuvwxyz -s 2020-12-29

import argparse
import datetime

import github3
import pytz

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--github-key', required=True, help='Github API Key')
parser.add_argument(
    '-s', '--start-date',
    required=False,
    help='Start of data (e.g. 2020-12-29)',
    type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
    default=datetime.datetime.now() + datetime.timedelta(-90)
)
parser.add_argument(
    '-e', '--end-date',
    required=False,
    help='Start of data (e.g. 2020-12-29)',
    type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
    default=datetime.datetime.now()
)
args = parser.parse_args()

# Connect to github
gh = github3.login(token=args.github_key)
repo = gh.repository('SEED-platform', 'seed')
internal_users = ['nllong', 'axelstudios', 'Myoldmopar', 'adrian-lara']

print(gh.octocat())
print("Connecting to GitHub repository: %s" % repo)

# Naming lookups - Boolean key is if the issue is new or not.
naming_lookup = {
    "Feature": {
        True: 'New Feature',
        False: 'Feature'
    },
    "Maintenance": {
        True: 'New Maintenance',
        False: 'Maintenance'
    },
    "Enhancement": {
        True: 'New Improvement',
        False: 'Improved'
    },
    "Issue": {
        True: 'New Issue',
        False: 'Fixed'
    }
}


def add_issue(listobj, issue_type, issue):
    listobj.append({
        'type': issue_type,
        'number': issue.number,
        'title': issue.title,
        'url': issue.html_url,
    })


def add_pr(listobj, issue):
    listobj.append({
        'type': 'PR',
        'number': issue.number,
        'title': issue.title,
        'url': issue.html_url,
    })


# initialize local variables
new_issues = []
closed_issues = []
accepted_pull_requests = []

start_date = pytz.utc.localize(args.start_date)
end_date = pytz.utc.localize(args.end_date)
for issue in repo.issues(state='closed'):
    if issue.closed_at > start_date:
        # convert the github iterator to a normal list
        labels = [label.name for label in issue.labels()]

        if issue.pull_request():
            # print('Pull request found')
            add_pr(accepted_pull_requests, issue)
        else:
            if 'Include Before Closure' in labels:
                # sometimes we want to tag an item as complete before testing has
                # been finished to have it show up in the change log. This will be
                # excluded in the 'closed' checks, but included in the 'open' checks.
                continue

            if 'Duplicate' in labels:
                # print('Found duplicate label on issue, will ignore in change log')
                continue

            if 'No Longer Valid' in labels:
                # print('No longer valid issue found, will ignore in change log')
                continue

            if 'Not Reproducible' in labels:
                # these issues are noxt going to be reported
                continue

            if 'Feature' in labels:
                # print('New feature found')
                add_issue(closed_issues, naming_lookup['Feature'][False], issue)
            elif 'Maintenance' in labels:
                # print('New maintenance task')
                add_issue(closed_issues, naming_lookup['Maintenance'][False], issue)
            elif 'Enhancement' in labels:
                add_issue(closed_issues, naming_lookup['Enhancement'][False], issue)
            else:
                # print('Must be a bug')
                add_issue(closed_issues, naming_lookup['Issue'][False], issue)

# find all open issues that have the 'Include Before Closure'
for issue in repo.issues(state='open', labels='Include Before Closure'):
    labels = [label.name for label in issue.labels()]

    if not issue.pull_request():
        if 'Feature' in labels:
            # print('new issue created during this time')
            add_issue(closed_issues, naming_lookup['Feature'][False], issue)
        elif 'Maintenance' in labels:
            add_issue(closed_issues, naming_lookup['Maintenance'][False], issue)
        elif 'Enhancement' in labels:
            add_issue(closed_issues, naming_lookup['Enhancement'][False], issue)
        else:
            add_issue(closed_issues, naming_lookup['Issue'][False], issue)

for issue in repo.issues(state='open'):
    if issue.created_at > start_date:
        # convert the github iterator to a normal list
        labels = [label.name for label in issue.labels()]

        if not issue.pull_request():
            if 'Feature' in labels:
                # print('new issue created during this time')
                add_issue(new_issues, naming_lookup['Feature'][True], issue)
            elif 'Maintenance' in labels:
                add_issue(new_issues, naming_lookup['Maintenance'][True], issue)
            elif 'Enhancement' in labels:
                add_issue(new_issues, naming_lookup['Enhancement'][True], issue)
            else:
                add_issue(new_issues, naming_lookup['Issue'][True], issue)

# Sort the issues by oldest to newest
closed_issues = sorted(closed_issues, key=lambda kv: kv['number'])
accepted_pull_requests = sorted(accepted_pull_requests, key=lambda kv: kv['number'])

# print('')
# print('########### Review Pull Requests ################')
# print(
#     'Review the pull requests below to make sure that they have relevant tickets to be account for in the change log.')
# for issue in accepted_pull_requests:
#     print(issue)
# print('')
print('')
print('########### Change Log ################')
print('')
print('Date Range: %s - %s' % (start_date.strftime('%m/%d/%y'), end_date.strftime('%m/%d/%y')))
print('')
print(f'New Issues (Total: {len(new_issues)}):')
for issue in new_issues:
    print('- %s [#%s]( %s ), %s' % (issue['type'], issue['number'], issue['url'], issue['title']))
print('')
print(f'Closed Issues and Features (Total: {len(closed_issues)}):')
for issue in closed_issues:
    print('- %s [#%s]( %s ), %s' % (issue['type'], issue['number'], issue['url'], issue['title']))
