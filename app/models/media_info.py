from dataclasses import dataclass


@dataclass
class MediaInfo:
    name: str
    path: str
    media_type: str = ""
    duration: float = 0.0
    resolution: str = ""
    fps: float = 0.0
    frame_count: int = 0
    file_size: int = 0
    imported_at: str = ""
    has_labels: bool = False
