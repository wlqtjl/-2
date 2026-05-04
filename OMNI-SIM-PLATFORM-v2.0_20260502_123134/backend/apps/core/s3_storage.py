from typing import Optional, Dict, Any, BinaryIO
import logging
from io import BytesIO
from apps.core.config import settings

logger = logging.getLogger(__name__)

# boto3 是可选依赖，仅在启用 S3 时才需要安装
try:
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
    BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore
    BOTO3_AVAILABLE = False


class S3Storage:
    """S3存储服务封装"""

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region_name = settings.S3_REGION_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.enabled = settings.S3_ENABLED and BOTO3_AVAILABLE

        if settings.S3_ENABLED and not BOTO3_AVAILABLE:
            logger.warning("S3_ENABLED=True 但未安装 boto3，请先 pip install boto3 botocore")

        self.client = None
        if self.enabled:
            self._init_client()
    
    def _init_client(self):
        """初始化S3客户端"""
        try:
            config = {
                'region_name': self.region_name,
            }
            
            if self.endpoint_url:
                config['endpoint_url'] = self.endpoint_url
            
            if self.access_key and self.secret_key:
                config['aws_access_key_id'] = self.access_key
                config['aws_secret_access_key'] = self.secret_key
            
            self.client = boto3.client('s3', **config)
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = 'application/octet-stream',
        acl: str = 'private',
        extra_args: Optional[Dict[str, Any]] = None
    ) -> str:
        """上传文件到S3"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return ""
        
        try:
            args = {'ContentType': content_type, 'ACL': acl}
            if extra_args:
                args.update(extra_args)
            
            self.client.upload_fileobj(file_obj, self.bucket_name, key, ExtraArgs=args)
            url = self.get_url(key)
            logger.info(f"File uploaded successfully: {url}")
            return url
        except ClientError as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise
    
    def upload_file_from_path(
        self,
        file_path: str,
        key: str,
        content_type: str = 'application/octet-stream',
        acl: str = 'private'
    ) -> str:
        """从文件路径上传文件"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return ""
        
        try:
            self.client.upload_file(file_path, self.bucket_name, key, ExtraArgs={
                'ContentType': content_type,
                'ACL': acl
            })
            url = self.get_url(key)
            logger.info(f"File uploaded from path: {url}")
            return url
        except ClientError as e:
            logger.error(f"Failed to upload file from path: {str(e)}")
            raise
    
    def download_file(self, key: str) -> BytesIO:
        """下载文件到内存"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return BytesIO()
        
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return BytesIO(response['Body'].read())
        except ClientError as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise
    
    def download_file_to_path(self, key: str, file_path: str):
        """下载文件到指定路径"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return
        
        try:
            self.client.download_file(self.bucket_name, key, file_path)
            logger.info(f"File downloaded to: {file_path}")
        except ClientError as e:
            logger.error(f"Failed to download file to path: {str(e)}")
            raise
    
    def delete_file(self, key: str):
        """删除文件"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted: {key}")
        except ClientError as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise
    
    def get_url(self, key: str) -> str:
        """获取文件URL"""
        if not self.enabled or not self.client:
            return ""
        
        if self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket_name}/{key}"
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{key}"
    
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """获取预签名URL"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return ""
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise
    
    def list_files(self, prefix: str = "") -> list:
        """列出指定前缀的文件"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return []
        
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            return files
        except ClientError as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise
    
    def file_exists(self, key: str) -> bool:
        """检查文件是否存在"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {str(e)}")
            raise
    
    def copy_file(self, source_key: str, destination_key: str):
        """复制文件"""
        if not self.enabled or not self.client:
            logger.warning("S3 storage is not enabled")
            return
        
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key
            )
            logger.info(f"File copied: {source_key} -> {destination_key}")
        except ClientError as e:
            logger.error(f"Failed to copy file: {str(e)}")
            raise


# 全局存储实例
s3_storage = S3Storage()


# 文件类型配置
class FileTypes:
    """文件类型常量"""
    PDF = 'application/pdf'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    DOC = 'application/msword'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    PPT = 'application/vnd.ms-powerpoint'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    XLS = 'application/vnd.ms-excel'
    JPG = 'image/jpeg'
    PNG = 'image/png'
    GIF = 'image/gif'
    WEBP = 'image/webp'
    SVG = 'image/svg+xml'
    MP4 = 'video/mp4'
    MP3 = 'audio/mpeg'
    ZIP = 'application/zip'
    TAR = 'application/x-tar'
    JSON = 'application/json'
    CSV = 'text/csv'
    TXT = 'text/plain'


# 文件路径生成器
class FilePathGenerator:
    """文件路径生成工具"""
    
    @staticmethod
    def generate_course_upload_path(course_id: int, filename: str) -> str:
        """生成课程上传文件路径"""
        return f"courses/{course_id}/{filename}"
    
    @staticmethod
    def generate_user_avatar_path(user_id: int, filename: str) -> str:
        """生成用户头像文件路径"""
        return f"users/{user_id}/avatar/{filename}"
    
    @staticmethod
    def generate_import_path(task_id: str, filename: str) -> str:
        """生成导入任务文件路径"""
        return f"imports/{task_id}/{filename}"
    
    @staticmethod
    def generate_export_path(task_id: str, filename: str) -> str:
        """生成导出任务文件路径"""
        return f"exports/{task_id}/{filename}"
    
    @staticmethod
    def generate_backup_path(timestamp: str, filename: str) -> str:
        """生成备份文件路径"""
        return f"backups/{timestamp}/{filename}"