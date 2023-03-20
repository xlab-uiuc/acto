import argparse
import csv
import datetime
import os
import time
from typing import List
from github import Github, RateLimitExceededException, Repository, UnknownObjectException
import logging


def get_months_since(start_year: int, month: int) -> List[str]:
    end_year = datetime.date.today().year

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):

            yield datetime.date(year, month, 1).strftime('%Y-%m-%d')


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

    num_total = 0
    num_clientgo = 0
    num_controller_rt = 0

    with open(args.output, mode='w') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Name", "Owner", "Desc", "url", "forks", "stars", "watches", "created_at"])

        months_of_interest = list(get_months_since(2014, 1))  # 2014 is when k8s got released
        last_queried_month = None

        for month in months_of_interest:
            if last_queried_month is None:
                last_queried_month = month
                continue

            try:
                query = f"operator language:go created:{last_queried_month}..{month}"
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