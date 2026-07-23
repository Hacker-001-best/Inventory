from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# =========================
# Пользователь
# =========================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('cashier', 'Кассир'),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='cashier'
    )
    owner = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cashiers',
        limit_choices_to={'role': 'admin'}
    )
    def __str__(self):
        return self.username


# =========================
# Категория товара
# =========================
class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# =========================
# Товар
# =========================
class Product(models.Model):
    name = models.CharField(max_length=255)
    STATUS = (
        ('active', 'Активен'),
        ('archived', 'Архив'),
        ('blocked', 'Заблокирован'),
    )
    status = models.CharField(max_length=10, choices=STATUS, default='active')
    barcode = models.CharField(    max_length=100, unique=True, db_index=True, null=True, blank=True)
    photo = models.ImageField( upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default="шт")
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.name} ({self.barcode})"


# =========================
# Движение товара (склад)
# =========================
class StockDocument(models.Model):
    MOVEMENT_TYPE = (
        ('in', 'Приход'),
        ('out', 'Расход'),
    )

    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} №{self.id}"

class StockMovement(models.Model):
    document = models.ForeignKey(StockDocument, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


# =========================
# Чек (продажа)
# =========================
class Sale(models.Model):
    STATUS = (
        ('active', 'Активен'),
        ('canceled', 'Отменён'),
    )
    cashier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    canceled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='active')
    total_price = models.DecimalField( max_digits=12, decimal_places=2)
    stock_document = models.ForeignKey(
        StockDocument,
        on_delete=models.PROTECT,
        related_name='sales'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чек #{self.id} на {self.total_price}"


# =========================
# Товары в чеке
# =========================
class SaleItem(models.Model):
    sale = models.ForeignKey( Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey( Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total(self):
        return self.quantity * self.selling_price

class Customer(models.Model):
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    passport = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['phone', 'passport'],
                name='unique_phone_passport'
            )
        ]

    def __str__(self):
        return f"{self.name} {self.surname}"


# =========================
# Деньги (бухгалтерия)
# =========================
class Transaction(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    DEBT_STATUS = (
        ('open', 'Открыт'),
        ('closed', 'Закрыт'),
    )

    debt_status = models.CharField(
        max_length=10,
        choices=DEBT_STATUS,
        default='open'
    )
    debt_closed_at = models.DateTimeField(null=True, blank=True)

    PAYMENT_TYPE = (('cash', 'Наличные'), ('debt', 'В долг'))

    payment_type = models.CharField( max_length=10, choices=PAYMENT_TYPE )

    # Общая сумма по чеку
    total_amount = models.DecimalField( max_digits=12, decimal_places=2)

    # Сколько клиент заплатил сейчас
    paid_amount = models.DecimalField( max_digits=12, decimal_places=2, default=0)

    # Сколько осталось в долг
    debt_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    months = models.PositiveIntegerField(default=0)

    # Связь с чеком
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def recalc_amounts(self):
        if not self.schedules.exists():
            return
        total_paid = self.schedules.aggregate(
            s=models.Sum('paid_amount')
        )['s'] or Decimal('0.00')

        self.paid_amount = min(total_paid, self.total_amount)
        self.debt_amount = max(
            Decimal('0.00'),
            self.total_amount - self.paid_amount
        )
        if self.debt_amount <= 0:
            self.close_debt(commit=False)

        self.save(update_fields=['paid_amount', 'debt_amount', 'debt_status', 'debt_closed_at'])

    def close_debt(self, commit=True):
        self.debt_status = 'closed'
        self.debt_amount = Decimal('0.00')
        self.paid_amount = self.total_amount
        self.debt_closed_at = timezone.now()

        if commit:
            self.save(update_fields=[
                'debt_status',
                'debt_amount',
                'paid_amount',
                'debt_closed_at'
            ])
    def __str__(self):
        return f"{self.payment_type} - {self.total_amount}"


class DebtSchedule(models.Model):
    STATUS = (
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('overdue', 'Просрочен'),
    )

    transaction = models.ForeignKey(
        Transaction,
        related_name='schedules',
        on_delete=models.CASCADE
    )

    due_date = models.DateField()  # дата платежа (месяц)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # сколько нужно
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default='pending'
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(paid_amount__gte=0),
                name='paid_amount_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='amount_gt_0'
            ),
            models.UniqueConstraint(
                fields=['transaction', 'due_date'],
                name='unique_month_per_transaction'
            )
        ]

    def apply_payment(self, amount):
        self.paid_amount = min(self.amount, self.paid_amount + amount)

        if self.paid_amount >= self.amount:
            self.status = 'paid'
            self.paid_at = timezone.now()

        self.save(update_fields=['paid_amount', 'status', 'paid_at'])

    def __str__(self):
        return f"{self.transaction.id} | {self.due_date} | {self.amount}"
