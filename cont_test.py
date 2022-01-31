import argparse
from distutils.log import error
import os
import kubernetes
import yaml
import time
import Test

def test_modify_yaml():
    with open('namespace.yaml', 'r+') as operator_yaml:
        namespace = str()
        parsed_operator_documents = yaml.load_all(operator_yaml, Loader=yaml.FullLoader)
        new_yaml = []
        for document in parsed_operator_documents:
            if document['kind'] == 'Deployment':
                document['metadata']['labels']['testing/tag'] = 'testing'
                namespace = document['metadata']['namespace']
            new_yaml.append(document)
        print('cat <<EOF | kubectl apply -f -\n%s\nEOF' % yaml.dump_all(new_yaml))

def test_construct_candidate_helper():
    input_dict = {
        'a': {
            'candidates': [1, 2, 3]
        },
        'b': {
            'c': {
                'candidates': [1]
            },
            'd': {
                'candidates': [2]
            }
        }
    }
    print(input_dict)
    result={}
    Test.construct_candidate_helper(input_dict, '', result)
    print(result)

def test_mutate_application_spec():
    current_dict = {
        'a': 2,
        'b': {
            'c': 0,
            'd': 0
        }
    }

    candidates_dict = {'.a': [1, 2, 3], '.b.c': [1], '.b.d': [2]}
    print(Test.mutate_application_spec(current_dict, candidates_dict))


if __name__ == '__main__':
    test_modify_yaml()
    test_construct_candidate_helper()
    test_mutate_application_spec()