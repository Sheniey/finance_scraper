
from typing import Literal
from pydantic import BaseModel, Field


# ================================================== #
# TYPES AND MODELS                                   #
# ================================================== #

type LangStyle = Literal['friendly', 'professional', 'technical']

class Language(BaseModel):
    code: str
    name: str
    style: LangStyle = Field(default='friendly')
