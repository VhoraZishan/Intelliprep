from datetime import datetime
from typing import Dict, List


class SessionState:
    def __init__(self, session_id: str, question_ids: List[int]):
        self.session_id = session_id
        self.question_ids = question_ids
        self.start_time = datetime.utcnow()

        # question_index -> render start time
        self.question_start_times: Dict[int, datetime] = {}

SESSION_STORE: Dict[str, SessionState] = {}
