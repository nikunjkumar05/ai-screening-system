import asyncio
from app.main import get_session_summary
from app.database import SessionLocal
import traceback

async def run():
    db = SessionLocal()
    try:
        res = await get_session_summary(1, db)
        print(res)
    except Exception as e:
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run())
