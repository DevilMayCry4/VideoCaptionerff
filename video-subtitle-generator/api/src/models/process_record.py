"""
处理记录数据模型
"""

from datetime import datetime
from typing import Optional
from flask_sqlalchemy import SQLAlchemy

# 初始化数据库
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class ProcessRecord(db.Model):
    """视频处理记录模型"""
    
    __tablename__ = 'process_records'
    
    # 主键
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 文件信息
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    file_size = db.Column(db.BigInteger, default=0)
    
    # 处理状态
    status = db.Column(
        db.String(50), 
        default='pending',
        nullable=False,
        index=True
    )
    
    # 进度信息
    progress = db.Column(db.Integer, default=0, nullable=False)
    
    # 文件路径
    audio_path = db.Column(db.Text)
    subtitle_path = db.Column(db.Text)
    
    # 错误信息
    error_message = db.Column(db.Text)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 索引
    __table_args__ = (
        db.Index('idx_status_created', 'status', 'created_at'),
        db.CheckConstraint("progress >= 0 AND progress <= 100", name='check_progress'),
        db.CheckConstraint(
            "status IN ('pending', 'processing', 'extracting', 'transcribing', 'completed', 'failed')",
            name='check_status'
        )
    )
    
    def __repr__(self):
        return f"<ProcessRecord {self.id}: {self.original_filename} - {self.status}>"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'status': self.status,
            'progress': self.progress,
            'audio_path': self.audio_path,
            'subtitle_path': self.subtitle_path,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_status(self, status: str, progress: Optional[int] = None, 
                     error_message: Optional[str] = None) -> None:
        """更新处理状态"""
        self.status = status
        if progress is not None:
            self.progress = progress
        if error_message is not None:
            self.error_message = error_message
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_by_id(cls, task_id: str) -> Optional['ProcessRecord']:
        """根据ID获取记录"""
        return cls.query.get(task_id)
    
    @classmethod
    def get_by_status(cls, status: str):
        """根据状态获取记录列表"""
        return cls.query.filter_by(status=status).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_pending_tasks(cls, limit: int = 10):
        """获取待处理任务"""
        return cls.query.filter(
            cls.status.in_(['pending', 'processing'])
        ).order_by(cls.created_at.asc()).limit(limit).all()
    
    @classmethod
    def get_completed_tasks(cls, limit: int = 50):
        """获取已完成任务"""
        return cls.query.filter_by(status='completed').order_by(
            cls.created_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def cleanup_old_records(cls, days: int = 7) -> int:
        """清理旧记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_records = cls.query.filter(
            cls.created_at < cutoff_date,
            cls.status.in_(['completed', 'failed'])
        ).all()
        
        count = len(old_records)
        for record in old_records:
            # 删除相关文件
            try:
                if record.file_path and os.path.exists(record.file_path):
                    os.remove(record.file_path)
                if record.audio_path and os.path.exists(record.audio_path):
                    os.remove(record.audio_path)
                if record.subtitle_path and os.path.exists(record.subtitle_path):
                    os.remove(record.subtitle_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {e}")
            
            # 删除数据库记录
            db.session.delete(record)
        
        db.session.commit()
        return count