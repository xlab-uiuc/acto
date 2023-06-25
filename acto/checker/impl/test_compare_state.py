import pytest

from acto.checker.impl.compare_state import is_nullish, CompareMethods


@pytest.mark.parametrize(
    ("value", "expected_value"),
    [
        (None, True),
        (0, True),
        (0.0, True),
        ("", True),
        ([], True),
        ({}, True),
        pytest.param(False, False, marks=pytest.mark.xfail(reason="Not sure about the right answer here")),
        (True, False),
        (1, False),
        (1.0, False),
        ("a", False),
        ([1], False),
        ({"a": 1}, False)
    ]
)
def test_is_nullish(value, expected_value):
    assert is_nullish(value) == expected_value


@pytest.mark.parametrize("value", [
    [
        None, 'kcaqbdpkpt',
        '4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=2\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=65536\nsnapCount=10000\ncommitLogCount=500\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=4000\nmaxSessionTimeout=40000\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=1\nquorumListenOnAllIPs=false\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n',
        'apqwpwxmlo=kcaqbdpkpt\n4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=4\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=2\nsnapCount=5\ncommitLogCount=2\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=5\nmaxSessionTimeout=5\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=5\nquorumListenOnAllIPs=true\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n'
    ],
    [
        'cluster_partition_handling = pause_minority\nvm_memory_high_watermark_paging_ratio = 0.99\ndisk_free_limit.relative = 1.0\ncollect_statistics_interval = 10000\n',
        None,
        'total_memory_available_override_value = 3435973837\ncluster_partition_handling            = pause_minority\nvm_memory_high_watermark_paging_ratio = 0.99\ndisk_free_limit.relative              = 1.0\ncollect_statistics_interval           = 10000\n',
        None
    ],
    [
        None, "-.4272625998Mi",
        None, "-448017308m"
    ],
    [
        None, 10,
        None, 1000
    ],  # this case is used to test substring matching
    [
        None, '.1571549',
        None, '158m'
    ]])
def test_compare_methods(value):
    c = CompareMethods(enable_k8s_value_canonicalization=True)
    assert c.equals_after_transform(value[0], value[1], value[2], value[3])
