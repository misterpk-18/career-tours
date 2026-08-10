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

        # No default bucket. The old fallback was `career-tours-data`, a bucket
        # this account cannot touch, so a missing AWS_BUCKET_NAME surfaced as a
        # 500 with S3's opaque `AllAccessDisabled` instead of a config error.
        # Deployments must set the bucket explicitly; the real one is
        # `career-tours-bkt`.
        self.bucket_name = os.getenv("AWS_BUCKET_NAME")

        if not self.bucket_name:
            raise RuntimeError(
                "AWS_BUCKET_NAME is not set; refusing to guess an S3 bucket"
            )

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
            self.client.upload_file(Filename=str(path), Bucket=self.bucket_name, Key=object_name)

            # Construct the S3 URL
            # Note: For some regions, the format is s3.amazonaws.com or s3-{region}.amazonaws.com.
            # Virtual-host style is generally: https://<bucket>.s3.<region>.amazonaws.com/<key>
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
            return s3_url

        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")

    def generate_presigned_url(
        self, object_name: str, expires_in: int = 3600, inline: bool = True
    ) -> str:
        """Generate a time-limited presigned GET URL for a private S3 object.

        Args:
            object_name: The S3 object key (e.g. "<uuid>.pdf").
            expires_in: Seconds until the URL expires (default 1 hour).
            inline: If True, the browser renders the file (e.g. PDF) inline;
                    otherwise it is served as an attachment/download.

        Returns:
            A signed URL that grants temporary read access to the object.
        """
        disposition = "inline" if inline else "attachment"

        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_name,
                    "ResponseContentDisposition": disposition,
                },
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    @staticmethod
    def key_from_url(file_url: str) -> str:
        """Extract the S3 object key from a stored file URL.

        The DB stores the full virtual-host URL, not the bare key, so we take
        everything after the ".amazonaws.com/" marker.
        """
        marker = ".amazonaws.com/"
        idx = file_url.find(marker)
        if idx == -1:
            raise ValueError(f"Cannot extract S3 key from URL: {file_url}")
        return file_url[idx + len(marker):]
