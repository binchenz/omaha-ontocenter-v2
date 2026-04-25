from typing import Any, Literal, Union
from pydantic import BaseModel


class Option(BaseModel):
    label: str
    value: str


class TextResponse(BaseModel):
    type: Literal["text"] = "text"
    content: str


class OptionsResponse(BaseModel):
    type: Literal["options"] = "options"
    content: str
    options: list[Option]


class PanelResponse(BaseModel):
    type: Literal["panel"] = "panel"
    content: str
    panel_type: str
    data: dict[str, Any]


class FileUploadRequest(BaseModel):
    type: Literal["file_upload"] = "file_upload"
    content: str
    accept: str = ".xlsx,.xls,.csv"
    multiple: bool = True


StructuredItem = Union[TextResponse, OptionsResponse, PanelResponse, FileUploadRequest]


class StructuredContent(BaseModel):
    items: list[StructuredItem]
