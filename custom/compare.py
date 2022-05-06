from deepdiff.helper import NotPresent


class CompareMethods:

    def __init__(self):
        # self.method_list = \
        #     [a for a in dir(self) if not a.startswith('__') and a != "compare" and callable(getattr(self, a))]
        self.custom_operators = [
            self.none_notpresent_operator, self.substring_operator
        ]

    # def __iter__(self):
    #     # make the defined methods iterable
    #     for method in self.method_list:
    #         yield getattr(self, method)

    def operator(self, input, output) -> bool:
        if input == output:
            return True
        else:
            for op in self.custom_operators:
                if op(input, output):
                    return True
            return False

    def none_notpresent_operator(self, input, output) -> bool:
        # None and NotPresent are wildcards
        if input == None or output == None:
            return True
        elif isinstance(input, NotPresent) or isinstance(output, NotPresent):
            return True

    def substring_operator(self, input, output) -> bool:
        if str(input) in str(output):
            return True

    def compare(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        # try every compare method possible
        if self.operator(in_prev, out_prev) and self.operator(
                in_curr, out_curr):
            return True
        else:
            return False


if __name__ == '__main__':
    testcases = [
        [
            None, 'kcaqbdpkpt',
            '4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=2\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=65536\nsnapCount=10000\ncommitLogCount=500\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=4000\nmaxSessionTimeout=40000\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=1\nquorumListenOnAllIPs=false\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n',
            'apqwpwxmlo=kcaqbdpkpt\n4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=4\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=2\nsnapCount=5\ncommitLogCount=2\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=5\nmaxSessionTimeout=5\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=5\nquorumListenOnAllIPs=true\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n'
        ],
    ]
    compare = CompareMethods()

    for case in testcases:
        assert (compare.compare(case[0], case[1], case[2], case[3]))
