from django.urls import path

from .views import (
    CheckoutAPIView,
    OrderListAPIView,
    OrderDetailAPIView,
    OrderCancelAPIView,
    OrderStatusUpdateAPIView,
)


urlpatterns = [
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
    path("", OrderListAPIView.as_view(), name="order-list"),
    path("<int:pk>/", OrderDetailAPIView.as_view(), name="order-detail"),
    path("<int:pk>/cancel/", OrderCancelAPIView.as_view(), name="order-cancel"),
    path("<int:pk>/status/", OrderStatusUpdateAPIView.as_view(), name="order-status-update"),
]