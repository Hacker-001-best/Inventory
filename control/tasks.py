from celery import shared_task
from datetime import date, timedelta
from .models import DebtSchedule

@shared_task
def mark_overdue_debts():
    yesterday = date.today() - timedelta(days=1)

    updated = DebtSchedule.objects.filter(
        due_date__lte=yesterday,   # ⬅️ вчера И РАНЬШЕ
        status='pending',
        transaction__debt_status='open'
    ).update(status='overdue')

    return updated
