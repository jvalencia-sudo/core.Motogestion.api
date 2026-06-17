from pydantic import BaseModel


class FileDownloadUrlContract(BaseModel):
    url: str
