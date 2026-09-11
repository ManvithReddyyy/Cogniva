import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

pooler_url = (
    'postgresql://postgres.rzyblluwtipqhkitpxca:hmmmmhkmm12'
    '@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres'
)
print('Connecting via pooler...')

engine = create_engine(
    pooler_url,
    connect_args={'connect_timeout': 30, 'options': '-c statement_timeout=30000'}
)

with engine.connect() as conn:
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='subscribers'")
    )
    existing = [r[0] for r in result]
    print('Existing columns:', existing)
    if 'display_name' not in existing:
        conn.execute(text('ALTER TABLE subscribers ADD COLUMN display_name VARCHAR'))
        conn.commit()
        print('SUCCESS: display_name column added!')
    else:
        print('OK: display_name already exists')
