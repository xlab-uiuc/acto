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
    if re.search(klog_regex, line) != None:
        # log is in klog format
        match = re.search(klog_regex, line)
        log_line = {}
        
        if match.group(1) == 'E':
            log_line['level'] = 'error'
        elif match.group(1) == 'I':
            log_line['level'] = 'info'
        elif match.group(1) == 'W':
            log_line['level'] = 'warn'
        elif match.group(1) == 'F':
            log_line['level'] = 'fatal'
        
        log_line['message'] = match.group(11)
    elif re.search(logr_regex, line) != None:
        # log is in logr format
        match = re.search(logr_regex, line)

        log_line = {}

        log_line['level'] = match.group(2).lower()
        log_line['message'] = match.group(4)
    else:
        try:
            log_line = json.loads(line)
        except:
            pass
    
    return log_line


if __name__ == '__main__':
    log_filepath = 'testrun-2022-06-29-23-59/trial-00-0003/operator-2.log'

    with open(log_filepath, 'r') as log_file:
        for line in log_file:
            if re.search(klog_regex, line) != None:
                # log is in klog format
                match = re.search(klog_regex, line)
                log_line = {}
                
                if match.group(1) == 'E':
                    log_line['level'] = 'error'
                elif match.group(1) == 'I':
                    log_line['level'] = 'info'
                elif match.group(1) == 'W':
                    log_line['level'] = 'warn'
                elif match.group(1) == 'F':
                    log_line['level'] = 'fatal'
                
                log_line['message'] = match.group(10)
            elif re.search(logr_regex, line) != None:
                # log is in logr format
                match = re.search(logr_regex, line)

                log_line = {}

                log_line['level'] = match.group(2).lower()
                log_line['message'] = match.group(4)
            else:
                try:
                    log_line = json.loads(line)
                except:
                    continue

            print(log_line['message'])