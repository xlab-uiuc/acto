from enum import Enum
from typing import Dict


class BugCategory(str, Enum):
    """Categories of bugs in the Oat NSDI 26 paper"""

    OPERATION_SEMANTICS = "Operation Semantics"
    STATE_OBSERVABILITY = "State Observability"
    VERSION_COMPATIBILITY = "Version Compatibility"
    ERROR_HANDLING = "Error Handling"
    BY_PRODUCT = "By Product"

    def __str__(self) -> str:
        return self.value


class OatBugConfig:
    """Configuration for a bug in the Oat NSDI 26 paper"""

    def __init__(
        self,
        category: BugCategory,
        path: str,
        difftest: bool = False,
        fault: bool = False,
    ) -> None:
        self._category = category
        self._path = path
        self._difftest = difftest
        self._fault = fault

    @property
    def category(self) -> BugCategory:
        """The category of the bug"""
        return self._category

    @property
    def path(self) -> str:
        """The relative directory containing the inputs for reproducing this bug"""
        return self._path

    @property
    def difftest(self) -> bool:
        """If the bug is found by the differential oracle"""
        return self._difftest

    @property
    def fault(self) -> bool:
        """If the bug requires a fault injection to reproduce"""
        return self._fault


class OperatorPrettyName(str, Enum):
    """Pretty names for operators in the Oat NSDI 26 paper"""

    CASS_OPERATOR = "CassOp"
    KAFKA_OPERATOR = "KafkaOp"
    MARIADB_OPERATOR = "MariaDBOp"
    MINIO_OPERATOR = "MinIOOp"
    MONGODB_OPERATOR = "MongoOp"
    TIDB_OPERATOR = "TiDBOp"


# Mapping from operator name to pretty name
operator_pretty_name_mapping: Dict[str, OperatorPrettyName] = {
    "cass-operator": OperatorPrettyName.CASS_OPERATOR,
    "kafka-operator": OperatorPrettyName.KAFKA_OPERATOR,
    "mariadb-operator": OperatorPrettyName.MARIADB_OPERATOR,
    "minio-operator": OperatorPrettyName.MINIO_OPERATOR,
    "mongodb-operator": OperatorPrettyName.MONGODB_OPERATOR,
    "tidb-operator": OperatorPrettyName.TIDB_OPERATOR,
}


ALL_BUGS: dict[OperatorPrettyName, dict[str, OatBugConfig]] = {
    OperatorPrettyName.CASS_OPERATOR: {
        "cassop-103": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/cassop-103",
            fault=True,
        ),
        "cassop-532": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/cassop-532",
        ),
        "cassop-694": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/cassop-694",
            difftest=True,
        ),
        "cassop-695": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/cassop-695",
        ),
        "cassop-696": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/cassop-696",
        ),
        "cassop-705": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/cassop-705",
        ),
        "cassop-725": OatBugConfig(
            category=BugCategory.VERSION_COMPATIBILITY,
            path="test/oat_tests/cassop-725",
        ),
        "k8ssandra-client-80-0": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/k8ssandra-client-80-0",
        ),
        "k8ssandra-client-80-1": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/k8ssandra-client-80-1",
        ),
        "k8ssandra-client-80-2": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/k8ssandra-client-80-2",
        ),
    },
    OperatorPrettyName.KAFKA_OPERATOR: {
        "kafkaop-10231": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/kafkaop-10231",
            difftest=True,
        ),
        "kafkaop-11084": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/kafkaop-11084",
        ),
        "kafkaop-11085": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/kafkaop-11085",
        ),
    },
    OperatorPrettyName.MARIADB_OPERATOR: {
        "mariadbop-863": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-863",
        ),
        "mariadbop-864": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-864",
        ),
        "mariadbop-866": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-866",
        ),
        "mariadbop-874": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/mariadbop-874",
            difftest=True,
        ),
        "mariadbop-875": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/mariadbop-875",
            difftest=True,
        ),
        "mariadbop-876": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/mariadbop-876",
            difftest=True,
        ),
        "mariadbop-927": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-927",
            fault=True,
        ),
        "mariadbop-1021": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-1021",
        ),
        "mariadbop-1022": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-1022",
        ),
        "mariadbop-1023": OatBugConfig(
            category=BugCategory.ERROR_HANDLING,
            path="test/oat_tests/mariadbop-1023",
            fault=True,
        ),
        "mariadbop-1024": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-1024",
            fault=True,
        ),
        "mariadbop-1072": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-1072",
        ),
        "mariadbop-1096": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/mariadbop-1096",
        ),
        "mariadbop-1226": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/mariadbop-1226",
        ),
        "MDEV-35569": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35569",
        ),
        "MDEV-35722": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35722",
        ),
        "MDEV-35754-0": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-0",
        ),
        "MDEV-35754-1": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-1",
        ),
        "MDEV-35754-2": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-2",
        ),
        "MDEV-35754-3": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-3",
        ),
        "MDEV-35754-4": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-4",
        ),
        "MDEV-35754-5": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-5",
        ),
        "MDEV-35754-6": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-6",
        ),
        "MDEV-35754-7": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-7",
        ),
        "MDEV-35754-8": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-8",
        ),
        "MDEV-35754-9": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/MDEV-35754-9",
        ),
        "mysql-116879": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/mysql-116879",
        ),
    },
    OperatorPrettyName.MINIO_OPERATOR: {
        "minioop-1100": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/minioop-1100",
        ),
        "minioop-2392": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/minioop-2392",
        ),
    },
    OperatorPrettyName.MONGODB_OPERATOR: {
        "K8SPSMDB-1103": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1103",
            fault=True,
        ),
        "K8SPSMDB-1143": OatBugConfig(
            category=BugCategory.ERROR_HANDLING,
            path="test/oat_tests/K8SPSMDB-1143",
        ),
        "K8SPSMDB-1144": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1144",
        ),
        "K8SPSMDB-1145": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/K8SPSMDB-1145",
            difftest=True,
        ),
        "K8SPSMDB-1154": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1154",
        ),
        "K8SPSMDB-1155": OatBugConfig(
            category=BugCategory.ERROR_HANDLING,
            path="test/oat_tests/K8SPSMDB-1155",
        ),
        "K8SPSMDB-1156": OatBugConfig(
            category=BugCategory.ERROR_HANDLING,
            path="test/oat_tests/K8SPSMDB-1156",
            difftest=True,
        ),
        "K8SPSMDB-1157": OatBugConfig(
            category=BugCategory.VERSION_COMPATIBILITY,
            path="test/oat_tests/K8SPSMDB-1157",
        ),
        "K8SPSMDB-1178": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1178",
            fault=True,
        ),
        "K8SPSMDB-1200": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/K8SPSMDB-1200",
            difftest=True,
        ),
        "K8SPSMDB-1201": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1201",
        ),
        "K8SPSMDB-1240": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1240",
        ),
        "K8SPSMDB-1241": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1241",
        ),
        "K8SPSMDB-1242": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1242",
        ),
        "K8SPSMDB-1333": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/K8SPSMDB-1333",
        ),
        "K8SPSMDB-1334": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/K8SPSMDB-1334",
        ),
        "K8SPSMDB-1335-0": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-0",
        ),
        "K8SPSMDB-1335-1": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-1",
        ),
        "K8SPSMDB-1335-2": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-2",
        ),
        "K8SPSMDB-1335-3": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-3",
        ),
        "K8SPSMDB-1335-4": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-4",
        ),
        "K8SPSMDB-1335-5": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-5",
        ),
        "K8SPSMDB-1335-6": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-6",
        ),
        "K8SPSMDB-1335-7": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-7",
        ),
        "K8SPSMDB-1335-8": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-8",
        ),
        "K8SPSMDB-1335-9": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/K8SPSMDB-1335-9",
        ),
    },
    OperatorPrettyName.TIDB_OPERATOR: {
        "tidbop-98": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidbop-98",
            difftest=True,
        ),
        "tidbop-5728": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-5728",
        ),
        "tidbop-5729": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-5729",
        ),
        "tidbop-5739": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidbop-5739",
        ),
        "tidbop-5741": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidbop-5741",
            difftest=True,
        ),
        "tidbop-5742": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidbop-5742",
        ),
        "tidbop-5833": OatBugConfig(
            category=BugCategory.VERSION_COMPATIBILITY,
            path="test/oat_tests/tidbop-5833",
        ),
        "tidbop-5834": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-5834",
        ),
        "tidbop-5835": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidbop-5835",
        ),
        "tidbop-6013": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/tidbop-6013",
        ),
        "tidbop-6014": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6014",
        ),
        "tidbop-6015": OatBugConfig(
            category=BugCategory.STATE_OBSERVABILITY,
            path="test/oat_tests/tidbop-6015",
        ),
        "tidbop-6131": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6131",
        ),
        "tidbop-6134-0": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6134-0",
        ),
        "tidbop-6134-1": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6134-1",
        ),
        "tidbop-6134-2": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6134-2",
        ),
        "tidbop-6134-3": OatBugConfig(
            category=BugCategory.OPERATION_SEMANTICS,
            path="test/oat_tests/tidbop-6134-3",
        ),
        "tidb-56643": OatBugConfig(
            category=BugCategory.BY_PRODUCT,
            path="test/oat_tests/tidb-56643",
        ),
    },
}
