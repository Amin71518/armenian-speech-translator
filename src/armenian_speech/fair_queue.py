"""Bounded per-source pending phrases feeding one worker in round-robin order."""

import sys
from collections import deque
from time import perf_counter


class FairQueue:
    def __init__(self, worker, capacity=2):
        if capacity < 1:
            raise ValueError("Per-source pending capacity must be positive.")
        self.worker, self.capacity = worker, capacity
        self.labels = ("Me", "System")
        self.queues = {name: deque() for name in self.labels}
        self.stats = {name: {"offered": 0, "buffered": 0, "dispatched": 0,
                             "dropped_full": 0, "skipped_gap": 0, "cancelled": 0,
                             "worker_rejected": 0, "peak_pending": 0} for name in self.labels}
        for counts in self.stats.values():
            counts.update(max_pending_wait_s=0.0, sum_pending_wait_s=0.0)
        self.next = 0

    def offer(self, label, segment):
        if label not in self.queues:
            raise ValueError("Unknown source label.")
        counts, queue = self.stats[label], self.queues[label]
        counts["offered"] += 1
        if segment.reason == "gap":
            counts["skipped_gap"] += 1
            print(f"{label}: skipped incomplete gap phrase.", file=sys.stderr, flush=True)
            return False
        if len(queue) >= self.capacity:
            counts["dropped_full"] += 1
            print(f"{label}: pending phrase queue full; dropped incoming phrase.",
                  file=sys.stderr, flush=True)
            return False
        queue.append((segment, perf_counter()))
        counts["buffered"] += 1
        counts["peak_pending"] = max(counts["peak_pending"], len(queue))
        return True

    @property
    def pending(self):
        return sum(len(queue) for queue in self.queues.values())

    def dispatch(self):
        self.worker.poll()
        while self.worker.stats["accepted"] - self.worker.stats["completed"] < self.worker.capacity:
            choice = next((i for i in (self.next, 1 - self.next)
                           if self.queues[self.labels[i]]), None)
            if choice is None:
                break
            label = self.labels[choice]
            segment, offered = self.queues[label].popleft()
            wait = perf_counter() - offered
            self.stats[label]["max_pending_wait_s"] = max(
                self.stats[label]["max_pending_wait_s"], wait,
            )
            self.stats[label]["sum_pending_wait_s"] += wait
            self.next = 1 - choice
            key = "dispatched" if self.worker.submit(segment, speaker=label) else "worker_rejected"
            self.stats[label][key] += 1

    def cancel(self):
        for label, queue in self.queues.items():
            self.stats[label]["cancelled"] += len(queue)
            queue.clear()

    def summary(self):
        return {label: {**counts, "pending": len(self.queues[label])}
                for label, counts in self.stats.items()}
