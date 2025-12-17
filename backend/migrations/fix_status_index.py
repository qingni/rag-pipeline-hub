"""Fix: Add idx_status index."""
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///./app.db')

with engine.connect() as conn:
    try:
        conn.execute(text('CREATE INDEX idx_status ON embedding_results (status)'))
        conn.commit()
        print('✅ Index idx_status created successfully!')
    except Exception as e:
        print(f'Error: {e}')
