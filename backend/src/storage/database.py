"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Create engine
# For SQLite, add timeout and enable write access
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30  # Wait up to 30 seconds for database lock
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True  # Verify connections before using them
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency that creates a new database session for each request.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    # 确保推荐引擎相关模型被导入（触发 SQLAlchemy 元数据注册）
    try:
        from ..models.vector_index import RecommendationRule, RecommendationLog  # noqa: F401
    except ImportError:
        pass
    
    Base.metadata.create_all(bind=engine)
    
    # 迁移: 为 vector_indexes 表添加 uuid 列（如果不存在）
    _migrate_vector_indexes_uuid()
    
    # 迁移: 为 vector_indexes 表添加 collection_name 列（如果不存在）
    _migrate_vector_indexes_collection_name()
    
    # 迁移: 为 vector_indexes 表添加 physical_collection_name 列（如果不存在）
    _migrate_vector_indexes_physical_collection_name()
    
    # 执行推荐规则迁移脚本（如果表为空则初始化默认规则）
    _init_recommendation_rules()
    
    print("Database initialized successfully")


def _migrate_vector_indexes_uuid():
    """
    迁移: 为 vector_indexes 表添加 uuid 列
    
    如果表存在但缺少 uuid 列，则添加该列并为已有记录填充 UUID 值。
    """
    import uuid as uuid_mod
    
    db = SessionLocal()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        if 'vector_indexes' not in inspector.get_table_names():
            return
        
        # 检查 uuid 列是否已存在
        columns = [col['name'] for col in inspector.get_columns('vector_indexes')]
        if 'uuid' in columns:
            return  # 已存在，跳过
        
        # 添加 uuid 列
        db.execute(text("ALTER TABLE vector_indexes ADD COLUMN uuid VARCHAR(36)"))
        db.commit()
        
        # 为已有记录填充 UUID
        result = db.execute(text("SELECT id FROM vector_indexes WHERE uuid IS NULL"))
        rows = result.fetchall()
        for row in rows:
            db.execute(
                text("UPDATE vector_indexes SET uuid = :uuid WHERE id = :id"),
                {"uuid": str(uuid_mod.uuid4()), "id": row[0]}
            )
        db.commit()
        
        print(f"Migrated vector_indexes: added uuid column, filled {len(rows)} records")
        
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to migrate vector_indexes uuid: {e}")
    finally:
        db.close()


def _migrate_vector_indexes_collection_name():
    """
    迁移: 为 vector_indexes 表添加 collection_name 列
    
    如果表存在但缺少 collection_name 列，则添加该列并为已有记录填充默认值 'default_collection'。
    """
    db = SessionLocal()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        if 'vector_indexes' not in inspector.get_table_names():
            return
        
        # 检查 collection_name 列是否已存在
        columns = [col['name'] for col in inspector.get_columns('vector_indexes')]
        if 'collection_name' in columns:
            return  # 已存在，跳过
        
        # 添加 collection_name 列，默认值为 'default_collection'
        db.execute(text(
            "ALTER TABLE vector_indexes ADD COLUMN collection_name VARCHAR(255) DEFAULT 'default_collection'"
        ))
        db.commit()
        
        # 为已有记录填充默认值
        result = db.execute(text("SELECT COUNT(*) FROM vector_indexes WHERE collection_name IS NULL"))
        null_count = result.scalar()
        if null_count > 0:
            db.execute(text(
                "UPDATE vector_indexes SET collection_name = 'default_collection' WHERE collection_name IS NULL"
            ))
            db.commit()
        
        print(f"Migrated vector_indexes: added collection_name column")
        
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to migrate vector_indexes collection_name: {e}")
    finally:
        db.close()


def _migrate_vector_indexes_physical_collection_name():
    """
    迁移: 为 vector_indexes 表添加 physical_collection_name 列
    
    Dify 方案：按维度拆分物理 Collection，需要记录物理 Collection 名称。
    如果表存在但缺少 physical_collection_name 列，则添加该列并为已有记录
    根据 collection_name + dimension 自动生成物理名称。
    """
    db = SessionLocal()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        if 'vector_indexes' not in inspector.get_table_names():
            return
        
        # 检查 physical_collection_name 列是否已存在
        columns = [col['name'] for col in inspector.get_columns('vector_indexes')]
        if 'physical_collection_name' in columns:
            return  # 已存在，跳过
        
        # 添加 physical_collection_name 列
        db.execute(text(
            "ALTER TABLE vector_indexes ADD COLUMN physical_collection_name VARCHAR(255)"
        ))
        db.commit()
        
        # 为已有记录自动生成物理 Collection 名称
        # 格式: {collection_name}_dim{dimension}
        result = db.execute(text(
            "SELECT id, collection_name, dimension FROM vector_indexes WHERE physical_collection_name IS NULL"
        ))
        rows = result.fetchall()
        for row in rows:
            idx_id, coll_name, dim = row
            if coll_name and dim:
                physical_name = f"{coll_name}_dim{dim}"
                db.execute(
                    text("UPDATE vector_indexes SET physical_collection_name = :pname WHERE id = :id"),
                    {"pname": physical_name, "id": idx_id}
                )
        db.commit()
        
        print(f"Migrated vector_indexes: added physical_collection_name column, filled {len(rows)} records")
        
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to migrate vector_indexes physical_collection_name: {e}")
    finally:
        db.close()


def _init_recommendation_rules():
    """
    初始化推荐规则默认数据（T072）
    
    如果 recommendation_rules 表为空，则从 008_recommendation.sql 
    或默认配置中插入初始规则。
    """
    import json
    
    db = SessionLocal()
    try:
        # 检查表是否存在并且为空
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        if 'recommendation_rules' not in inspector.get_table_names():
            return
        
        result = db.execute(text("SELECT COUNT(*) FROM recommendation_rules"))
        count = result.scalar()
        
        if count > 0:
            return  # 已有数据，跳过初始化
        
        # 尝试从配置文件加载默认规则
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config", "recommendation_rules.json"
        )
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            import uuid
            for rule in config.get("rules", []):
                db.execute(text("""
                    INSERT INTO recommendation_rules 
                    (rule_id, priority, min_vector_count, max_vector_count, 
                     min_dimension, max_dimension, embedding_models,
                     recommended_index_type, recommended_metric_type, 
                     reason_template, is_active)
                    VALUES (:rule_id, :priority, :min_vc, :max_vc, 
                            :min_dim, :max_dim, :models,
                            :index_type, :metric_type, :reason, :active)
                """), {
                    "rule_id": rule.get("rule_id", str(uuid.uuid4())),
                    "priority": rule["priority"],
                    "min_vc": rule.get("min_vector_count"),
                    "max_vc": rule.get("max_vector_count"),
                    "min_dim": rule.get("min_dimension"),
                    "max_dim": rule.get("max_dimension"),
                    "models": json.dumps(rule.get("embedding_models")) if rule.get("embedding_models") else None,
                    "index_type": rule["recommended_index_type"],
                    "metric_type": rule.get("recommended_metric_type"),
                    "reason": rule["reason_template"],
                    "active": True
                })
            
            db.commit()
            print(f"Initialized {len(config.get('rules', []))} recommendation rules")
        
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to initialize recommendation rules: {e}")
    finally:
        db.close()


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)
    print("Database dropped successfully")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "init":
            init_db()
        elif command == "drop":
            confirm = input("Are you sure you want to drop all tables? (yes/no): ")
            if confirm.lower() == "yes":
                drop_db()
            else:
                print("Operation cancelled")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: init, drop")
    else:
        print("Usage: python database.py [init|drop]")
