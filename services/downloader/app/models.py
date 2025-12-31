from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class DownloadJobView:
    id: str
    url: str
    format: str
    status: str
    percent: int
    title: Optional[str] = None
    filename: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
