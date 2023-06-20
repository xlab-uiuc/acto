import os
import pathlib
import unittest

import yaml

from acto.input.get_matched_schemas import field_matched, find_matched_schema
from acto.input.known_schemas import *
from acto.input.valuegenerator import extract_schema_with_value_generator
from acto.schema import extract_schema

test_dir = pathlib.Path(__file__).parent.resolve()


class TestSchema(unittest.TestCase):

    def test_statefulset_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ['root'], crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']
                ['spec']['properties']['override']['properties']['statefulSet'])

        self.assertTrue(StatefulSetSchema.Match(spec_schema))

    def test_service_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ['root'], crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']
                ['spec']['properties']['override']['properties']['service'])

        self.assertTrue(ServiceSchema.Match(spec_schema))

    def test_affinity_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(['root'],
                                       crd['spec']['versions'][0]['schema']['openAPIV3Schema']
                                       ['properties']['spec']['properties']['affinity'])

        self.assertTrue(AffinitySchema.Match(spec_schema))

    def test_tolerations_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ArraySchema(['root'],
                                      crd['spec']['versions'][0]['schema']['openAPIV3Schema']
                                      ['properties']['spec']['properties']['tolerations'])

        self.assertTrue(TolerationsSchema.Match(spec_schema))

    def test_tolerations_not_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(['root'],
                                       crd['spec']['versions'][0]['schema']['openAPIV3Schema']
                                       ['properties']['spec']['properties']['tolerations']['items'])

        self.assertFalse(TolerationsSchema.Match(spec_schema))

    def test_resources_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(['root'],
                                       crd['spec']['versions'][0]['schema']['openAPIV3Schema']
                                       ['properties']['spec']['properties']['resources'])

        self.assertTrue(ResourceRequirementsSchema.Match(spec_schema))

    def test_container_match(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ['root'], crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']
                ['spec']['properties']['override']['properties']['statefulSet']['properties']
                ['spec']['properties']['template']['properties']['spec']['properties']['containers']
                ['items'])

        self.assertTrue(ContainerSchema.Match(spec_schema))

        with open(os.path.join(test_dir, 'psmdb.percona.com_perconaservermongodbs.yaml'),
                  'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ['root'], crd['spec']['versions'][-1]['schema']['openAPIV3Schema']['properties']
                ['spec']['properties']['replsets']['items']['properties']['sidecars']['items'])

        self.assertTrue(ContainerSchema.Match(spec_schema))

    def test_resources_match(self):
        with open(os.path.join(test_dir, 'crdb_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            tls_schema = ObjectSchema(
                ['root'],
                crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec']
                ['properties']['ingress']['properties']['sql']['properties']['tls']['items'])

        self.assertTrue(IngressTLSSchema.Match(tls_schema))

        self.assertTrue(field_matched(tls_schema, IngressTLSSchema))

    def test_pod_spec_match(self):
        with open(os.path.join(test_dir, 'cassop_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)

            spec_schema = extract_schema_with_value_generator([],
                                         crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec']['properties']['podTemplateSpec']['properties']['spec']['properties']['containers']['items']['properties']['livenessProbe'])
            # tuples = find_all_matched_schemas_type(spec_schema)
            # for tuple in tuples:
            #     print(f'Found matched schema: {tuple[0].path} -> {tuple[1]}')
            #     k8s_schema = K8sField(tuple[0].path, tuple[1])
            print(LivenessProbeSchema.Match(spec_schema))

    def test_find_matches(self):
        with open(os.path.join(test_dir, 'rabbitmq_crd.yaml'), 'r') as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = extract_schema([],
                                         crd['spec']['versions'][0]['schema']['openAPIV3Schema'])
            print(find_all_matched_schemas(spec_schema))


if __name__ == '__main__':
    unittest.main()