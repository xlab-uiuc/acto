import argparse
import json
import os


def count_recovery_deletion_tests(folder_path: str):
    """Count the number of deletion and recovery tests in the testrun folder"""
    # Initialize the test counter
    recovery_tests_ = 0
    deletion_tests_ = 0

    # Iterate over all files in the folder
    for root, dirs, _ in os.walk(folder_path):
        for dir_ in dirs:
            deletion_tests_ += 1
            if "mutated--01.yaml" in os.listdir(os.path.join(root, dir_)):
                recovery_tests_ += 1

    return deletion_tests_, recovery_tests_


def count_post_diff_tests(folder_path: str) -> int:
    """Count the number of post-diff tests in the testrun folder"""
    # Initialize the test counter
    post_diff_tests_ = 0

    for root, dirs, _ in os.walk(folder_path):
        for root, dirs, _ in os.walk(os.path.join(root, "post_diff_test")):
            for dir_ in dirs:
                for file in os.listdir(os.path.join(root, dir_)):
                    if file.startswith("mutated"):
                        post_diff_tests_ += 1

    return post_diff_tests_


def read_normal_tests(folder_path) -> int:
    """Read the number of normal tests in the testrun folder"""
    # Initialize the test counter
    normal_tests_ = 0

    with open(
        os.path.join(folder_path, "testrun_info.json"), "r", encoding="utf-8"
    ) as f:
        testrun_info = json.load(f)
        normal_tests_ = testrun_info["num_total_testcases"][
            "total_number_of_test_cases"
        ]

    return normal_tests_


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the testrun folder")
    parser.add_argument("--operator", type=str, help="Name of the operator")
    args = parser.parse_args()

    deletion_tests, recovery_tests = count_recovery_deletion_tests(args.path)
    normal_tests = read_normal_tests(args.path)
    post_diff_tests = count_post_diff_tests(  # pylint: disable=invalid-name
        args.path
    )

    total = deletion_tests + recovery_tests + post_diff_tests + normal_tests

    print(f"Operator: {args.operator}")
    print(f"Total tests: {total}")
    print(f"    Normal tests: {normal_tests}")
    print(f"    Deletion tests: {deletion_tests}")
    print(f"    Recovery tests: {recovery_tests}")
    print(f"    Post-diff tests: {post_diff_tests}")
