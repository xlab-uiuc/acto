#%%
import argparse
import csv
import datetime
import os
import random
import time
from typing import List
from github import Github, RateLimitExceededException, Repository, UnknownObjectException, GithubException
import logging


def shuffle_csv(csv_file: str, output_file: str):
    random.seed(0)
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader, None) # skip header
        data = list(reader)

    random.shuffle(data)

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(data)

#%%
shuffle_csv('../data/df_10_commits_uptodate.csv', '../data/df_10_commits_uptodate_shuffled.csv')

#%%


def get_months_since(start_year: int, month: int) -> List[str]:
    end_year = datetime.date.today().year

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):

            yield datetime.date(year, month, 1).strftime('%Y-%m-%d')


def crawl_github_repos(output_file: str, token: str):
    github = Github(token)

    num_total = 0
    num_clientgo = 0
    num_controller_rt = 0

    with open(output_file, mode='w') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Name", "Owner", "Desc", "url", "forks", "stars", "watches", "created_at"])

        months_of_interest = list(get_months_since(2014, 1))  # 2014 is when k8s got released
        last_queried_month = None

        for month in months_of_interest:
            if last_queried_month is None:
                last_queried_month = month
                continue

            try:
                query = f"kubernetes operator language:go created:{last_queried_month}..{month}"
                repos: List[Repository.Repository] = github.search_repositories(query)

                logging.info(f"Found {repos.totalCount} repos for {last_queried_month} - {month}")
                if repos.totalCount == 1000:
                    logging.warning(
                        f"Found 1000 repos for {last_queried_month} - {month}, risk of overflowing")
                
                num_total += repos.totalCount

                rows = []
                for repo in repos:
                    try:
                        result = repo.get_contents('go.mod')
                    except UnknownObjectException:
                        continue

                    if isinstance(result, list):
                        continue
                    else:
                        content = result.decoded_content.decode('utf-8')
                        if 'k8s.io/controller-runtime' in content:
                            num_controller_rt += 1
                        if 'k8s.io/client-go' in content:
                            num_clientgo += 1
                        else:
                            continue

                    rows.append([
                        repo.name, repo.owner.login, repo.description, repo.html_url,
                        repo.forks_count, repo.stargazers_count, repo.subscribers_count,
                        repo.created_at.strftime('%Y-%m-%d')
                    ])

                writer.writerows(rows)
                last_queried_month = month
            except RateLimitExceededException as e:
                sleep_time = int(e.headers['x-ratelimit-reset']) - time.time() + 3
                print(f"Sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

        logging.info(f"Query returned {num_total} repos in total")
        logging.info(f"Found {num_clientgo} repos with client-go")
        logging.info(f"Found {num_controller_rt} repos with controller-runtime")


def crawl_github_repos_v2(output_file: str, token: str):
    github = Github(token)

    num_total = 0

    with open(output_file, mode='w') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Name", "Owner", "Desc", "url", "forks", "stars", "commits", "watches", "created_at", "pushed_at"])

        # months_of_interest = list(get_months_since(2017, 1))  # 2014 is when k8s got released
        months_of_interest = ['2022-10-01', '2022-11-01', '2022-12-01']
        last_queried_month = None
        next_index = 0

        for month in months_of_interest:
            if last_queried_month is None:
                last_queried_month = month
                continue

            try:
                query = f"kubernetes operator in:name,description,readme created:{last_queried_month}..{month}"
                repos: List[Repository.Repository] = github.search_repositories(query)

                logging.info(f"Found {repos.totalCount} repos for {last_queried_month} - {month}")
                if repos.totalCount == 1000:
                    logging.warning(
                        f"Found 1000 repos for {last_queried_month} - {month}, risk of overflowing")
                
                num_total += repos.totalCount

                rows = []
                for repo in repos:
                    try:
                        num_commits = repo.get_commits().totalCount
                    except GithubException as e:
                        if e.status == 409 and e.data['message'] == 'Git Repository is empty.':
                            num_commits = 0
                        else:
                            raise e

                    rows.append([
                        repo.name, repo.owner.login, repo.description, repo.html_url,
                        repo.forks_count, repo.stargazers_count, repo.subscribers_count, num_commits,
                        repo.created_at.strftime('%Y-%m-%d'), repo.pushed_at.strftime('%Y-%m-%d')
                    ])

                writer.writerows(rows)
                last_queried_month = month
                out_csv.flush()
            except RateLimitExceededException as e:
                sleep_time = int(e.headers['x-ratelimit-reset']) - time.time() + 3
                print(f"Sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

        logging.info(f"Query returned {num_total} repos in total")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="output csv file destination")
    parser.add_argument("--token", help="access token for github")
    args = parser.parse_args()

    logging.basicConfig(
        filename='./crawl_git_repos.log',
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("github").setLevel(logging.ERROR)

    crawl_github_repos_v2(args.output, args.token)