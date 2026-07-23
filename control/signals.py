from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *


@receiver(post_save, sender=DebtSchedule)
def update_transaction_after_payment(sender, instance, created, **kwargs):
    if not created:
        transaction.on_commit(
            lambda: instance.transaction.recalc_amounts()
        )

