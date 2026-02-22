import uuid
from datetime import datetime


def generate_plan_id() -> str:
    return f"LP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"


def generate_adjustment_id() -> str:
    return f"RA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"


def generate_prepayment_id() -> str:
    return f"PP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
