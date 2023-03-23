from github import Github
from jira import JIRA

import csv
import argparse
import re

github_regex = r'^\[.*\]\(https://github.com/'
github_regex += r'(\S+)/' # owner
github_regex += r'(\S+)/' # repo
github_regex += r'(\w+)/' # issue type
github_regex += r'(\d+)\)$' # issue number
print(github_regex)

jira_regex = r'^\[.*\]\(https://jira.percona.com/browse/'
jira_regex += r'(\S+)\)$' # issue ID

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process bugs info')
    parser.add_argument('--bugs-csv', dest='bugs_csv', help='Bugs info file', required=True)
    parser.add_argument("--token", help="access token for github")
    args = parser.parse_args()

    g = Github(args.token)
    auth_jira = JIRA(server='https://jira.percona.com/', token_auth='MjY3MjI0OTkyNTc3OoKNTUoqJZrWZ7MdEZd9fZ+SxLWI')
    with open(args.bugs_csv, 'r') as bugs_csv, open('bugs_info.csv', 'w') as bugs_info_csv:
        reader = csv.reader(bugs_csv)
        writer = csv.writer(bugs_info_csv)
        for row in reader:
            repo_name = row[0]
            link = row[1]
            status = row[2]

            match = re.search(github_regex, link)
            if match:
                owner = match.group(1)
                repo_str = match.group(2)
                issue_type = match.group(3)
                issue_number = match.group(4)

                repo = g.get_repo(owner + '/' + repo_str)
                if issue_type == 'issues':
                    issue = repo.get_issue(int(issue_number))
                else:
                    issue = repo.get_pull(int(issue_number))
                writer.writerow([owner + '/' + repo_str + '#' + issue_number, repo.full_name, link, issue.title])
            else:
                match = re.search(jira_regex, link)
                if match:
                    issue_id = match.group(1)
                    issue = auth_jira.issue(issue_id)
                    writer.writerow([issue_id, repo_name, link, issue.fields.summary])