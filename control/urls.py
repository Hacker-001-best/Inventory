from django.urls import path
from .views import *

urlpatterns = [
    # Продукты
    path('products/', ProductAPIView.as_view(), name='product-create'),
    path('products/<int:product_id>/', ProductAPIView.as_view(), name='product-update-delete'),
    path('products/barcode/<int:product_id>/', ProductBardcodePrintAPIView.as_view(), name='product-barcode'),

    # Продажи
    path('sales/', SaleAPIView.as_view(), name='sale-create'),
    path('sales/<int:sale_id>/', SaleAPIView.as_view(), name='sale-detail-cancel'),

    # Склад
    path('stocks/', CreateStockDocumentAPIView.as_view(), name='stock-create'),

    # Долги
    path('transactions/search/', TransactionsSearchAPIView.as_view(), name='transaction-search'),
    path('debts/pay/<int:transaction_id>/', PayDebtAPIView.as_view(), name='pay-debt'),

    # Кассиры
    path('cashiers/', CashierAPIView.as_view(), name='cashier-create-list'),
    path('cashiers/<int:cashier_id>/', CashierAPIView.as_view(), name='cashier-update-delete'),

    # Аутентификация
    path('logination/', LoginationAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
]