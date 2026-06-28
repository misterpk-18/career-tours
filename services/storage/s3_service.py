import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class S3Service:

    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY")
        self.secret_key = os.getenv("AWS_SECRET_KEY")
        self.region = os.getenv("AWS_REGION", "ap-south-1")
        self.bucket_name = os.getenv("AWS_BUCKET_NAME", "career-tours-data")

        # Initialize boto3 client
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def upload_file(self, file_path: str, object_name: Optional[str] = None) -> str:
        """Uploads a file to the S3 bucket and returns its S3 URL.

        Args:
            file_path: Absolute or relative path to the local file.
            object_name: Optional custom name for the object in S3. If not provided,
                         the filename from file_path is used.

        Returns:
            The public URL of the uploaded file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if object_name is None:
            object_name = path.name

        try:
            # We don't set ACL='public-read' unless required, as modern S3 buckets block public ACLs by default.
            # Instead, we just upload the file. We construct a standard virtual-host style URL.
            self.client.upload_file(
                Filename=str(path),
                Bucket=self.bucket_name,
                Key=object_name
            )

            # Construct the S3 URL
            # Note: For some regions, the format is s3.amazonaws.com or s3-{region}.amazonaws.com.
            # Virtual-host style is generally: https://<bucket>.s3.<region>.amazonaws.com/<key>
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
            return s3_url

        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")
