from typing import Annotated

from pydantic import BaseModel, StringConstraints


class SnapshotInput(BaseModel):
    month: Annotated[str, StringConstraints(pattern=r'^20[0-9]{2}-(0[1-9]|1[0-2])$')]
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
