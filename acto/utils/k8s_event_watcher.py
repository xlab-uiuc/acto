"""determines whether cluster is stuck in an unhealthy state through interpreting K8s events"""
import json
import multiprocessing
from acto.utils.thread_logger import get_thread_logger
from typing import Callable, Optional
import copy


class Predicate():
    def __init__(self, reason: str, message_filter: Callable[[Optional[str]], bool] = lambda x: True, threshold: Optional[int] = None) -> None:
        self.reason = reason
        self.message_filter = message_filter    # event count threshold for deciding an abort
        self.threshold = threshold

    def match(self, reason: str, message: str = ""):
        return self.reason == reason and self.message_filter(message)
    
    def __str__(self) -> str:
        return "(reason: {}, count_threshold: {})".format(self.reason, self.threshold)
    
    
#todo: unify this with other Acto configs
k8s_event_watcher_config = {
    "default_threshold": 3,
    "abort_predicates": [
        # a full list of kubelet emitted reason can be found at https://github.com/kubernetes/kubernetes/blob/master/pkg/kubelet/events/event.go
        # event reason emitted by K8s controllers however, needs a scan from source code unfortunately

        #kublet reasons, todo: add fine-calibrated message filters
        Predicate("Failed"),
        Predicate("BackOff", threshold=5),
        Predicate("FailedCreatePodContainer"),
        Predicate("ErrImageNeverPull"), 
        Predicate("FailedAttachVolume"), 
        Predicate("FailedMount"), 
        Predicate("VolumeResizeFailed"), 
        Predicate("FileSystemResizeFailed"), 
        Predicate("FailedMapVolume"),

        # it is possible that scheduling fails due to node.kubernetes.io/not-ready
        # which should be transient. We need to filter for truly alarming ones
        Predicate(
            "FailedScheduling",
            lambda msg : any([keyword in msg for keyword in ["affinity", "Insufficient memory", "Insufficient cpu"]])
        )
    ]

}



class K8sEventWatcher():
    """watch for K8s events that might signal an unresolvable state and request Acto to abort the convergence wait"""

    ABORT = "k8s_event_watcher_abort_request"

    
    def __init__(self, output_channel: multiprocessing.Queue) -> None:
        self.logger = get_thread_logger(with_prefix=True)
        self.output_channel = output_channel  
        self.counter = dict()
        self.abort_requested = False
        self.abort_predicates = copy.deepcopy(k8s_event_watcher_config.get("abort_predicates", []))
        for predicate in self.abort_predicates:
            t = predicate.threshold
            predicate.threshold = t if t is not None and t > 0 else k8s_event_watcher_config.get("default_threshold", 3)

    
    
        
    def observe(self, payload: bytes) -> None:
        if self.abort_requested:    # do nothing since we have already requested Acto to abort the convergence wait
            return

        try:
            event: dict = json.loads(payload.decode("utf-8"))
            reason = event.get("object", {}).get("reason")
            message = event.get("object", {}).get("message")    
        except Exception:
            self.logger.warning("Failed to deserialize K8s event from payload", str(payload))
            return 
        
        for predicate in self.abort_predicates:
            if predicate.match(reason, message):
                involved_object = event["object"].get("involvedObject", {})
                self.logger.info("Observered K8s event matching abort predicate %s for object %s" % (predicate, str(involved_object)))
                object_id = involved_object.get("uid", "")

                need_abort = self._inc_and_check(object_id, predicate)
                if need_abort:
                    self.logger.warning("Aborting convergence wait due to failed predicate %s"  % predicate)
                    self.output_channel.put(self.ABORT)
                    self.abort_requested = True
                break 

    

    def _inc_and_check(self, object_id: str, predicate: Predicate) -> bool:
        if not predicate in self.counter:
            self.counter[predicate] = dict()
        
        if not object_id in self.counter[predicate]:
            self.counter[predicate][object_id] = 0
        
        self.counter[predicate][object_id] += 1
        need_abort = self.counter[predicate][object_id] >= predicate.threshold
        return need_abort
