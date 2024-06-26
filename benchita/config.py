import yaml
from pydantic import BaseModel, Field
from typing import List, Optional

from benchita.task import get_tasks
from benchita.template import get_templates

class Task(BaseModel):
    name: str
    num_shots: int = 3
    args: dict = {}

class Model(BaseModel):
    name: str
    class_name: str = Field(alias="class", default="AutoModelForCausalLM")
    dtype: str = "float32"
    args: dict = {}

class Tokenizer(BaseModel):
    name: str = None
    class_name: str = Field(alias="class", default="AutoTokenizer")
    patch_tokenizer_pad: bool = False
    args: dict = {}

class Template(BaseModel):
    system_style: str = "inject"
    name: str = None
    force: bool = False
    args: dict = {"add_generation_prompt": True, "tokenize": False}

class PeftAdapter(BaseModel):
    name: str
    class_name: str = Field(alias="class", default="PeftModel")
    args: dict = {}

class Generate(BaseModel):
    batch_size: int = 16
    args: dict = {"do_sample": False}

class ModelConfig(BaseModel):
    model: Model
    tokenizer: Tokenizer = Tokenizer()
    template: Template = Template()
    generate: Generate = Generate()
    peft: Optional[PeftAdapter] = None

class Config(BaseModel):
    experiment: str
    tasks: List[Task]
    models: List[ModelConfig]


def parse_config(config_file):
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    config = Config(**config)

    for task in config.tasks:
        if task.name not in get_tasks():
            raise Exception(f"Task {task.name} not found")

    for model in config.models:
        if model.template.name is not None and model.template.name not in get_templates():
            raise Exception(f"Template {model.template.name} not found")
        if model.tokenizer.name is None:
            model.tokenizer.name = model.model.name

    return config