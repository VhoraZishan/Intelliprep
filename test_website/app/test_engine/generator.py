import random
from collections import defaultdict, deque
from typing import List
from app.db import get_connection,put_connection


TOTAL_QUESTIONS = 25

DOMAIN_QUOTAS = {
    "aptitude": 10,
    "technical": 15,
}

DIFFICULTIES = ["easy", "medium", "hard"]

MAX_TOPIC_RATIO = 0.30
MAX_PER_TOPIC = int(TOTAL_QUESTIONS * MAX_TOPIC_RATIO)


def generate_question_ids() -> List[int]:
    conn = get_connection()
    cur = conn.cursor()

    selected = []
    used_ids = set()
    topic_counter = defaultdict(int)

    for domain, domain_quota in DOMAIN_QUOTAS.items():
        remaining = domain_quota

        # 1️⃣ Fetch ALL questions for this domain
        cur.execute(
            """
            SELECT id, topic, difficulty
            FROM questions
            WHERE is_active = true
              AND domain = %s
            ORDER BY random();
            """,
            (domain,),
        )

        rows = cur.fetchall()

        # 2️⃣ Group by difficulty
        by_difficulty = {
            "easy": deque(),
            "medium": deque(),
            "hard": deque(),
        }

        for qid, topic, diff in rows:
            if diff in by_difficulty:
                by_difficulty[diff].append((qid, topic))

        # 3️⃣ Round-robin pick (removes bias)
        while remaining > 0 and any(by_difficulty.values()):
            for diff in DIFFICULTIES:
                if remaining == 0:
                    break
                if not by_difficulty[diff]:
                    continue

                qid, topic = by_difficulty[diff].popleft()

                if qid in used_ids:
                    continue

                # Soft topic cap
                if topic_counter[topic] >= MAX_PER_TOPIC:
                    continue

                selected.append(qid)
                used_ids.add(qid)
                topic_counter[topic] += 1
                remaining -= 1

        # 4️⃣ Backfill ignoring difficulty & topic if still short
        if remaining > 0:
            for qid, topic, _ in rows:
                if remaining == 0:
                    break
                if qid in used_ids:
                    continue

                selected.append(qid)
                used_ids.add(qid)
                topic_counter[topic] += 1
                remaining -= 1

        if remaining > 0:
            cur.close()
            put_connection(conn)
            raise RuntimeError(f"Dataset cannot satisfy domain quota for {domain}")

    cur.close()
    put_connection(conn)

    if len(selected) != TOTAL_QUESTIONS:
        raise RuntimeError("Failed to generate 25-question test")

    random.shuffle(selected)
    return selected
