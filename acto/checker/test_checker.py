import importlib
import json
import logging
import sys

from acto.checker.checker_set import CheckerSet
from acto.common import RunResult, RecoveryResult, ErrorResult, Oracle
from acto.input import InputModel
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot

if __name__ == "__main__":
    import argparse
    import glob
    import multiprocessing
    import os
    import queue
    import traceback
    from types import SimpleNamespace

    import pandas
    import yaml

    def checker_save_result(trial_dir: str, original_result: dict, runResult: RunResult,
                            alarm: bool, mode: str):

        result_dict = {}
        result_dict['alarm'] = alarm
        result_dict['original_result'] = original_result
        post_result = {}
        result_dict['post_result'] = post_result
        try:
            trial_num = '-'.join(trial_dir.split('-')[-2:])
            post_result['trial_num'] = trial_num + '-%d' % runResult.generation
        except:
            post_result['trial_num'] = trial_dir
        post_result['error'] = runResult.to_dict()
        result_path = os.path.join(trial_dir,
                                   'post-result-%d-%s.json' % (runResult.generation, mode))
        with open(result_path, 'w') as result_file:
            json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)

    def check_trial_worker(workqueue: multiprocessing.Queue, checker_class: type,
                           num_system_fields_list: multiprocessing.Array,
                           num_delta_fields_list: multiprocessing.Array, mode: str):
        while True:
            try:
                trial_dir = workqueue.get(block=False)
            except queue.Empty:
                break

            print(trial_dir)
            if not os.path.isdir(trial_dir):
                continue
            original_result_path = "%s/result.json" % (trial_dir)
            with open(original_result_path, 'r') as original_result_file:
                original_result = json.load(original_result_file)

            input_model = InputModel(context['crd']['body'], [], config.example_dir, 1, 1, [])

            module = importlib.import_module(config.k8s_fields)

            for k8s_field in module.WHITEBOX:
                input_model.apply_k8s_schema(k8s_field)

            if 'analysis_result' in context and 'default_value_map' in context['analysis_result']:
                input_model.apply_default_value(context['analysis_result']['default_value_map'])

            checker: CheckerSet = checker_class(context=context,
                                             trial_dir=trial_dir,
                                             input_model=input_model)
            snapshots = []
            snapshots.append(Snapshot(seed))

            alarm = False
            for generation in range(0, 20):
                mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
                operator_log_path = "%s/operator-%d.log" % (trial_dir, generation)
                system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
                events_log_path = "%s/events-%d.json" % (trial_dir, generation)
                cli_output_path = "%s/cli-output-%d.log" % (trial_dir, generation)
                runtime_result_path = "%s/generation-%d-runtime.json" % (trial_dir, generation)

                if not os.path.exists(mutated_filename):
                    break

                if not os.path.exists(operator_log_path):
                    continue

                with open(mutated_filename, 'r') as input_file, \
                        open(operator_log_path, 'r') as operator_log, \
                        open(system_state_path, 'r') as system_state, \
                        open(cli_output_path, 'r') as cli_output, \
                        open(runtime_result_path, 'r') as runtime_result_file:
                    # open(events_log_path, 'r') as events_log, \
                    input = yaml.load(input_file, Loader=yaml.FullLoader)
                    cli_result = json.load(cli_output)
                    logging.info(cli_result)
                    system_state = json.load(system_state)
                    runtime_result = json.load(runtime_result_file)
                    operator_log = operator_log.read().splitlines()
                    snapshot = Snapshot(input, cli_result, system_state, operator_log)

                    prev_snapshot = snapshots[-1]
                    runResult = checker.check(snapshot=snapshot,
                                              prev_snapshot=prev_snapshot,
                                              revert=runtime_result['revert'],
                                              generation=generation,
                                              testcase_signature=runtime_result['testcase'])
                    snapshots.append(snapshot)

                    if runtime_result['recovery_result'] != None and runtime_result[
                        'recovery_result'] != 'Pass':
                        runResult.recovery_result = RecoveryResult(
                            runtime_result['delta', runtime_result['from'], runtime_result['to']])

                    if runtime_result['custom_result'] != None and runtime_result[
                        'custom_result'] != 'Pass':
                        runResult.custom_result = ErrorResult(
                            Oracle.CUSTOM, runtime_result['custom_result']['message'])

                    if runResult.is_connection_refused():
                        logging.debug('Connection refused')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_basic_error():
                        logging.debug('Basic error')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, True, mode)
                        continue
                    is_invalid, _ = runResult.is_invalid()
                    if is_invalid:
                        logging.debug('Invalid')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_unchanged():
                        logging.debug('Unchanged')
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_error():
                        logging.info('%s reports an alarm' % system_state_path)
                        checker_save_result(trial_dir, runtime_result, runResult, True, mode)
                        alarm = True
                    else:
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)

                    # TODO: migrate count_num_fields to checker.py
                    num_fields_tuple = checker.count_num_fields(snapshot=snapshot,
                                                                prev_snapshot=prev_snapshot)
                    if num_fields_tuple != None:
                        num_system_fields, num_delta_fields = num_fields_tuple
                        num_system_fields_list.append(num_system_fields)
                        num_delta_fields_list.append(num_delta_fields)

            if not alarm:
                logging.info('%s does not report an alarm' % system_state_path)

    parser = argparse.ArgumentParser(description='Standalone checker for Acto')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)
    parser.add_argument('--config', help='Path to config file', required=True)
    parser.add_argument('--num-workers', help='Number of workers', type=int, default=4)
    parser.add_argument('--blackbox', dest='blackbox', help='Blackbox mode', action='store_true')
    # parser.add_argument('--output', help='Path to output file', required=True)

    args = parser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
    testrun_dir = args.testrun_dir
    context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')

    logging.basicConfig(
        filename=os.path.join('.', testrun_dir, 'checker_test.log'),
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(asctime)s %(threadName)-11s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s'
    )

    def handle_excepthook(type, message, stack):
        '''Custom exception handler

        Print detailed stack information with local variables
        '''
        if issubclass(type, KeyboardInterrupt):
            sys.__excepthook__(type, message, stack)
            return

        stack_info = traceback.StackSummary.extract(traceback.walk_tb(stack),
                                                    capture_locals=True).format()
        logging.critical(f'An exception occured: {type}: {message}.')
        for i in stack_info:
            logging.critical(i.encode().decode('unicode-escape'))
        return

    sys.excepthook = handle_excepthook

    trial_dirs = glob.glob(testrun_dir + '/trial-??-????')
    with open(context_cache, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])

    context['enable_analysis'] = True

    if 'enable_analysis' in context and context['enable_analysis'] == True:
        logging.info('Analysis is enabled')
        for path in context['analysis_result']['control_flow_fields']:
            path.pop(0)
    else:
        context['enable_analysis'] = False

    with open(config.seed_custom_resource, 'r') as seed_file:
        seed = yaml.load(seed_file, Loader=yaml.FullLoader)

    checker_class = CheckerSet

    mp_manager = multiprocessing.Manager()

    num_system_fields_list = mp_manager.list()
    num_delta_fields_list = mp_manager.list()

    workqueue = multiprocessing.Queue()
    for trial_dir in sorted(trial_dirs):
        workqueue.put(trial_dir)

    workers = [
        multiprocessing.Process(target=check_trial_worker,
                                args=(workqueue, checker_class, num_system_fields_list,
                                      num_delta_fields_list, 'all'))
        for _ in range(args.num_workers)
    ]

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join()

    num_system_fields_df = pandas.Series(list(num_system_fields_list))
    num_delta_fields_df = pandas.Series(list(num_delta_fields_list))
    logging.info(
        'Number of system fields: max[%s] min[%s] mean[%s]' %
        (num_system_fields_df.max(), num_system_fields_df.min(), num_system_fields_df.mean()))
    logging.info(
        'Number of delta fields: max[%s] min[%s] mean[%s]' %
        (num_delta_fields_df.max(), num_delta_fields_df.min(), num_delta_fields_df.mean()))