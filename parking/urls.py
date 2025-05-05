from django.urls import path
from parking.views import payment_callback

urlpatterns = [
    path('payment/callback/', payment_callback, name='payment-callback'),
]