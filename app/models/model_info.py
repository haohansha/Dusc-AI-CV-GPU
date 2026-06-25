from dataclasses import dataclass, field


@dataclass
class ModelInfo:
    name: str
    path: str
    model_type: str = ""
    num_classes: int = 0
    class_names: list = field(default_factory=list)
    file_size: int = 0
    created_at: str = ""
    status: str = "ready"
    metrics: dict = field(default_factory=dict)
