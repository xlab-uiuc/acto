import argparse
import csv
import os
import time
from typing import List
from github import Github, RateLimitExceededException, Repository, UnknownObjectException
import logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="output csv file destination")
    parser.add_argument("--token", help="access token for github")
    args = parser.parse_args()

    github = Github(args.token)

    logging.basicConfig(
        filename='./crawl_git_repos.log',
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("github").setLevel(logging.ERROR)

    query = "operator+language:go"
    repos: List[Repository.Repository] = github.search_repositories(query, sort='stars', order='desc')

    logging.info(f"Found {repos.totalCount} repos")
    num_clientgo = 0
    num_controller_rt = 0

    with open(args.output, mode='w') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow([
            "Name", "Owner", "Desc", "url", "forks", "stars", "watches",
            "open issues", "closed issues"
        ])


        try:
            for repo in repos:
                try:
                    result = repo.get_contents('go.mod')
                except UnknownObjectException:
                    logging.info(f"Repo {repo.name} does not have go.mod")
                    continue
                if isinstance(result, list):
                    continue
                else:
                    content = result.decoded_content.decode('utf-8')
                    if 'k8s.io/client-go' in content:
                        num_clientgo += 1
                    if 'k8s.io/controller-runtime' in content:
                        num_controller_rt += 1

                    if 'k8s.io/client-go' not in content:
                        logging.info(f"Repo {repo.name} is not operator")
                        continue
                    
                
                closed_issues = repo.get_issues(state='closed')
                writer.writerow([
                    repo.name, repo.owner.login, repo.description, repo.html_url,
                    repo.forks_count, repo.stargazers_count, repo.subscribers_count,
                    repo.open_issues_count, closed_issues.totalCount
                ])
        except RateLimitExceededException as e:
            sleep_time = int(e.headers['x-ratelimit-reset']) - time.time() + 3
            print(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
        
        logging.info(f"Found {num_clientgo} repos with client-go")
        logging.info(f"Found {num_controller_rt} repos with controller-runtime")