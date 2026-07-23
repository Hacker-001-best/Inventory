import base64
import hashlib
import re
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from dateutil.relativedelta import relativedelta
from datetime import date
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from .models import *



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
    digits = re.sub(r'\D', '', hash_str)
    name_part = digits[:6].ljust(6, '0')
    id_part = str(product_id).zfill(6)
    return f"{name_part}{id_part}"
def get_or_create_customer_for_debt(name: str,surname: str,phone: str, passport: str):
    name = (name or '').strip()
    surname = (surname or '').strip()
    phone = (phone or '').strip()
    passport = (passport or '').strip()
    phone = re.sub(r'\D', '', phone)
    passport = passport.upper().strip()
    name = name.strip().title()
    surname = surname.strip().title()
    if not all([name, surname, phone, passport]):
        raise ValueError('Не все данные клиента переданы')

    customer = Customer.objects.filter(
        phone=phone,
        passport=passport
    ).first()

    # 🔍 Если клиент найден
    if customer:
        # ❌ Имя или фамилия не совпадает
        if (
                customer.name.lower() != name.lower()
                or customer.surname.lower() != surname.lower()
        ):
            raise ValueError(
                'Клиент с таким паспортом и номером уже существует'
            )

        # ✅ Всё совпадает — используем
        return customer

    # ➕ Клиента нет — создаём
    try:
        return Customer.objects.create(
            name=name,
            surname=surname,
            phone=phone,
            passport=passport
        )
    except IntegrityError:
        # защита от race condition
        raise ValueError(
            'Клиент с таким паспортом и номером уже существует'
        )
@transaction.atomic()
def create_debt_plan(transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id)

    if tx.months <= 0:
        raise ValueError('Количество месяцев должно быть > 0')

    total = tx.debt_amount
    base = (total / tx.months).quantize(Decimal('0.01'))
    remainder = total - (base * tx.months)

    start = date.today()

    for i in range(tx.months):
        amount = base
        if i == tx.months - 1:
            amount += remainder

        DebtSchedule.objects.create(
            transaction=tx,
            due_date=start + relativedelta(months=i + 1),
            amount=amount
        )
    return base