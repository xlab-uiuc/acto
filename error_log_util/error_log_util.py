# This file is used to collect all error logs from all operator log
# in one testrun, and then parse error logs using Drain to group them.

import os
import glob
from logparser import Drain
import sys
sys.path.append('../')
from acto.parse_log import parse_log

if __name__ == '__main__':
    testrun_dir = sys.argv[1]

    error_list = []
    for dirpath in glob.glob(os.path.join(testrun_dir, '*/operator-*.log')):
        with open(dirpath, 'r') as f:
            for line in f.readlines():
                log_line = parse_log(line)
                if 'level' in log_line and (log_line['level'] == 'error' or log_line['level'] == 'fatal'):
                    error_list.append(log_line['msg'])
                        
    with open(os.path.join(testrun_dir, 'error_logs.txt'), 'w') as f:
        for line in error_list:
            f.write(line + '\n')

    input_dir = testrun_dir # The input directory of log file
    output_dir = testrun_dir  # The output directory of parsing results
    log_file = 'error_logs.txt'  # The input log file name
    log_format = '<Content>'  # log format
    regex = []  # Regular expression list for optional preprocessing (default: [])
    st         = 0.5  # Similarity threshold
    depth      = 4  # Depth of all leaf nodes

    log_parser = Drain.LogParser(log_format, indir=input_dir, outdir=output_dir,  depth=depth, st=st, rex=regex)
    log_parser.parse(log_file)
