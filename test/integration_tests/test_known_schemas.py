# pylint: disable=missing-docstring, line-too-long

import os
import pathlib
import unittest

import yaml

from acto.input.k8s_schemas import K8sSchemaMatcher, KubernetesSchema
from acto.input.valuegenerator import extract_schema_with_value_generator
from acto.schema import extract_schema
from acto.schema.base import BaseSchema
from acto.schema.object import ObjectSchema

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestSchema(unittest.TestCase):
    """This class tests the schema matching code for various CRDs."""

    @classmethod
    def setUpClass(cls):
        cls.schema_matcher = K8sSchemaMatcher.from_version("v1.29.0")
        cls.schema_matcher_1_20 = K8sSchemaMatcher.from_version("v1.20.0")
        cls.schema_matcher_1_21 = K8sSchemaMatcher.from_version("v1.21.0")
        cls.schema_matcher_1_23 = K8sSchemaMatcher.from_version("v1.23.0")

    def assert_exists(
        self,
        suffix: str,
        schema_name: str,
        matches: list[tuple[BaseSchema, KubernetesSchema]],
    ):
        applied = 0
        for schema, k8s_schema in matches:
            if k8s_schema.k8s_schema_name is None:
                continue
            schema_path = "/".join(schema.path)
            if schema_path.endswith(suffix):
                self.assertTrue(
                    k8s_schema.k8s_schema_name.endswith(schema_name),
                    f"Schema name mismatch! Path={schema_path} Expected={schema_name} Actual={k8s_schema.k8s_schema_name}",
                )
                applied += 1
        if applied == 0:
            self.fail(f"Schema path suffix {schema_name} not found")

    def test_rabbitmq_crd(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
        spec_schema = extract_schema(
            [], crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        )
        matches = self.schema_matcher.find_all_matched_schemas(spec_schema)
        self.assert_exists("labelSelector", "v1.LabelSelector", matches)
        self.assert_exists("exec", "v1.ExecAction", matches)
        self.assert_exists("httpGet/httpHeaders/ITEM", "v1.HTTPHeader", matches)
        self.assert_exists("fieldRef", "v1.ObjectFieldSelector", matches)
        self.assert_exists("seLinuxOptions", "v1.SELinuxOptions", matches)
        self.assert_exists("seccompProfile", "v1.SeccompProfile", matches)
        self.assert_exists("volumeMounts/ITEM", "v1.VolumeMount", matches)
        self.assert_exists(
            "configMapKeyRef", "v1.ConfigMapKeySelector", matches
        )
        self.assert_exists("secretKeyRef", "v1.SecretKeySelector", matches)
        self.assert_exists("envFrom/ITEM", "v1.EnvFromSource", matches)
        self.assert_exists(
            "Containers/ITEM/ports/ITEM", "v1.ContainerPort", matches
        )
        self.assert_exists("capabilities", "v1.Capabilities", matches)
        self.assert_exists("volumeDevices/ITEM", "v1.VolumeDevice", matches)
        self.assert_exists("tolerations/ITEM", "v1.Toleration", matches)
        self.assert_exists(
            "spec/dataSource", "v1.TypedLocalObjectReference", matches
        )
        self.assert_exists("affinity/nodeAffinity", "v1.NodeAffinity", matches)
        self.assert_exists(
            "imagePullSecrets/ITEM", "v1.LocalObjectReference", matches
        )
        self.assert_exists("volumes/ITEM/nfs", "v1.NFSVolumeSource", matches)
        self.assert_exists(
            "volumes/ITEM/hostPath", "v1.HostPathVolumeSource", matches
        )
        self.assert_exists("securityContext/sysctls/ITEM", "v1.Sysctl", matches)

    def test_cassop_crd(self):
        with open(
            os.path.join(test_data_dir, "cassop_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
        spec_schema = extract_schema(
            [], crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        )
        matches = self.schema_matcher.find_all_matched_schemas(spec_schema)
        self.assert_exists("affinity/nodeAffinity", "v1.NodeAffinity", matches)
        self.assert_exists(
            "podAffinityTerm/labelSelector", "v1.LabelSelector", matches
        )
        self.assert_exists(
            "podAffinityTerm/namespaceSelector", "v1.LabelSelector", matches
        )
        self.assert_exists(
            "requiredDuringSchedulingIgnoredDuringExecution/ITEM/labelSelector",
            "v1.LabelSelector",
            matches,
        )
        self.assert_exists(
            "requiredDuringSchedulingIgnoredDuringExecution/ITEM/namespaceSelector",
            "v1.LabelSelector",
            matches,
        )
        self.assert_exists(
            "configMapKeyRef", "v1.ConfigMapKeySelector", matches
        )
        self.assert_exists("fieldRef", "v1.ObjectFieldSelector", matches)
        self.assert_exists("secretKeyRef", "v1.SecretKeySelector", matches)
        self.assert_exists("envFrom/ITEM", "v1.EnvFromSource", matches)
        self.assert_exists("lifecycle/postStart/exec", "v1.ExecAction", matches)
        self.assert_exists("httpGet/httpHeaders/ITEM", "v1.HTTPHeader", matches)
        self.assert_exists("livenessProbe/exec", "v1.ExecAction", matches)
        self.assert_exists("ports/ITEM", "v1.ContainerPort", matches)
        self.assert_exists("readinessProbe/exec", "v1.ExecAction", matches)
        self.assert_exists("readinessProbe/grpc", "v1.GRPCAction", matches)
        self.assert_exists(
            "containers/ITEM/securityContext", "v1.SecurityContext", matches
        )
        self.assert_exists("volumeDevices/ITEM", "v1.VolumeDevice", matches)
        self.assert_exists("volumeMounts/ITEM", "v1.VolumeMount", matches)
        self.assert_exists(
            "podTemplateSpec/spec/dnsConfig", "v1.PodDNSConfig", matches
        )
        self.assert_exists("podTemplateSpec/spec/os", "v1.PodOS", matches)
        self.assert_exists(
            "spec/readinessGates/ITEM", "v1.PodReadinessGate", matches
        )
        self.assert_exists(
            "podTemplateSpec/spec/securityContext",
            "v1.PodSecurityContext",
            matches,
        )
        self.assert_exists("spec/tolerations/ITEM", "v1.Toleration", matches)
        self.assert_exists(
            "topologySpreadConstraints/ITEM/labelSelector",
            "v1.LabelSelector",
            matches,
        )
        self.assert_exists(
            "volumes/ITEM/awsElasticBlockStore",
            "v1.AWSElasticBlockStoreVolumeSource",
            matches,
        )
        self.assert_exists(
            "volumes/ITEM/azureDisk", "v1.AzureDiskVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/azureFile", "v1.AzureFileVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/cephfs", "v1.CephFSVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/cinder", "v1.CinderVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/configMap", "v1.ConfigMapVolumeSource", matches
        )
        self.assert_exists("volumes/ITEM/csi", "v1.CSIVolumeSource", matches)
        self.assert_exists(
            "items/ITEM/fieldRef", "v1.ObjectFieldSelector", matches
        )
        self.assert_exists(
            "volumeClaimTemplate/spec/dataSource",
            "v1.TypedLocalObjectReference",
            matches,
        )
        # self.assert_exists("volumeClaimTemplate/spec/dataSourceRef", "v1.TypedObjectReference", matches)
        self.assert_exists(
            "volumeClaimTemplate/spec/selector", "v1.LabelSelector", matches
        )
        self.assert_exists("volumes/ITEM/fc", "v1.FCVolumeSource", matches)
        self.assert_exists(
            "volumes/ITEM/flexVolume", "v1.FlexVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/flocker", "v1.FlockerVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/gcePersistentDisk",
            "v1.GCEPersistentDiskVolumeSource",
            matches,
        )
        self.assert_exists(
            "volumes/ITEM/gitRepo", "v1.GitRepoVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/glusterfs", "v1.GlusterfsVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/hostPath", "v1.HostPathVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/iscsi", "v1.ISCSIVolumeSource", matches
        )
        self.assert_exists("volumes/ITEM/nfs", "v1.NFSVolumeSource", matches)
        self.assert_exists(
            "volumes/ITEM/persistentVolumeClaim",
            "v1.PersistentVolumeClaimVolumeSource",
            matches,
        )
        self.assert_exists(
            "volumes/ITEM/photonPersistentDisk",
            "v1.PhotonPersistentDiskVolumeSource",
            matches,
        )
        self.assert_exists(
            "volumes/ITEM/portworxVolume", "v1.PortworxVolumeSource", matches
        )
        self.assert_exists(
            "sources/ITEM/configMap", "v1.ConfigMapProjection", matches
        )
        self.assert_exists(
            "volumes/ITEM/quobyte", "v1.QuobyteVolumeSource", matches
        )
        self.assert_exists("volumes/ITEM/rbd", "v1.RBDVolumeSource", matches)
        self.assert_exists(
            "volumes/ITEM/scaleIO", "v1.ScaleIOVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/secret", "v1.SecretVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/storageos", "v1.StorageOSVolumeSource", matches
        )
        self.assert_exists(
            "volumes/ITEM/vsphereVolume",
            "v1.VsphereVirtualDiskVolumeSource",
            matches,
        )
        self.assert_exists(
            "ITEM/pvcSpec/dataSource", "v1.TypedLocalObjectReference", matches
        )
        # self.assert_exists("ITEM/pvcSpec/dataSourceRef", "v1.TypedObjectReference", matches)
        self.assert_exists(
            "storageConfig/cassandraDataVolumeClaimSpec/dataSource",
            "v1.TypedLocalObjectReference",
            matches,
        )
        self.assert_exists(
            "storageConfig/cassandraDataVolumeClaimSpec/dataSourceRef",
            "v1alpha2.ResourceClaimParametersReference",
            matches,
        )
        self.assert_exists(
            "storageConfig/cassandraDataVolumeClaimSpec/selector",
            "v1.LabelSelector",
            matches,
        )
        self.assert_exists("spec/tolerations/ITEM", "v1.Toleration", matches)

    def test_strimzi_kafka_crd(self):
        with open(
            os.path.join(test_data_dir, "kafka_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)

        spec_schema = extract_schema(
            [], crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        )
        matches = self.schema_matcher.find_all_matched_schemas(spec_schema)
        self.assert_exists(
            "namespaceSelector/matchExpressions/ITEM",
            "v1.LabelSelectorRequirement",
            matches,
        )
        self.assert_exists(
            "labelSelector/matchExpressions/ITEM",
            "v1.LabelSelectorRequirement",
            matches,
        )
        self.assert_exists(
            "container/securityContext", "v1.SecurityContext", matches
        )
        self.assert_exists("resources/claims/ITEM", "v1.ResourceClaim", matches)
        self.assert_exists(
            "configMapKeyRef", "v1.ConfigMapKeySelector", matches
        )
        self.assert_exists(
            "imagePullSecrets/ITEM", "v1.LocalObjectReference", matches
        )
        self.assert_exists(
            "pod/securityContext", "v1.PodSecurityContext", matches
        )
        self.assert_exists("affinity/nodeAffinity", "v1.NodeAffinity", matches)
        self.assert_exists("tolerations/ITEM", "v1.Toleration", matches)
        self.assert_exists("hostAliases/ITEM", "v1.HostAlias", matches)
        self.assert_exists(
            "networkPolicyPeers/ITEM/ipBlock", "v1.IPBlock", matches
        )
        # The following are schemas that are descendants of already matched schemas
        self.assert_exists("capabilities", "v1.Capabilities", matches)
        self.assert_exists("seLinuxOptions", "v1.SELinuxOptions", matches)
        self.assert_exists("seccompProfile", "v1.SeccompProfile", matches)

    @unittest.skip("Need approaximate matching for the RabbitMQ's StatefulSet")
    def test_statefulset_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["override"]["properties"][
                    "statefulSet"
                ][
                    "properties"
                ][
                    "spec"
                ],
            )

        self.assertTrue(
            self.schema_matcher_1_20.k8s_models[
                "io.k8s.api.apps.v1.StatefulSetSpec"
            ].match(spec_schema)
        )

    # @unittest.skip("Need approaximate matching for the schema path")
    def test_service_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["override"]["properties"]["service"][
                    "properties"
                ][
                    "spec"
                ],
            )

        self.assertTrue(
            self.schema_matcher_1_21.k8s_models[
                "io.k8s.api.core.v1.ServiceSpec"
            ].match(spec_schema)
        )

    def test_affinity_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["affinity"],
            )

        self.assertTrue(
            self.schema_matcher_1_23.k8s_models[
                "io.k8s.api.core.v1.Affinity"
            ].match(spec_schema)
        )

    def test_toleration_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["tolerations"]["items"],
            )

        self.assertTrue(
            self.schema_matcher.k8s_models[
                "io.k8s.api.core.v1.Toleration"
            ].match(spec_schema)
        )

    def test_resources_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["resources"],
            )

        print(
            self.schema_matcher_1_20.k8s_models[
                "io.k8s.api.core.v1.ResourceRequirements"
            ].dump_schema()
        )

        print(spec_schema)

        self.assertTrue(
            self.schema_matcher_1_20.k8s_models[
                "io.k8s.api.core.v1.ResourceRequirements"
            ].match(spec_schema)
        )

    def test_container_match(self):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            container_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["override"]["properties"][
                    "statefulSet"
                ][
                    "properties"
                ][
                    "spec"
                ][
                    "properties"
                ][
                    "template"
                ][
                    "properties"
                ][
                    "spec"
                ][
                    "properties"
                ][
                    "containers"
                ][
                    "items"
                ],
            )
            probe_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["override"]["properties"][
                    "statefulSet"
                ][
                    "properties"
                ][
                    "spec"
                ][
                    "properties"
                ][
                    "template"
                ][
                    "properties"
                ][
                    "spec"
                ][
                    "properties"
                ][
                    "containers"
                ][
                    "items"
                ][
                    "properties"
                ][
                    "livenessProbe"
                ],
            )

        self.assertTrue(
            self.schema_matcher_1_21.k8s_models[
                "io.k8s.api.core.v1.Probe"
            ].match(probe_schema)
        )

        self.assertTrue(
            self.schema_matcher_1_21.k8s_models[
                "io.k8s.api.core.v1.Container"
            ].match(container_schema)
        )

        with open(
            os.path.join(
                test_data_dir,
                "psmdb.percona.com_perconaservermongodbs.yaml",
            ),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["replsets"]["items"]["properties"][
                    "sidecars"
                ][
                    "items"
                ],
            )

        self.assertTrue(
            self.schema_matcher_1_23.k8s_models[
                "io.k8s.api.core.v1.Container"
            ].match(spec_schema)
        )

    def test_ingress_tls_match(self):
        with open(
            os.path.join(test_data_dir, "crdb_crd.yaml"), "r", encoding="utf-8"
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            tls_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["ingress"]["properties"]["sql"][
                    "properties"
                ][
                    "tls"
                ][
                    "items"
                ],
            )

        self.assertTrue(
            self.schema_matcher.k8s_models[
                "io.k8s.api.networking.v1.IngressTLS"
            ].match(tls_schema)
        )

    def test_pod_spec_match(self):
        with open(
            os.path.join(test_data_dir, "cassop_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)

            spec_schema = extract_schema_with_value_generator(
                [],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["podTemplateSpec"]["properties"][
                    "spec"
                ][
                    "properties"
                ][
                    "containers"
                ][
                    "items"
                ][
                    "properties"
                ][
                    "livenessProbe"
                ],
            )
            # tuples = find_all_matches_schemas_type(spec_schema)
            # for tuple in tuples:
            #     print(f"Found matches schema: {tuple[0].path} -> {tuple[1]}")
            #     k8s_schema = K8sField(tuple[0].path, tuple[1])
            self.assertTrue(
                self.schema_matcher_1_23.k8s_models[
                    "io.k8s.api.core.v1.Probe"
                ].match(spec_schema)
            )

    def test_pvc_match(self):
        with open(
            os.path.join(
                test_data_dir, "databases.spotahome.com_redisfailovers.yaml"
            ),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
                    "properties"
                ]["spec"]["properties"]["redis"]["properties"]["storage"][
                    "properties"
                ][
                    "persistentVolumeClaim"
                ][
                    "properties"
                ][
                    "spec"
                ],
            )

            self.assertTrue(
                self.schema_matcher_1_23.k8s_models[
                    "io.k8s.api.core.v1.PersistentVolumeClaimSpec"
                ].match(spec_schema)
            )

    def test_opaque_semantic_schema(self):
        with open(
            os.path.join(
                test_data_dir, "hdfsclusters.hdfs.stackable.tech.yaml"
            ),
            "r",
            encoding="utf-8",
        ) as crd_yaml:
            crd = yaml.load(crd_yaml, Loader=yaml.FullLoader)
            spec_schema = ObjectSchema(
                ["root"],
                crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"],
            )

            self.schema_matcher.find_all_matched_schemas(spec_schema)


if __name__ == "__main__":
    unittest.main()
