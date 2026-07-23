from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.db import transaction
from .models import *
from .services import *

class ProductCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all()
    )

    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'purchase_price',
            'selling_price',
            'unit',
            'photo',
        )

    def create(self, validated_data):
        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            product.barcode = generate_barcode(product.id, product.name)
            product.save(update_fields=['barcode'])
        return product

class ProductUpdateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Product
        fields = (
            'product_id',
            'name',
            'category',
            'purchase_price',
            'selling_price',
            'unit',
            'photo',
        )

    def update(self, instance, validated_data):
        validated_data.pop('product_id', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

class SaleItemSerializer(serializers.Serializer):
    barcode = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)

class SaleCreateSerializer(serializers.Serializer):
    items = SaleItemSerializer(many=True)

    payment_type = serializers.ChoiceField(choices=['cash', 'debt'])
    paid_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0
    )
    month = serializers.IntegerField(required=False, min_value=1)

    customer_name = serializers.CharField(required=False)
    customer_surname = serializers.CharField(required=False)
    customer_phone = serializers.CharField(required=False)
    customer_passport = serializers.CharField(required=False)

    def validate(self, data):
        if data['payment_type'] == 'debt':
            required = [
                'customer_name',
                'customer_surname',
                'customer_phone',
                'customer_passport',
                'month'
            ]
            for field in required:
                if not data.get(field):
                    raise serializers.ValidationError(
                        {field: 'Обязательно для продажи в долг'}
                    )
        return data

    def create(self, validated_data):
        request = self.context['request']

        items = validated_data['items']
        payment_type = validated_data['payment_type']
        paid_amount = validated_data.get('paid_amount', Decimal('0'))
        month = validated_data.get('month', 0)

        with transaction.atomic():

            customer = None
            if payment_type == 'debt':
                customer = get_or_create_customer_for_debt(
                    validated_data['customer_name'],
                    validated_data['customer_surname'],
                    validated_data['customer_phone'],
                    validated_data['customer_passport'],
                )

            stock_doc = StockDocument.objects.create(
                movement_type='out',
                user=request.user,
                comment='Продажа'
            )

            sale = Sale.objects.create(
                cashier=request.user,
                total_price=0,
                stock_document=stock_doc
            )

            total = Decimal('0')

            for item in items:
                product = Product.objects.select_for_update().get(
                    barcode=item['barcode'],
                    status='active'
                )

                if product.quantity < item['quantity']:
                    raise serializers.ValidationError(
                        f'Недостаточно товара: {product.name}'
                    )

                product.quantity -= item['quantity']
                product.save(update_fields=['quantity'])

                StockMovement.objects.create(
                    document=stock_doc,
                    product=product,
                    quantity=item['quantity']
                )

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=item['quantity'],
                    purchase_price=product.purchase_price,
                    selling_price=product.selling_price
                )

                total += product.selling_price * item['quantity']

            sale.total_price = total
            sale.save(update_fields=['total_price'])

            if payment_type == 'cash':
                paid_amount = total


            tx = Transaction.objects.create(
                sale=sale,
                customer=customer,
                payment_type=payment_type,
                total_amount=total,
                paid_amount=paid_amount,
                months=month
            )

            if payment_type == 'debt':
                create_debt_plan(tx.id)

        return sale

class StockItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class StockDocumentCreateSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=['in', 'out'])
    items = StockItemSerializer(many=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('Список товаров пуст')
        return items

    def create(self, validated_data):
        request = self.context['request']

        movement_type = validated_data['movement_type']
        items = validated_data['items']
        comment = validated_data.get('comment', '')

        with transaction.atomic():
            document = StockDocument.objects.create(
                movement_type=movement_type,
                user=request.user,
                comment=comment
            )

            for item in items:
                product = Product.objects.select_for_update().get(
                    id=item['product_id']
                )

                qty = item['quantity']

                if movement_type == 'out' and product.quantity < qty:
                    raise serializers.ValidationError(
                        f'Недостаточно товара: {product.name}'
                    )

                if movement_type == 'in':
                    product.quantity += qty
                else:
                    product.quantity -= qty

                product.save(update_fields=['quantity'])

                StockMovement.objects.create(
                    document=document,
                    product=product,
                    quantity=qty
                )

        return document

class TransactionSearchFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    query = serializers.CharField(required=False, allow_blank=True)
    debt_status = serializers.ChoiceField(
        choices=['open', 'closed'],
        required=False
    )
    sale_status = serializers.ChoiceField(
        choices=['active', 'canceled'],
        required=False
    )

class DebtScheduleSerializer(serializers.Serializer):
    due_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()


class TransactionResultSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(source='id')
    created_at = serializers.DateTimeField()
    payment_type = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    debt_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    debt_status = serializers.CharField()
    sale_status = serializers.SerializerMethodField()

    need_to_pay_now = serializers.SerializerMethodField()
    overdue_amount = serializers.SerializerMethodField()
    overdue_months = serializers.SerializerMethodField()

    customer = serializers.SerializerMethodField()
    debt_schedules = serializers.SerializerMethodField()

    def get_sale_status(self, obj):
        return obj.sale.status if obj.sale else ''

    def get_customer(self, obj):
        if not obj.customer:
            return None
        return {
            'name': obj.customer.name,
            'surname': obj.customer.surname,
            'phone': obj.customer.phone,
            'passport': obj.customer.passport,
        }

    def get_debt_schedules(self, obj):
        today = date.today()
        result = []

        for s in obj.schedules.all().order_by('due_date'):
            remaining = s.amount - s.paid_amount

            result.append({
                'due_date': s.due_date,
                'amount': s.amount,
                'paid_amount': s.paid_amount,
                'remaining': remaining,
                'status': s.status,
            })

        return result

    def get_need_to_pay_now(self, obj):
        today = date.today()
        total = Decimal('0.00')

        for s in obj.schedules.all():
            if s.status in ('pending', 'overdue') and s.due_date <= today:
                total += (s.amount - s.paid_amount)

        return total

    def get_overdue_amount(self, obj):
        today = date.today()
        total = Decimal('0.00')

        for s in obj.schedules.all():
            if s.due_date < today and s.status != 'paid':
                total += (s.amount - s.paid_amount)

        return total

    def get_overdue_months(self, obj):
        today = date.today()
        return sum(
            1 for s in obj.schedules.all()
            if s.due_date < today and s.status != 'paid'
        )

class PayDebtSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )

    def save(self, **kwargs):
        transaction_id = self.context['transaction_id']

        with transaction.atomic():
            tx = get_object_or_404(
                Transaction.objects.select_for_update(),
                id=transaction_id
            )

            amount = min(self.validated_data['amount'], tx.debt_amount)
            rest = amount

            schedules = tx.schedules.select_for_update().filter(
                status__in=['pending', 'overdue']
            ).order_by('due_date')

            for s in schedules:
                if rest <= 0:
                    break

                need = s.amount - s.paid_amount
                pay = min(rest, need)

                s.apply_payment(pay)
                rest -= pay

        tx.refresh_from_db()
        return tx, amount


User = get_user_model()


class CashierCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Ulanyjy eyyam doredilen!')
        return value

    def create(self, validated_data):
        request = self.context['request']

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                phone=validated_data['phone'],
                role='cashier',              # 🔒 жёстко
                owner=request.user           # 🔒 привязка к админу
            )

        return user

class CashierUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False, write_only=True)

    def update(self, instance, validated_data):
        if 'username' in validated_data:
            instance.username = validated_data['username']

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()
        return instance

class CashierListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')

class SaleCancelSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()

    def validate_sale_id(self, value):
        if not Sale.objects.filter(id=value, status='active').exists():
            raise serializers.ValidationError(
                'Чек не найден или уже отменён'
            )
        return value

    def save(self):
        request = self.context['request']
        sale_id = self.validated_data['sale_id']

        with transaction.atomic():

            sale = Sale.objects.select_for_update().get(
                id=sale_id,
                status='active'
            )

            # 1️⃣ складской документ возврата
            stock_doc = StockDocument.objects.create(
                movement_type='in',
                user=request.user,
                comment=f'Возврат по отмене чека #{sale.id}'
            )

            # 2️⃣ возврат товаров
            for item in sale.items.select_related('product'):
                product = item.product
                product.quantity += item.quantity
                product.save(update_fields=['quantity'])

                StockMovement.objects.create(
                    document=stock_doc,
                    product=product,
                    quantity=item.quantity
                )

            # 3️⃣ отмена чека
            sale.status = 'canceled'
            sale.canceled_at = timezone.now()
            sale.save(update_fields=['status', 'canceled_at'])

            # 4️⃣ закрытие долгов
            for tx in Transaction.objects.filter(
                sale=sale,
                debt_status='open'
            ):
                tx.debt_status = 'closed'
                tx.debt_amount = Decimal('0.00')
                tx.paid_amount = Decimal('0.00')
                tx.debt_closed_at = timezone.now()
                tx.save(update_fields=[
                    'debt_status',
                    'debt_amount',
                    'paid_amount',
                    'debt_closed_at'
                ])

        return sale

class SaleItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    qty = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class SaleDetailSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()
    status = serializers.CharField()
    date = serializers.DateTimeField()
    cashier = serializers.CharField()
    items = SaleItemSerializer(many=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    debt = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_type = serializers.CharField()
    customer = serializers.DictField()
