import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from subprocess import CompletedProcess
from typing import Callable, List, Optional

import kubernetes
from kubernetes.client import CoreV1EventList

from acto.checker.checker import OracleControlFlow
from acto.checker.impl.health import HealthChecker
from acto.kubectl_client import KubectlClient
from acto.kubectl_client.collector import Collector
from acto.runner.ray_runner import Runner
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
            self.kubectl_collector = Collector(self.namespace, kubectl_client, self.crd_meta_info)


def with_context(ctx: CollectorContext, collector: Callable[[CollectorContext, Runner, Trial, dict], Snapshot]) -> Callable[[Runner, Trial, dict], Snapshot]:
    @wraps(collector)
    def wrapper(runner: Runner, trial: Trial, system_input: dict) -> Snapshot:
        ctx.set_collector_if_none(runner.kubectl_client)
        return collector(ctx, runner, trial, system_input)

    return wrapper


def apply_system_input_and_wait(ctx: CollectorContext, runner: Runner, system_input: dict) -> CompletedProcess:
    cli_result = runner.kubectl_client.apply(system_input, namespace=ctx.namespace)
    if cli_result.returncode != 0:
        logging.error(f'Failed to apply system input to namespace {ctx.namespace}.\n{system_input}')
        raise RuntimeError(f'Failed to apply system input to namespace {ctx.namespace}.\n{system_input}')
    asyncio.run(wait_for_system_converge(ctx.kubectl_collector, ctx.timeout))
    return cli_result


def snapshot_collector(ctx: CollectorContext, runner: Runner, trial: Trial, system_input: dict) -> Snapshot:
    cli_result = apply_system_input_and_wait(ctx, runner, system_input)

    cli_result = {
        "stdout": cli_result.stdout.strip(),
        "stderr": cli_result.stderr.strip(),
    }

    asyncio.run(wait_for_system_converge(ctx.kubectl_collector, ctx.timeout))

    system_state = ctx.kubectl_collector.collect_system_state()
    operator_log = ctx.kubectl_collector.collect_operator_log()
    events = ctx.kubectl_collector.collect_events()
    not_ready_pods_logs = ctx.kubectl_collector.collect_not_ready_pods_logs()

    return Snapshot(input=system_input, system_state=system_state,
                    operator_log=operator_log, cli_result=cli_result,
                    events=events, not_ready_pods_logs=not_ready_pods_logs,
                    generation=trial.generation, trial_state=trial.state)


async def wait_until_no_future_events(core_api: kubernetes.client.CoreV1Api, namespace: str, timeout: int):
    """
    Wait until no events are generated for the given namespace for the given timeout.
    @param core_api: kubernetes api client, CoreV1Api
    @param namespace: kubernetes namespace
    @param timeout: timeout in seconds
    @return:
    """
    while True:
        events: CoreV1EventList = core_api.list_namespaced_event(namespace)
        events_last_time: List[datetime] = [event.last_timestamp for event in events.items]
        if not events_last_time:
            return True
        max_time: datetime = max(events_last_time)
        # check how much time has passed since the last event
        time_since_last_event = datetime.now() - max_time
        if time_since_last_event.total_seconds() > timeout:
            return True
        await asyncio.sleep((timedelta(seconds=timeout) - time_since_last_event).total_seconds())


async def wait_for_system_converge(collector: Collector, no_events_threshold: int, hard_timeout=480):
    futures = [
        asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, collector.namespace, no_events_threshold)),
        asyncio.create_task(asyncio.sleep(hard_timeout, result=False))
    ]

    await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)


async def wait_for_system_converge_expect_more_events(collector: Collector, no_events_threshold: int, hard_timeout=480) -> bool:
    futures = [
        asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, collector.namespace, no_events_threshold)),
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
        futures = pending_futures + [asyncio.create_task(wait_until_no_future_events(collector.coreV1Api, collector.namespace, no_events_threshold))]
