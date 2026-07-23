from datetime import datetime
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.db.models import Q
from .permissions import IsCashier, IsAdmin
from .models import Product, Sale, Transaction
from .serializers import (
    ProductCreateSerializer, ProductUpdateSerializer, 
    SaleCreateSerializer, SaleCancelSerializer, SaleDetailSerializer,
    StockDocumentCreateSerializer, TransactionSearchFilterSerializer,
    TransactionResultSerializer, PayDebtSerializer, CashierCreateSerializer,
    CashierListSerializer, CashierUpdateSerializer
)
from .services import generate_barcode_image

@method_decorator(csrf_exempt, name='dispatch')
class ProductAPIView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=ProductCreateSerializer,
        responses={201: ProductCreateSerializer}
    )
    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        return Response({
            'status': 'ok',
            'product_id': product.id,
            'barcode': product.barcode
        })

    def patch(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'status': 'error', 'message': 'product_id is required'},
                status=400
            )
        product = get_object_or_404(Product, id=product_id)
        serializer = ProductUpdateSerializer(
            product,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'status': 'ok',
            'product_id': product.id
        })

    def delete(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        product.status = 'archived'
        product.save(update_fields=['status'])
        return Response({'status': 'ok'})

class SaleAPIView(APIView):
    permission_classes = [IsCashier]

    def post(self, request):
        serializer = SaleCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()

        return Response({
            'status': 'ok',
            'sale_id': sale.id,
            'total_price': str(sale.total_price)
        })

    def delete(self, request, sale_id):
        serializer = SaleCancelSerializer(
            data={'sale_id': sale_id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'status': 'ok',
            'message': 'Чек отменён, товар возвращён на склад'
        })

    def get(self, request, sale_id):
        sale = get_object_or_404(Sale, id=sale_id)

        # Используем select_related для оптимизации, если связь 1-к-1
        tx = Transaction.objects.filter(sale=sale).select_related('customer').first()

        items = []
        for item in sale.items.select_related('product'):
            items.append({
                'name': item.product.name,
                'qty': item.quantity,
                'price': item.selling_price,
                'total': item.quantity * item.selling_price
            })

        data = {
            'sale_id': sale.id,
            'status': sale.status,
            'date': sale.created_at,
            'cashier': sale.cashier.username if sale.cashier else '',
            'items': items,
            'total': sale.total_price,
            'paid': tx.paid_amount if tx else Decimal('0.00'),
            'debt': tx.debt_amount if tx else Decimal('0.00'),
            'payment_type': tx.payment_type if tx else '',
            'customer': {
                'name': tx.customer.name if tx and tx.customer else '',
                'surname': tx.customer.surname if tx and tx.customer else '',
                'phone': tx.customer.phone if tx and tx.customer else '',
            }
        }

        serializer = SaleDetailSerializer(data)
        return Response(serializer.data)


class CreateStockDocumentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StockDocumentCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        return Response({
            'status': 'ok',
            'document_id': document.id
        })




class ProductBardcodePrintAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request,product_id):
        product = get_object_or_404(Product, id=product_id)

        barcode_img = generate_barcode_image(product.barcode)

        return Response({
            'name': product.name,
            'barcode': product.barcode,
            'barcode_image': barcode_img,
            'price': str(product.selling_price),
            'unit': product.unit
        })



class TransactionsSearchAPIView(APIView):
    permission_classes = [IsCashier]
    # Добавляем стандартную пагинацию DRF
    pagination_class = PageNumberPagination

    def post(self, request):
        paginator = self.pagination_class()
        
        filter_serializer = TransactionSearchFilterSerializer(
            data=request.data
        )
        filter_serializer.is_valid(raise_exception=True)
        data = filter_serializer.validated_data

        qs = Transaction.objects.select_related(
            'customer', 'sale'
        ).prefetch_related(
            'schedules'
        ).order_by('-created_at')

        if 'date_from' in data:
            qs = qs.filter(created_at__date__gte=data['date_from'])

        if 'date_to' in data:
            qs = qs.filter(created_at__date__lte=data['date_to'])

        if 'query' in data:
            qs = qs.filter(
                Q(id__icontains=data['query']) |
                Q(customer__phone__icontains=data['query']) |
                Q(customer__passport__icontains=data['query'])
            )

        if 'debt_status' in data:
            qs = qs.filter(debt_status=data['debt_status'])

        if 'sale_status' in data:
            qs = qs.filter(sale__status=data['sale_status'])

        # Применяем пагинацию к QuerySet
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = TransactionResultSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PayDebtAPIView(APIView):
    permission_classes = [IsCashier]

    def post(self, request, transaction_id):
        serializer = PayDebtSerializer(
            data=request.data,
            context={'transaction_id': transaction_id}
        )

        serializer.is_valid(raise_exception=True)
        tx, paid_amount = serializer.save()

        return Response({
            'paid_now': str(paid_amount),
            'remaining_debt': str(tx.debt_amount),
            'debt_status': tx.debt_status
        })

class LoginationAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'success': 'error', 'message': 'Hemmesini doldyr!'},
                status=400
            )

        user = authenticate(request, username=username, password=password)

        if not user:
            return Response(
                {'success': 'error', 'message': 'Yalnys at ya-da parol!'},
                status=401
            )

        login(request, user)

        return Response({
            'success': 'ok',
            'username': user.username,
            'role': user.role
        })


User = get_user_model()


class CashierAPIView(APIView):
    permission_classes = [IsAdmin]

    # ➕ создать кассира
    def post(self, request):
        serializer = CashierCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'success': 'ok'})

    # 📋 список кассиров
    def get(self, request):
        cashiers = User.objects.filter(
            role='cashier',
            owner=request.user
        )

        serializer = CashierListSerializer(cashiers, many=True)
        return Response(serializer.data)

    # ✏️ обновить кассира
    def patch(self, request, cashier_id):
        cashier = get_object_or_404(
            User,
            id=cashier_id,
            role='cashier',
            owner=request.user
        )

        if cashier == request.user:
            return Response(
                {'error': 'Нельзя менять самого себя'},
                status=400
            )

        serializer = CashierUpdateSerializer(
            cashier,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'success': 'ok'})

    # ❌ удалить кассира
    def delete(self, request, cashier_id):
        cashier = get_object_or_404(
            User,
            id=cashier_id,
            role='cashier',
            owner=request.user
        )

        cashier.delete()
        return Response({'success': 'ok'})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        logout(request)
        return Response({'success': 'ok'})
