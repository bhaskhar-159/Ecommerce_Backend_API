from decimal import Decimal

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart

from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderStatusUpdateSerializer


class CheckoutAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        # 1. Get the user's cart
        try:
            cart = Cart.objects.get(
                user=request.user
            )
        except Cart.DoesNotExist:
            return Response(
                {
                    "error": "Cart not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Get cart items
        cart_items = cart.items.select_related("product").all()

        # 3. Check if cart is empty
        if not cart_items.exists():
            return Response(
                {
                    "error": "Your cart is empty."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Check stock for every product
        for cart_item in cart_items:

            if cart_item.quantity > cart_item.product.stock:
                return Response(
                    {
                        "error": (
                            f"Not enough stock for "
                            f"{cart_item.product.name}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 5. Calculate total
        total_amount = Decimal("0.00")

        for cart_item in cart_items:

            subtotal = (cart_item.product.price * cart_item.quantity)

            total_amount += subtotal

        # 6. Create Order
        order = Order.objects.create(
            user=request.user,
            status="pending",
            total_amount=total_amount
        )

        # 7. Create OrderItems and reduce stock
        for cart_item in cart_items:

            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )

            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save(
                update_fields=["stock"]
            )

        # 8. Clear the cart
        cart.items.all().delete()

        # 9. Serialize the order
        serializer = OrderSerializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
        
        
class OrderListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        orders = Order.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)        
        
        
class OrderDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        try:
            order = Order.objects.get(
                id=pk,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {
                    "error": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderSerializer(order)

        return Response(serializer.data, status=status.HTTP_200_OK)        
    
    
class OrderCancelAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):

        try:
            order = Order.objects.get(
                id=pk,
                user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {
                    "error": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Check whether the order can be cancelled
        if order.status not in ["pending", "confirmed"]:
            return Response(
                {
                    "error": (
                        f"Order cannot be cancelled "
                        f"because its status is '{order.status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore product stock
        for order_item in order.items.select_related("product").all():

            order_item.product.stock += order_item.quantity

            order_item.product.save(
                update_fields=["stock"]
            )

        # Change order status
        order.status = "cancelled"
        order.save(
            update_fields=["status", "updated_at"]
        )

        serializer = OrderSerializer(order)

        return Response(serializer.data, status=status.HTTP_200_OK)    
    
    
class OrderStatusUpdateAPIView(APIView):

    permission_classes = [IsAdminUser]

    def patch(self, request, pk):

        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response(
                {
                    "error": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderStatusUpdateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data["status"]

        allowed_transitions = {
            "pending": ["confirmed"],
            "confirmed": ["shipped"],
            "shipped": ["delivered"],
            "delivered": [],
            "cancelled": [],
        }

        if new_status not in allowed_transitions[order.status]:
            return Response(
                {
                    "error": (
                        f"Cannot change order status "
                        f"from '{order.status}' "
                        f"to '{new_status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )   

        order.status = new_status

        order.save(
            update_fields=["status", "updated_at"]
        )

        order.save(
            update_fields=["status", "updated_at"]
        )

        response_serializer = OrderSerializer(order)

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK
        )    
    