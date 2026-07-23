from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Category,
    Product,
    StockDocument,
    StockMovement,
    Sale,
    SaleItem,
    Customer,
    Transaction,
    DebtSchedule,
)

# =========================
# Пользователь
# =========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Роль', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')


# =========================
# Категория
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


# =========================
# Товар
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'barcode',
        'category',
        'status',
        'quantity',
        'selling_price',
        'created_at'
    )
    list_filter = ('status', 'category')
    search_fields = ('name', 'barcode')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status', 'quantity')


# =========================
# Движение склада
# =========================
class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0


@admin.register(StockDocument)
class StockDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'movement_type', 'user', 'created_at')
    list_filter = ('movement_type',)
    inlines = (StockMovementInline,)
    readonly_fields = ('created_at',)


# =========================
# Продажа
# =========================
class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('purchase_price', 'selling_price')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'cashier', 'total_price', 'status', 'created_at')
    list_filter = ('status',)
    inlines = (SaleItemInline,)
    readonly_fields = ('created_at', 'canceled_at')


# =========================
# Клиент
# =========================
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'surname', 'phone', 'passport')
    search_fields = ('name', 'surname', 'phone', 'passport')
    list_filter = ('surname',)
    ordering = ('surname',)


# =========================
# График платежей (inline)
# =========================
class DebtScheduleInline(admin.TabularInline):
    model = DebtSchedule
    extra = 0
    readonly_fields = ('paid_amount', 'status', 'paid_at')
    ordering = ('due_date',)


# =========================
# Транзакция (долг)
# =========================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'payment_type',
        'customer',
        'total_amount',
        'paid_amount',
        'debt_amount',
        'debt_status',
        'created_at'
    )
    list_filter = ('payment_type', 'debt_status')
    search_fields = (
        'id',
        'customer__phone',
        'customer__passport',
        'customer__name',
        'customer__surname',
    )
    readonly_fields = ('created_at', 'debt_closed_at')
    inlines = (DebtScheduleInline,)


# =========================
# График платежей (отдельно)
# =========================
@admin.register(DebtSchedule)
class DebtScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'transaction',
        'due_date',
        'amount',
        'paid_amount',
        'status',
        'paid_at'
    )
    list_filter = ('status', 'due_date')
    search_fields = ('transaction__id',)
    readonly_fields = ('paid_at',)
