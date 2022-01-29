import argparse
import csv
from github import Github

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-output", help="output csv file destination")
    parser.add_argument("-token", help="access token for github")
    args = parser.parse_args()

    github = Github(args.token)

    query = "operator+language:go"
    repos = github.search_repositories(query, sort='stars', order='desc')[:50]

    with open(args.output, mode='w') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Name", "Owner", "Desc", "url", "forks", "stars", "watches", "open issues", "closed issues"])

        for repo in repos:
            closed_issues = repo.get_issues(state='closed')
            writer.writerow([repo.name, repo.owner.login, repo.description, repo.html_url,
                            repo.forks_count, repo.stargazers_count, repo.subscribers_count, repo.open_issues_count,
                            closed_issues.totalCount])
