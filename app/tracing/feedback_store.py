"""In-memory user feedback store for thumbs up/down ratings."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FeedbackRecord:
    timestamp: str
    trace_id: str
    rating: str  # "up" or "down"


@dataclass
class FeedbackStore:
    records: deque = field(default_factory=lambda: deque(maxlen=10000))

    def record(self, trace_id: str, rating: str) -> None:
        self.records.append(
            FeedbackRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                trace_id=trace_id,
                rating=rating,
            )
        )

    def get_summary(self) -> dict:
        up = sum(1 for r in self.records if r.rating == "up")
        down = sum(1 for r in self.records if r.rating == "down")
        return {
            "total": len(self.records),
            "thumbs_up": up,
            "thumbs_down": down,
            "recent": [
                {"timestamp": r.timestamp, "trace_id": r.trace_id, "rating": r.rating}
                for r in list(self.records)[-20:]
            ],
        }


feedback_store = FeedbackStore()
