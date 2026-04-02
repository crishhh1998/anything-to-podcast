from dataclasses import dataclass


@dataclass
class FetchResult:
    title: str
    content: str
    source_type: str  # "paper", "report", "reddit", "twitter"
    url: str


class BaseFetcher:
    def fetch(self, url: str) -> FetchResult:
        raise NotImplementedError
