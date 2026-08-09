from django.urls import path

from .views import CartAPIView, CartItemCreateAPIView, CartItemDetailAPIView


urlpatterns = [
    path("", CartAPIView.as_view(), name="cart"),

    path("items/", CartItemCreateAPIView.as_view(), name="cart-item-create"),

    path("items/<int:pk>/", CartItemDetailAPIView.as_view(), name="cart-item-detail"),
]