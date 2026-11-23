from typing import Annotated

from pydantic import BaseModel, StringConstraints


class Login(BaseModel):
    username: Annotated[str, StringConstraints(min_length=1, max_length=48, strip_whitespace=True)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
