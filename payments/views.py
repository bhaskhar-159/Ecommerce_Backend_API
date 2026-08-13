from uuid import uuid4

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order

from .models import Payment
from .serializers import PaymentSerializer


class PaymentCreateAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        order_id = request.data.get("order")

        if not order_id:
            return Response(
                {
                    "error": "Order ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(
                id=order_id,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {
                    "error": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent payment for cancelled orders
        if order.status == "cancelled":
            return Response(
                {
                    "error": "Cannot create payment for a cancelled order."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent duplicate payment
        if Payment.objects.filter(order=order).exists():
            return Response(
                {
                    "error": "Payment already exists for this order."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = request.data.get(
            "payment_method"
        )

        if payment_method not in [
            "card",
            "upi",
            "cod",
        ]:
            return Response(
                {
                    "error": "Invalid payment method."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.create(
            order=order,
            user=request.user,
            amount=order.total_amount,
            payment_method=payment_method,
            status="pending",
        )

        serializer = PaymentSerializer(payment)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class PaymentProcessAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):

        try:
            payment = Payment.objects.select_related(
                "order"
            ).get(
                id=pk,
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {
                    "error": "Payment not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if payment.status != "pending":
            return Response(
                {
                    "error": (
                        f"Payment cannot be processed "
                        f"because its status is "
                        f"'{payment.status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simulate successful payment
        payment.status = "paid"
        payment.transaction_id = (
            f"TXN-{uuid4().hex[:12].upper()}"
        )

        payment.save(
            update_fields=[
                "status",
                "transaction_id",
                "updated_at",
            ]
        )

        # Update order status
        order = payment.order

        if order.status == "pending":
            order.status = "confirmed"

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )    
        
        
class PaymentListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        payments = Payment.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = PaymentSerializer(
            payments,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
        
class PaymentDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        try:
            payment = Payment.objects.get(
                id=pk,
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {
                    "error": "Payment not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,

            status=status.HTTP_200_OK
        )       
        
        
class PaymentRefundAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):

        try:
            payment = Payment.objects.select_related(
                "order"
            ).get(
                id=pk,
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {
                    "error": "Payment not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if payment.status != "paid":
            return Response(
                {
                    "error": (
                        f"Payment cannot be refunded "
                        f"because its status is "
                        f"'{payment.status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        order = payment.order

        if order.status not in [
            "pending",
            "confirmed",
            "cancelled",
        ]:
            return Response(
                {
                    "error": (
                        f"Payment cannot be refunded "
                        f"for an order with status "
                        f"'{order.status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.status = "refunded"

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )