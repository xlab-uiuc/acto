import json
import re

from acto.common import get_thread_logger

KLOG_REGEX = r"^\s*"
KLOG_REGEX += r"(\w)"  # group 1: level
# group 2-7: timestamp
KLOG_REGEX += r"(\d{2})(\d{2})\s(\d{2}):(\d{2}):(\d{2})\.(\d{6})"
KLOG_REGEX += r"\s+"
KLOG_REGEX += r"(\d+)"  # group 8
KLOG_REGEX += r"\s"
KLOG_REGEX += r"(.+):"  # group 9: filename
KLOG_REGEX += r"(\d+)"  # group 10: lineno
KLOG_REGEX += r"\]\s"
KLOG_REGEX += r"(.*?)"  # group 11: message
KLOG_REGEX += r"\s*$"

LOGR_REGEX = r"^\s*"
# group 1: timestamp
LOGR_REGEX += r"(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)"
LOGR_REGEX += r"\s+([A-Z]+)"  # group 2: level
LOGR_REGEX += r"\s+(\S+)"  # group 3: source
LOGR_REGEX += r"\s+(.*?)"  # group 4: message
LOGR_REGEX += r"\s*$"

# 1.6599427639039357e+09	INFO	controllers.CassandraDatacenter	Reconcile loop completed	{"cassandradatacenter": "cass-operator/test-cluster", "requestNamespace": "cass-operator", "requestName": "test-cluster", "loopID": "be419d0c-c7d0-4dfa-8596-af94ea15d4f6", "duration": 0.253729569}
LOGR_SPECIAL_REGEX = r"^\s*"
LOGR_SPECIAL_REGEX += r"(\d{1}\.\d+e\+\d{2})"  # group 1: timestamp
LOGR_SPECIAL_REGEX += r"\s+([A-Z]+)"  # group 2: level
LOGR_SPECIAL_REGEX += r"\s+(\S+)"  # group 3: source
LOGR_SPECIAL_REGEX += r"\s+(.*?)"  # group 4: message
LOGR_SPECIAL_REGEX += r"\s*$"

# time="2022-08-08T03:21:28Z" level=debug msg="Sentinel is not monitoring the correct master, changing..." src="checker.go:175"
# time="2022-08-08T03:21:56Z" level=info msg="deployment updated" deployment=rfs-test-cluster namespace=acto-namespace service=k8s.deployment src="deployment.go:102"
LOGRUS_REGEX = r"^\s*"
# group 1: timestamp
LOGRUS_REGEX += r'time="(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}Z)"'
LOGRUS_REGEX += r"\s+level=([a-z]+)"  # group 2: level
LOGRUS_REGEX += r'\s+msg="(.*?[^\\])"'  # group 3: message
LOGRUS_REGEX += r".*"
LOGRUS_REGEX += r'\s+(src="(.*?)")?'  # group 4: src
LOGRUS_REGEX += r"\s*$"
# this is semi-auto generated by copilot, holy moly

# This one is similar to LOGR_SPECIAL_REGEX and LOGRUS_REGEX, but with some differences
# 2024-03-05T10:07:17Z	ERROR	GrafanaReconciler	reconciler error in stage	{"controller": "grafana", "controllerGroup": "grafana.integreatly.org", "controllerKind": "Grafana", "Grafana": {"name":"test-cluster","namespace":"grafana"}, "namespace": "grafana", "name": "test-cluster", "reconcileID": "5aa39e3e-d5d3-47fc-848d-c3d15dfbcc3d", "stage": "deployment", "error": "Deployment.apps \"test-cluster-deployment\" is invalid: [spec.template.spec.containers[0].image: Required value, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Required value: can not be empty, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Invalid value: \"\": name part must be non-empty, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Invalid value: \"\": name part must consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyName',  or 'my.name',  or '123-abc', regex used for validation is '([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]')]"}
GRAFANA_LOGR_REGEX = r"^\s*"
GRAFANA_LOGR_REGEX += (
    r"(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}Z)"  # Group 1: timestamp
)
GRAFANA_LOGR_REGEX += r"\s+([A-Z]+)"  # Group 2: level
GRAFANA_LOGR_REGEX += r"\s+(\S+)"  # Group 3: Source
GRAFANA_LOGR_REGEX += r"\s+(.*?)"  # Group 4: Message
GRAFANA_LOGR_REGEX += r"\s*$"  # Take up any remaining whitespace

# Kafka log format
# 2025-01-24 22:52:03 WARN  AbstractConfiguration:93 - Reconciliation #27(watch) Kafka(acto-namespace/test-cluster): Configuration option "process.roles" is forbidden and will be ignored
KAFKA_LOG_REGEX = r"^\s*"
KAFKA_LOG_REGEX += (
    r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+"  # Group 1: timestamp
)
KAFKA_LOG_REGEX += r"(INFO|WARN|ERROR|DEBUG)\s+"  # Group 2: level
KAFKA_LOG_REGEX += r"(\S+):(\d+)\s+-"  # Group 3: Source
KAFKA_LOG_REGEX += r"\s+(.*?)$"  # Group 4: Message


def parse_log(line: str) -> dict:
    """Try to parse the log line with some predefined format

    Currently only support three formats:
    - klog
    - logr
    - json

    Returns:
        a dict containing 'level' and 'message'
        'level' will always be a lowercase string
    """
    logger = get_thread_logger(with_prefix=True)

    log_line = {}
    if re.search(KLOG_REGEX, line) is not None:
        # log is in klog format
        match = re.search(KLOG_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        if match.group(1) == "E":
            log_line["level"] = "error"
        elif match.group(1) == "I":
            log_line["level"] = "info"
        elif match.group(1) == "W":
            log_line["level"] = "warn"
        elif match.group(1) == "F":
            log_line["level"] = "fatal"

        log_line["msg"] = match.group(11)
    elif re.search(LOGR_REGEX, line) is not None:
        # log is in logr format
        match = re.search(LOGR_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        log_line["level"] = match.group(2).lower()
        log_line["msg"] = match.group(4)
    elif re.search(LOGR_SPECIAL_REGEX, line) is not None:
        # log is in logr special format
        match = re.search(LOGR_SPECIAL_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        log_line["level"] = match.group(2).lower()
        log_line["msg"] = match.group(4)
    elif re.search(LOGRUS_REGEX, line) is not None:
        # log is in logrus format
        match = re.search(LOGRUS_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        log_line["level"] = match.group(2)
        log_line["msg"] = match.group(3)
    elif re.search(GRAFANA_LOGR_REGEX, line) is not None:
        match = re.search(GRAFANA_LOGR_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        log_line["level"] = match.group(2).lower()
        log_line["msg"] = match.group(4)
    elif re.search(KAFKA_LOG_REGEX, line) is not None:
        match = re.search(KAFKA_LOG_REGEX, line)
        if match is None:
            logger.debug("parse_log() cannot parse line %s", line)
            return {}
        log_line["level"] = match.group(2).lower()
        log_line["msg"] = match.group(5)
    else:
        try:
            log_line = json.loads(line)
            if "level" not in log_line:
                log_line["level"] = log_line["severity"]

                del log_line["severity"]
            log_line["level"] = log_line["level"].lower()
        except Exception as e:
            logger.debug("parse_log() cannot parse line %s due to %s", line, e)

    return log_line


# if __name__ == "__main__":
# line = '  	Ports: []v1.ServicePort{'
# line = 'E0714 23:11:19.386396       1 pd_failover.go:70] PD failover replicas (0) reaches the limit (0), skip failover'
# line = '{"level":"error","ts":1655678404.9488907,"logger":"controller-runtime.injectors-warning","msg":"Injectors are deprecated, and will be removed in v0.10.x"}'

# line = 'time="2022-08-08T03:21:56Z" level=info msg="deployment updated" deployment=rfs-test-cluster namespace=acto-namespace service=k8s.deployment src="deployment.go:102"'
# print(LOGRUS_REGEX)
# print(parse_log(line)['msg'])

# with open("testrun-kafka-config/trial-00-0020/operator-002.log", "r") as f:
#     for line in f.readlines():
#         print(f"Parsing log: {line}")

#         if (
#             parse_log(line) == {}
#             or parse_log(line)["level"].lower() != "error"
#             and parse_log(line)["level"].lower() != "fatal"
#         ):
#             print(f"Test passed: {line} {parse_log(line)}")
#         else:
#             print(f"Message Raw: {line}, Parsed {parse_log(line)}")
#             break
