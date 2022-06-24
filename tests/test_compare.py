import unittest
import sys

sys.path.append('..')
from compare import CompareMethods


class TestCompare(unittest.TestCase):

    def test_compare_substring(self):
        compare = CompareMethods()

        testcases = [
            [
                None, 'kcaqbdpkpt',
                '4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=2\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=65536\nsnapCount=10000\ncommitLogCount=500\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=4000\nmaxSessionTimeout=40000\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=1\nquorumListenOnAllIPs=false\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n',
                'apqwpwxmlo=kcaqbdpkpt\n4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=4\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=2\nsnapCount=5\ncommitLogCount=2\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=5\nmaxSessionTimeout=5\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=5\nquorumListenOnAllIPs=true\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n'
            ],
        ]
        for case in testcases:
            self.assertTrue(compare.compare(case[0], case[1], case[2], case[3]))

    def test_compare_config(self):
        compare = CompareMethods()

        testcases = [
            [
                'cluster_partition_handling = pause_minority\nvm_memory_high_watermark_paging_ratio = 0.99\ndisk_free_limit.relative = 1.0\ncollect_statistics_interval = 10000\n',
                'total_memory_available_override_value = 3435973837\ncluster_partition_handling            = pause_minority\nvm_memory_high_watermark_paging_ratio = 0.99\ndisk_free_limit.relative              = 1.0\ncollect_statistics_interval           = 10000\n'
            ],
        ]
        for case in testcases:
            self.assertTrue(compare.config_operator(case[0], case[1]))

        not_match_testcases = [
            ['vasdfsdf', 'asdfasdf'],
            ['cluster_partition_handling = pause_minority', 'total_memory_available_override_value = 3435973837'],
            ['total_memory_available_override_value = 3435973837', None]
        ]
        for case in not_match_testcases:
            self.assertFalse(compare.config_operator(case[0], case[1]))

if __name__ == '__main__':
    unittest.main()