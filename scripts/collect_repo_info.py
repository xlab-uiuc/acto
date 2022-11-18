from github import Github
import csv
import datetime
from texttable import Texttable

if __name__ == '__main__':
    REPOS = [
        'k8ssandra/cass-operator',
        'cockroachdb/cockroach-operator',
        'knative/operator',
        'mongodb/mongodb-kubernetes-operator',
        'percona/percona-server-mongodb-operator',
        'percona/percona-xtradb-cluster-operator',
        'rabbitmq/cluster-operator',
        'spotahome/redis-operator',
        'OT-CONTAINER-KIT/redis-operator',
        'pingcap/tidb-operator',
        'pravega/zookeeper-operator',
    ]

    g = Github("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")

    textTable = Texttable()
    textTable.set_cols_align(["c"] * 4)
    textTable.set_deco(Texttable.HEADER)
    table = []

    with open('repo_info.csv', 'w') as outstream:
        csvwriter = csv.writer(outstream)
        csvwriter.writerow(['Name', 'Owner', 'Stars', 'Commits', 'Age'])
        for repo_name in REPOS:
            repo = g.get_repo(repo_name)
            creation_time = repo.created_at
            now = datetime.datetime.now()
            age = now - creation_time

            csvwriter.writerow([repo.name, repo.owner.login, repo.stargazers_count, repo.get_commits().totalCount, str(age)])