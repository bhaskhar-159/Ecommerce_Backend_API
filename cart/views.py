from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)

        serializer = CartSerializer(cart)

        return Response(serializer.data)


class CartItemCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        cart, created = Cart.objects.get_or_create(user=request.user)

        product_id = request.data.get("product")
        quantity = request.data.get("quantity", 1)

        if not product_id:
            return Response(
                {
                    "error": "Product ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "Quantity must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {
                    "error": "Quantity must be greater than zero."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id)

        if product.stock < quantity:
            return Response(
                {
                    "error": "Not enough stock available."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": quantity
            }
        )

        if not created:

            new_quantity = cart_item.quantity + quantity

            if new_quantity > product.stock:
                return Response(
                    {
                        "error": "Requested quantity exceeds available stock."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):

        cart_item = get_object_or_404(CartItem, id=pk, cart__user=request.user)

        quantity = request.data.get("quantity")

        if quantity is None:
            return Response(
                {
                    "error": "Quantity is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "Quantity must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {
                    "error": "Quantity must be greater than zero."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity > cart_item.product.stock:
            return Response(
                {
                    "error": "Requested quantity exceeds available stock."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response(serializer.data)

    def delete(self, request, pk):

        cart_item = get_object_or_404(CartItem, id=pk, cart__user=request.user)

        cart_item.delete()

        return Response(
            {
                "message": "Item removed from cart."
            },
            status=status.HTTP_204_NO_CONTENT
        )
