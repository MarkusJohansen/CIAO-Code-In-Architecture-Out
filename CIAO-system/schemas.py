"""TypedDict schemas used throughout CIAO."""
from typing import Any, Dict, Sequence, TypedDict


class TextFormat(TypedDict):
    description: str


class TableFormat(TypedDict):
    columns: Sequence[str]
    caption: str


class DiagramFormat(TypedDict, total=False):
    type: str
    description: str


class StepsFormat(TypedDict):
    description: str


class ListFormat(TypedDict):
    items: Sequence[str]


class TreeFormat(TypedDict):
    description: str


class SectionFormat(TypedDict, total=False):
    text: TextFormat
    table: TableFormat
    diagram: DiagramFormat
    steps: StepsFormat
    list: ListFormat
    tree: TreeFormat
    examples: Dict[str, Any]


class SectionSpec(TypedDict, total=False):
    title: str
    goal: str
    format: SectionFormat
    style: str
    optional: bool
    example: Dict[str, Any]
    subsections: Dict[str, "SectionSpec"]


class GlobalGuidelines(TypedDict):
    objective: str
    formatting: Sequence[str]
    commitment: Sequence[str]
    code_analysis: str


class UserProfile(TypedDict):
    role: str
    preferred_language: str
    output_format: str
    writing_style: str
    target_audience: str
    include: Sequence[str]
    diagram_format: str


class Memory(TypedDict):
    global_guidelines: GlobalGuidelines
    md_safety: Sequence[str]
    user_profile: UserProfile
    doc_template: Dict[str, SectionSpec]
