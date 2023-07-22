import argparse
import glob
import os
import pickle
from dataclasses import asdict
from typing import Tuple, List

import pandas as pd

from acto.checker.checker import OracleControlFlow, OracleResult
from acto.snapshot import Snapshot
from acto.runner.trial import Trial

parser = argparse.ArgumentParser(description='Automatic, Continuous Testing for k8s/openshift Operators')
parser.add_argument('--workdir',
                    dest='workdir_path',
                    type=str,
                    help='Working directory')
args = parser.parse_args()


def export_result_in_trial(trial: Trial, trial_name: str) -> Tuple[List[dict], List[dict]]:
    simple_results = []
    detailed_results = []
    for (gen, (_, exception_or_snapshot_plus_oracle_result)) in enumerate(trial.history_iterator()):
        simple = {
            'id': trial_name,
            'generation': gen
        }
        detailed = {
            'id': trial_name,
            'generation': gen
        }
        if isinstance(exception_or_snapshot_plus_oracle_result, Exception):
            # the error is caused by faulty Acto implementation
            simple['acto_impl_exception'] = OracleControlFlow.terminate
            detailed['acto_impl_exception'] = str(exception_or_snapshot_plus_oracle_result)
        else:
            exception_or_snapshot_plus_oracle_result: (Snapshot, List[OracleResult])
            (_, oracle_results) = exception_or_snapshot_plus_oracle_result
            for result in oracle_results:
                simple[result.emit_by] = ','.join(result.all_meanings())
                detailed[result.emit_by] = asdict(result)
        simple_results.append(simple)
        detailed_results.append(detailed)
    return simple_results, detailed_results


trial_paths = glob.glob(os.path.join(args.workdir_path, '**', 'trial.pkl'))
common_prefix = trial_paths[0][trial_paths[0].find('trial-'):] if len(trial_paths) == 1 else os.path.commonpath(trial_paths)+os.path.sep
all_simple_results = []
all_detailed_results = []
for trial_path in trial_paths:
    trial_name = trial_path[len(common_prefix):][:-len('/trial.pkl')]
    trial_simple_results, trial_detailed_results = export_result_in_trial(pickle.load(open(trial_path, 'rb')), trial_name)
    all_simple_results += trial_simple_results
    all_detailed_results += trial_detailed_results

simple_df = pd.DataFrame(all_simple_results)
detailed_df = pd.DataFrame(all_detailed_results)
simple_df.to_csv(os.path.join(args.workdir_path, 'simple.csv'))
detailed_df.to_csv(os.path.join(args.workdir_path, 'detailed.csv'))
