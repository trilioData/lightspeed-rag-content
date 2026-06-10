import dataclasses

@dataclasses.dataclass
class Prompt:
    id: str
    category: str
    validation_mode: str
    prompt: str
    expected_citations: list[str]
    tags: list[str]
    gitbook_citations: list[str] = None
    expected_facts: list[str] = None
    yaml_validation: list[dict] = None