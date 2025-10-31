import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

db_url = os.getenv("DATABASE_URL", "sqlite:///breadcrumbs.sqlite")
engine = create_engine(db_url, echo=False)


class SessionFactory:
    def __init__(self, engine):
        self.engine = engine
        self._sessions = []  # Track sessions

    def create_session(self) -> Session:
        """Create a session without context management."""
        session = Session(self.engine)
        self._sessions.append(session)
        return session

    @contextmanager
    def managed_session(self) -> Generator[Session, None, None]:
        session = Session(self.engine)
        self._sessions.append(session)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._sessions.remove(session)

    def close_all_sessions(self):
        """Explicitly close all tracked sessions"""
        for session in self._sessions[
            :
        ]:  # Copy list to avoid modification during iteration
            try:
                session.close()
            except Exception:
                print(f"Error closing session: {session}")
        self._sessions.clear()


default_session_factory = SessionFactory(engine)
