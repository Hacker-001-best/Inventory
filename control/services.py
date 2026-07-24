import base64
import hashlib
import re
from io import BytesIO
from decimal import Decimal
import barcode
from barcode.writer import ImageWriter
from dateutil.relativedelta import relativedelta
from datetime import date
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from .models import Customer, Transaction, DebtSchedule


def generate_barcode_image(barcode_value: str) -> str:
    code = barcode.get(
        'code128',
        barcode_value,
        writer=ImageWriter()
    )
    buffer = BytesIO()
    code.write(buffer)
    return base64.b64encode(buffer.getvalue()).decode()


def generate_barcode(product_id: int, name: str) -> str:
    hash_str = hashlib.sha256(name.encode()).hexdigest()
    # Берем только цифры из хэша, если их мало - дополняем из самого хэша (преобразовав буквы в цифры)
    digits = "".join(filter(str.isdigit, hash_str))
    name_part = digits[:6].ljust(6, '7') 
    id_part = str(product_id).zfill(6)
    return f"{name_part}{id_part}"


def get_or_create_customer_for_debt(name: str, surname: str, phone: str, passport: str):
    phone = re.sub(r'\D', '', (phone or '').strip())
    passport = (passport or '').strip().upper()
    name = (name or '').strip().title()
    surname = (surname or '').strip().title()

    if not all([name, surname, phone, passport]):
        raise serializers.ValidationError('Не все данные клиента переданы')

    customer = Customer.objects.filter(
        phone=phone,
        passport=passport
    ).first()

    if customer:
        if (
                customer.name.lower() != name.lower()
                or customer.surname.lower() != surname.lower()
        ):
            raise serializers.ValidationError(
                'Клиент с таким паспортом и номером уже существует'
            )
        return customer

    try:
        return Customer.objects.create(
            name=name,
            surname=surname,
            phone=phone,
            passport=passport
        )
    except IntegrityError:
        raise serializers.ValidationError(
            'Клиент с таким паспортом и номером уже существует'
        )


@transaction.atomic()
def create_debt_plan(transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id)

    if tx.months <= 0:
        raise serializers.ValidationError('Количество месяцев должно быть > 0')

    total = tx.debt_amount
    base = (total / tx.months).quantize(Decimal('0.01'))
    remainder = total - (base * tx.months)

    start = date.today()
    schedules = []
    for i in range(tx.months):
        amount = base
        if i == tx.months - 1:
            amount += remainder

        schedules.append(DebtSchedule(
            transaction=tx,
            due_date=start + relativedelta(months=i + 1),
            amount=amount
        ))
    
    DebtSchedule.objects.bulk_create(schedules)
    return base