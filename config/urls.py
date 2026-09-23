"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from core.views import (
    home,
    accept_order,
    start_preparing,
    mark_ready,
    out_for_delivery,
    mark_delivered,
    manage_products,
    product_list,
    product_create,
    product_update,
    product_deactivate,
    product_activate,
    confirm_delivery,
)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home),
    path("pedido/<int:order_id>/aceitar/", accept_order),
    path("pedido/<int:order_id>/preparar/", start_preparing),
    path("pedido/<int:order_id>/pronto/", mark_ready),
    path("pedido/<int:order_id>/entrega/", out_for_delivery),
    path("pedido/<int:order_id>/entregue/", mark_delivered),
    path("__debug__/", include("debug_toolbar.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("produtos/gerenciar/", manage_products),
    path("produtos/", product_list),
    path("produtos/novo/", product_create),
path(
    "produtos/<int:product_id>/editar/",
    product_update,
    name="product_update",
),

path(
    "produtos/<int:product_id>/inativar/",
    product_deactivate,
    name="product_deactivate",
),
path(
    "produtos/<int:product_id>/ativar/",
    product_activate,
    name="product_activate",
),

path(
    "seu-pedido/confirmar/<uuid:token>/",
    confirm_delivery,
    name="confirm_delivery",
),
]