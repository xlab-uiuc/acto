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
        except Exception as e:
            print(e)
            pass
    
    return log_line


if __name__ == '__main__':
    # line = '  	Ports: []v1.ServicePort{'
    # line = 'E0714 23:11:19.386396       1 pd_failover.go:70] PD failover replicas (0) reaches the limit (0), skip failover'
    # line = '{"level":"error","ts":1655678404.9488907,"logger":"controller-runtime.injectors-warning","msg":"Injectors are deprecated, and will be removed in v0.10.x"}'
    with open ('testrun-2022-08-02-14-40/test-parse.log', 'r') as f:
        for line in f.readlines():
            if parse_log(line) == {} or parse_log(line)['level'] != 'error' and parse_log(line)['level'] != 'fatal':
                print('Test passed')
                print(parse_log(line))
            else:
                print("level:", parse_log(line)['level'])
                print("msg:", parse_log(line)['msg'])
                if 'error' in parse_log(line):
                    print('error:', parse_log(line)['error'])
