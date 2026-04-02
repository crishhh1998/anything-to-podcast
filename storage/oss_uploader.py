import oss2
from pathlib import Path


class OSSUploader:
    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str, bucket: str, base_url: str):
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket)
        self.base_url = base_url.rstrip("/")

    def upload(self, local_path: str, remote_key: str) -> str:
        """Upload file to OSS, return public URL."""
        self.bucket.put_object_from_file(remote_key, local_path)
        return f"{self.base_url}/{remote_key}"

    def delete(self, remote_key: str) -> None:
        self.bucket.delete_object(remote_key)
