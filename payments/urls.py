from django.urls import path

from .views import (
    PaymentCreateAPIView,
    PaymentProcessAPIView,
    PaymentListAPIView,
    PaymentDetailAPIView,
    PaymentRefundAPIView,
)


urlpatterns = [
    path("create/", PaymentCreateAPIView.as_view(), name="payment-create"),
    path("<int:pk>/process/", PaymentProcessAPIView.as_view(), name="payment-process"),
    path("", PaymentListAPIView.as_view(), name="payment-list"),
    path("<int:pk>/", PaymentDetailAPIView.as_view(), name="payment-detail"),
    path("<int:pk>/refund/", PaymentRefundAPIView.as_view(), name="payment-refund"),
]