# Instructions:
#   Get a token from github's settings (https://github.com/settings/tokens)
#   Install github3 using pip (pip install --pre github3.py)
#
# Example:
#   python change_log.py -k abcdefghijklmnopqrstuvwxyz -s 2017-09-06

import argparse
import datetime

import github3
import pytz

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--github-key', required=True, help='Github API Key')
parser.add_argument(
    '-s', '--start-date',
    required=False,
    help='Start of data (e.g. 2017-09-06)',
    type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
    default=datetime.datetime.now() + datetime.timedelta(-90)
)
parser.add_argument(
    '-e', '--end-date',
    required=False,
    help='Start of data (e.g. 2017-09-13)',
    type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
    default=datetime.datetime.now()
)
args = parser.parse_args()

# Connect to github
gh = github3.login(token=args.github_key)
repo = gh.repository('SEED-platform', 'seed')
internal_users = ['nllong', 'axelstudios', 'Myoldmopar', 'adrian-lara']

print(github3.octocat())
print("Connecting to GitHub repository: %s" % repo)


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
            if 'Duplicate' in labels:
                # print('Found duplicate label on issue, will ignore in change log')
                continue

            if 'No Longer Valid' in labels:
                # print('No longer valid issue found, will ignore in change log')
                continue

            if 'Feature' in labels:
                # print('New feature found')
                add_issue(closed_issues, 'Feature', issue)
            elif 'Maintenance' in labels:
                # print('New maintenance task')
                add_issue(closed_issues, 'Improved', issue)
            else:
                # print('Must be a bug')
                add_issue(closed_issues, 'Fixed', issue)

for issue in repo.issues(state='open'):
    if issue.created_at > start_date:
        # convert the github iterator to a normal list
        labels = [label.name for label in issue.labels()]

        if not issue.pull_request():
            if 'Feature' in labels:
                # print('new issue created during this time')
                add_issue(new_issues, 'New Feature', issue)
            elif 'Maintenance' in labels:
                add_issue(new_issues, 'New Improvement', issue)
            else:
                add_issue(new_issues, 'New Issue', issue)

# Sort the issues by oldest to newest
closed_issues = sorted(closed_issues, key=lambda kv: kv['number'])
accepted_pull_requests = sorted(accepted_pull_requests, key=lambda kv: kv['number'])

print('')
print('########### Review Pull Requests ################')
print(
    'Review the pull requests below to make sure that they have relevant tickets to be account for in the change log.')
for issue in accepted_pull_requests:
    print(issue)
print('')
print('')
print('########### Change Log ################')
print('')
print('Date Range: %s - %s' % (start_date.strftime('%m/%d/%y'), end_date.strftime('%m/%d/%y')))
print('')
print('New Issues:')
for issue in new_issues:
    print('- %s [#%s]( %s ), %s' % (issue['type'], issue['number'], issue['url'], issue['title']))
print('')
print('Closed Issues and Features:')
for issue in closed_issues:
    print('- %s [#%s]( %s ), %s' % (issue['type'], issue['number'], issue['url'], issue['title']))
