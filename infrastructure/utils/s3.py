import os
from typing import Tuple

import boto3

from config import settings


def upload_file(file_name: str, object_name=None, remove_on_upload: bool = False):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param object_name: S3 object name. If not specified then file_name is used
    :param remove_on_upload: Remove file on upload finished
    :return: True if file was uploaded, else False
    """
    config = settings.aws_config
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client("s3")
    s3_client.upload_file(file_name, config.bucket_name, object_name)

    if remove_on_upload:
        os.remove(file_name)

    return object_name


def download_file(file_name: str) -> Tuple[str, str]:
    config = settings.aws_config
    s3_client = boto3.client("s3")
    file_path = "./resources/reports/"
    s3_client.download_file(config.bucket_name, file_name, f"{file_path}{file_name}")
    return file_path, file_name


def generate_presigned_url(file_name: str, expiration: int = 3600):
    """
    Generate a presigned URL for an S3 object.
    :param file_name: The name of the file in the S3 bucket.
    :param expiration: Time in seconds for the presigned URL to remain valid. Default is 3600 seconds (1 hour).
    :return: A presigned URL as a string.
    """
    s3_client = boto3.client("s3")
    config = settings.aws_config
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.bucket_name, "Key": file_name},
        ExpiresIn=expiration,
    )
