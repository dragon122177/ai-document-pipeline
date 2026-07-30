from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .database import Database
from .events import EventBroker
from .pipeline import PipelineProcessor, PipelineWorker
from .storage import LocalFileStorage


@dataclass(slots=True)
class Services:
    settings: Settings
    database: Database
    storage: LocalFileStorage
    broker: EventBroker
    processor: PipelineProcessor
    worker: PipelineWorker
    provider_name: str
