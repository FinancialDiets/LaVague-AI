from __future__ import annotations
from typing import List, Callable, Optional
from pydantic import BaseModel
import yaml
import importlib.util
from pathlib import Path
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from ..defaults import (
    default_get_driver,
    DefaultLLM,
    DefaultEmbedder,
    default_python_code_extractor,
)
from ..prompts import DEFAULT_PROMPT
from ..driver import AbstractDriver
from ..action_engine import ActionEngine
from ..command_center import GradioDemo


class Config:
    def __init__(
        self,
        llm: BaseLLM,
        embedder: BaseEmbedding,
        get_driver: Callable[[], AbstractDriver],
        prompt_template: str,
        cleaning_function: Callable[[str], Optional[str]],
    ):
        self.llm = llm
        self.embedder = embedder
        self.get_driver = get_driver
        self.prompt_template = prompt_template
        self.cleaning_function = cleaning_function

    def from_path(path: str) -> Config:
        # Convert the path to a Python module path
        module_name = Path(path).stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        llm = getattr(module, "LLM", DefaultLLM)()
        embedder = getattr(module, "Embedder", DefaultEmbedder)()
        get_driver = getattr(module, "get_driver", default_get_driver)
        prompt_template = getattr(module, "prompt_template", DEFAULT_PROMPT)
        cleaning_function = getattr(
            module, "cleaning_function", default_python_code_extractor
        )
        return Config(llm, embedder, get_driver, prompt_template, cleaning_function)

    def make_default_action_engine() -> ActionEngine:
        return ActionEngine(
            DefaultLLM(),
            DefaultEmbedder(),
            DEFAULT_PROMPT,
            default_get_driver,
            default_python_code_extractor,
        )

    def make_action_engine(self) -> ActionEngine:
        return ActionEngine(
            self.llm, self.embedder, self.prompt_template, self.cleaning_function
        )


class Instructions(BaseModel):
    url: str
    instructions: List[str]

    def from_yaml(path: Path) -> Instructions:
        with open(path, "r") as file:
            loaded = yaml.safe_load(file)
        return Instructions(**loaded)
