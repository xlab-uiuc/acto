import json
import re

klog_regex = r'^\s*'
klog_regex += r'(\w)'  # group 1: level
klog_regex += r'(\d{2})(\d{2})\s(\d{2}):(\d{2}):(\d{2})\.(\d{6})' # group 2-7: timestamp
klog_regex += r'\s+'
klog_regex += r'(\d+)'  # group 8
klog_regex += r'\s'
klog_regex += r'(.+):'  # group 9: filename
klog_regex += r'(\d+)'  # group 10: lineno
klog_regex += r'\]\s'
klog_regex += r'(.*?)'  # group 11: message
klog_regex += r'\s*$'

logr_regex = r'^\s*'
logr_regex += r'(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)'  # group 1: timestamp
logr_regex += r'\s+([A-Z]+)'  # group 2: level
logr_regex += r'\s+(\S+)'  # group 3: source
logr_regex += r'\s+(.*?)'  # group 4: message
logr_regex += r'\s*$'


def parse_log(line: str) -> dict:
    '''Try to parse the log line with some predefined format

    Currently only support three formats:
    - klog
    - logr
    - json
    
    Returns:
        a dict containing 'level' and 'message'
    '''
    log_line = {}
    if re.search(klog_regex, line) != None:
        # log is in klog format
        match = re.search(klog_regex, line)
        if match.group(1) == 'E':
            log_line['level'] = 'error'
        elif match.group(1) == 'I':
            log_line['level'] = 'info'
        elif match.group(1) == 'W':
            log_line['level'] = 'warn'
        elif match.group(1) == 'F':
            log_line['level'] = 'fatal'
        
        log_line['msg'] = match.group(11)
    elif re.search(logr_regex, line) != None:
        # log is in logr format
        match = re.search(logr_regex, line)
        log_line['level'] = match.group(2).lower()
        log_line['msg'] = match.group(4)
    else:
        try:
            log_line = json.loads(line)
        except:
            pass
    
    return log_line


if __name__ == '__main__':
    # line = '  	Ports: []v1.ServicePort{'
    # line = 'E0714 23:11:19.386396       1 pd_failover.go:70] PD failover replicas (0) reaches the limit (0), skip failover'
    line = 'E0624 08:02:40.303209       1 tidb_cluster_control.go:129] tidb cluster acto-namespace/test-cluster is not valid and must be fixed first, aggregated error: [spec.tikv.env[0].valueFrom.fieldRef: Invalid value: "": fieldRef is not supported, spec.tikv.env[0].valueFrom: Invalid value: "": may not have more than one field specified at a time]'
    # line = '{"level":"error","ts":1655678404.9488907,"logger":"controller-runtime.injectors-warning","msg":"Injectors are deprecated, and will be removed in v0.10.x"}'
    if parse_log(line) == {} or parse_log(line)['level'] != 'error' and parse_log(line)['level'] != 'fatal':
        print('Test passed')
    else:
        print("level:", parse_log(line)['level'])
        print("msg:", parse_log(line)['msg'])
    # log_filepath = '/home/kunle/acto/testrun/testrun-tidb-1/trial-01-0532/operator-1.log'
    # with open(log_filepath, 'r') as log_file:
    #     line = log_file.readline()
    #     print(parse_log(line)['level'])
        # for line in log_file:
        #     if re.search(klog_regex, line) != None:
        #         # log is in klog format
        #         match = re.search(klog_regex, line)
        #         log_line = {}
                
        #         if match.group(1) == 'E':
        #             log_line['level'] = 'error'
        #         elif match.group(1) == 'I':
        #             log_line['level'] = 'info'
        #         elif match.group(1) == 'W':
        #             log_line['level'] = 'warn'
        #         elif match.group(1) == 'F':
        #             log_line['level'] = 'fatal'
                
        #         log_line['message'] = match.group(10)
        #     elif re.search(logr_regex, line) != None:
        #         # log is in logr format
        #         match = re.search(logr_regex, line)

        #         log_line = {}

        #         log_line['level'] = match.group(2).lower()
        #         log_line['message'] = match.group(4)
        #     else:
        #         try:
        #             log_line = json.loads(line)
        #         except:
        #             continue

        #     print(log_line['level'])