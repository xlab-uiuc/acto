import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Optional

import kubernetes
from kubernetes.client import CoreV1EventList, CoreV1Event

from acto.checker.checker import OracleControlFlow
from acto.checker.impl.health import HealthChecker
from acto.kubectl_client import KubectlClient
from acto.kubectl_client.collector import Collector
from acto.runner.runner import Runner
from acto.runner.trial import Trial
from acto.snapshot import Snapshot


@dataclass
class CollectorContext:
    namespace: Optional[str] = None
    timeout: int = 45
    crd_meta_info: Optional[dict] = None
    kubectl_collector: Optional[Collector] = None

    def set_collector_if_none(self, kubectl_client: KubectlClient):
        if self.kubectl_collector is None:
            # TODO: also add kubernetes client
            self.kubectl_collector = Collector(self.namespace, kubectl_client, self.crd_meta_info)


def with_context(ctx: CollectorContext, collector):
    # Todo: Fix type hints
    @wraps(collector)
    def wrapper(runner: Runner, *args, **kwargs) -> Snapshot:
        ctx.set_collector_if_none(runner.kubectl_client)
        return collector(ctx, runner, *args, **kwargs)

    return wrapper


def snapshot_collector(ctx: CollectorContext, runner: Runner, trial: Trial, system_input: dict, ignore_cli_error=False) -> Snapshot:
    '''Snapshot collector is responsible for applying the system_input and collecting the snapshot
    '''
    cli_result = runner.kubectl_client.apply(system_input, namespace=ctx.namespace)
    if cli_result.returncode != 0 and not ignore_cli_error:
        logging.error(f'Failed to apply system input to namespace {ctx.namespace}.\n{system_input}')

    skip_waiting_for_converge = cli_result.returncode != 0 and not ignore_cli_error

    cli_result = {
        "stdout": "" if cli_result.stdout is None else cli_result.stdout.strip(),
        "stderr": "" if cli_result.stderr is None else cli_result.stderr.strip(),
    }

    if not skip_waiting_for_converge:
        asyncio.run(wait_for_system_converge(ctx.kubectl_collector, ctx.timeout))

    system_state = ctx.kubectl_collector.collect_system_state()
    operator_log = ctx.kubectl_collector.collect_operator_log()
    events = ctx.kubectl_collector.collect_events()
    not_ready_pods_logs = ctx.kubectl_collector.collect_not_ready_pods_logs()

    return Snapshot(input=system_input, system_state=system_state,
                    operator_log=operator_log, cli_result=cli_result,
                    events=events, not_ready_pods_logs=not_ready_pods_logs,
                    generation=trial.generation, trial_state=trial.state)


def extract_event_time(event: CoreV1Event) -> Optional[datetime]:
    if event.event_time is not None:
        return event.event_time
    if event.last_timestamp is not None:
        return event.last_timestamp
    logging.warning(f'event {event} does not have a time')
    return None


async def wait_until_no_future_events(core_api: kubernetes.client.CoreV1Api, timeout: int):
    """
    Wait until no events are generated for the given namespace for the given timeout.
    @param core_api: kubernetes api client, CoreV1Api
    @param timeout: timeout in seconds
    @return:
    """
    await asyncio.sleep(timeout / 2)
    while True:
        events: CoreV1EventList = core_api.list_event_for_all_namespaces()
        events_last_time: List[datetime] = [extract_event_time(event) for event in events.items]
        events_last_time = list(filter(None, events_last_time))
        if not events_last_time:
            return True
        max_time: datetime = max(events_last_time)
        # check how much time has passed since the last event
        time_since_last_event = datetime.now(tz=max_time.tzinfo) - max_time
        if time_since_last_event.total_seconds() > timeout:
            return True
        await asyncio.sleep((timedelta(seconds=timeout) - time_since_last_event).total_seconds())


async def wait_for_system_converge(collector: Collector, no_events_threshold: int, hard_timeout=480):
    futures = [
        asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, no_events_threshold)),
        asyncio.create_task(asyncio.sleep(hard_timeout, result=False))
    ]

    await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)


async def wait_for_system_converge_expect_more_events(collector: Collector, no_events_threshold: int, hard_timeout=480) -> bool:
    futures = [
        asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, no_events_threshold)),
        asyncio.create_task(asyncio.sleep(hard_timeout, result=False))
    ]

    while True:
        [no_future_events], pending_futures = await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)
        if not no_future_events.result():
            # hard timeout
            return False
        system_state = collector.collect_system_state()
        health_result = HealthChecker().check(Snapshot(system_state=system_state), Snapshot())
        if health_result.means(OracleControlFlow.ok):
            return True
        # TODO: if the system is not healthy, but we have no events, do we need to wait more?
        futures = pending_futures + [asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, no_events_threshold))]
