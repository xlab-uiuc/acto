from deepdiff.helper import NotPresent
import configparser

from k8s_util.k8sutil import canonicalizeQuantity
from thread_logger import get_thread_logger
from common import FeatureGate


class CompareMethods:

    def __init__(self, feature_gate: FeatureGate):
        self.custom_operators = []
        self.feature_gate = feature_gate
        if feature_gate.canonicalization_enabled():
            self.custom_operators.extend([self.substring_operator, self.config_operator])

    def operator(self, input, output) -> bool:
        '''Operator here means binary comparison "==" operator'''
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
        else:
            if isinstance(input, str) and input == '':
                return True
            elif isinstance(output, str) and output == '':
                return True
            elif isinstance(input, int) and input == 0:
                return True
            elif isinstance(output, int) and output == 0:
                return True
            elif isinstance(input, float) and input == 0:
                return True
            elif isinstance(output, float) and output == 0:
                return True
            elif isinstance(input, list) and len(input) == 0:
                return True
            elif isinstance(output, list) and len(output) == 0:
                return True
            elif isinstance(input, dict) and len(input) == 0:
                return True
            elif isinstance(output, dict) and len(output) == 0:
                return True

        return False


    def substring_operator(self, input, output) -> bool:
        # if input is int, then we want exact match to avoid mapping 10 to 1000, 2 to 20, etc.
        if type(input) == int and input == output:
            return True
        elif str(input).lower() in str(output).lower():
            return True

    def config_operator(self, input, output) -> bool:
        logger = get_thread_logger(with_prefix=True)

        if isinstance(input, str) and isinstance(output, str):
            try:
                inputparser = configparser.ConfigParser()
                inputparser.read_string("[ACTO]\n" + input)
                if len(inputparser.options("ACTO")) == 0:
                    return False

                outputparser = configparser.ConfigParser()
                outputparser.read_string("[ACTO]\n" + output)

                for k, v in inputparser.items("ACTO"):
                    logger.debug(f"{k} - {v}")
                    if outputparser.get("ACTO", k) != v:
                        return False
                logger.info('Equal through config operator')
                return True
            except configparser.Error as e:
                return False
        else:
            return False

    def compare(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        # parse the argument: if a number, convert it to pure decimal format (i.e. 1e3 -> 1000); otherwise unchanged
        in_prev, in_curr, out_prev, out_curr = self.transform_field_value(
            in_prev, in_curr, out_prev, out_curr)

        # try every compare method possible
        if self.operator(in_prev, out_prev) and self.operator(in_curr, out_curr):
            return True
        elif self.none_notpresent_operator(in_prev, out_prev) \
                and self.operator(in_curr, out_curr):
            return True
        elif self.operator(in_prev, out_prev) \
                and self.none_notpresent_operator(in_curr, out_curr):
            return True
        else:
            return False

    def input_compare(self, prev, curr) -> bool:
        if prev is None:
            return True
        elif isinstance(prev, NotPresent):
            return True

        if prev == curr:
            return True
        elif prev == None and isinstance(curr, NotPresent):
            return True
        elif isinstance(prev, NotPresent) and curr == None:
            return True
        else:
            if isinstance(prev, str) and prev == '':
                if curr == None or isinstance(curr, NotPresent):
                    return True
            elif isinstance(curr, str) and curr == '':
                if prev == None or isinstance(prev, NotPresent):
                    return True
            elif isinstance(prev, int) and prev == 0:
                if curr == None or isinstance(curr, NotPresent):
                    return True
            elif isinstance(curr, int) and curr == 0:
                if prev == None or isinstance(prev, NotPresent):
                    return True
            elif isinstance(prev, float) and prev == 0:
                if curr == None or isinstance(curr, NotPresent):
                    return True
            elif isinstance(curr, float) and curr == 0:
                if prev == None or isinstance(prev, NotPresent):
                    return True
            elif isinstance(prev, list) and len(prev) == 0:
                if curr == None or isinstance(curr, NotPresent):
                    return True
            elif isinstance(curr, list) and len(curr) == 0:
                if prev == None or isinstance(prev, NotPresent):
                    return True
            elif isinstance(prev, dict) and len(prev) == 0:
                if curr == None or isinstance(curr, NotPresent):
                    return True
            elif isinstance(curr, dict) and len(curr) == 0:
                if prev == None or isinstance(prev, NotPresent):
                    return True
            return False

    def transform_field_value(self, in_prev, in_curr, out_prev, out_curr):
        '''transform the field value if necessary
            only one transformer is allowed for each field
        '''
        if self.feature_gate.canonicalization_enabled():
            # transform method 1: convert Quantity to unified unit
            new_in_prev = canonicalizeQuantity(in_prev)
            new_in_curr = canonicalizeQuantity(in_curr)
            new_out_prev = canonicalizeQuantity(out_prev)
            new_out_curr = canonicalizeQuantity(out_curr)

            if not (new_in_curr == in_curr and new_in_prev == in_prev and
                    new_out_curr == out_curr and new_out_prev == out_prev):
                # field values has been changed using canonicalizeQuantity
                return new_in_prev, new_in_curr, new_out_prev, new_out_curr

        # default: return original values
        return in_prev, in_curr, out_prev, out_curr


if __name__ == '__main__':
    testcases = [
        # [
        #     None, 'kcaqbdpkpt',
        #     '4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=2\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=65536\nsnapCount=10000\ncommitLogCount=500\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=4000\nmaxSessionTimeout=40000\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=1\nquorumListenOnAllIPs=false\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n',
        #     'apqwpwxmlo=kcaqbdpkpt\n4lw.commands.whitelist=cons, envi, conf, crst, srvr, stat, mntr, ruok\ndataDir=/data\nstandaloneEnabled=false\nreconfigEnabled=true\nskipACL=yes\nmetricsProvider.className=org.apache.zookeeper.metrics.prometheus.PrometheusMetricsProvider\nmetricsProvider.httpPort=7000\nmetricsProvider.exportJvmInfo=true\ninitLimit=10\nsyncLimit=4\ntickTime=2000\nglobalOutstandingLimit=1000\npreAllocSize=2\nsnapCount=5\ncommitLogCount=2\nsnapSizeLimitInKb=4194304\nmaxCnxns=0\nmaxClientCnxns=60\nminSessionTimeout=5\nmaxSessionTimeout=5\nautopurge.snapRetainCount=3\nautopurge.purgeInterval=5\nquorumListenOnAllIPs=true\nadmin.serverPort=8080\ndynamicConfigFile=/data/zoo.cfg.dynamic\n'
        # ],
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
        ]

    ]
    compare = CompareMethods()

    for case in testcases:
        assert (compare.compare(case[0], case[1], case[2], case[3]))
