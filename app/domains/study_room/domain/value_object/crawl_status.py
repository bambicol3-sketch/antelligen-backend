from enum import Enum


class CrawlStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STRUCTURE_CHANGED = "STRUCTURE_CHANGED"
