from django.urls import path, include
from .views import *
from rest_framework import routers

router = routers.DefaultRouter()
router.register('productos',ProductoViewset)
router.register('CarroItem',CarroItemViewset)
router.register('CarroCompras',CarroComprasViewset)
router.register('marca', MarcaViewset)  # Registrar el ViewSet de Marca
router.register('compra-item', CompraItemViewset)  # Registrar el ViewSet de CompraItem


urlpatterns = [

    path('compra-confirmada/', compra_confirm, name='compra_confirmada'),
    # API
    path('api/', include(router.urls)),




    path('', index, name = "index"),
    path('paypal-confirm/', paypal_confirm, name='paypal_confirm'),
    path('indexapi/', indexapi, name = "indexapi"),
    path('blog/', blog, name = "blog"),
    path('blogapi/', blogapi, name = "blogapi"),
    path('cart/', cart, name = "cart"),
    path('confirmar_pagos/', confirmar_pagos, name='confirmar_pagos'),
    path('cartUser/', cartUser, name = "cartUser"),
    path('category/', category, name = "category"),
    path('checkout/', checkout, name = "checkout"),
    path('confirmation/', confirmation, name = "confirmation"),
    path('order_history/', order_history, name="order_history"),
    path('contact/', contact,name = "contact"),

    path('indexUser/', indexUser,name = "indexUser"),
    path('indexUserSubscito/', indexUserSubscito, name = "indexUserSubscito"),
    path('login/', login,name = "login"),
    path('perfil/', perfil,name = "perfil"),
    path('registro/', registro,name = "registro"),
    path('singleblog/', singleblog, name="singleblog"),
    path('singleproduct/<id>/', singleproduct, name="singleproduct"),
    path('subsForm/', subsForm,name = "subsForm"),
    path('trackingorder/', trackingorder,name = "tracking-order"),
    path('asignar-roles/', asignar_roles, name='asignar_roles'),

    


    path('forgot-password/', forgot_password, name='forgot_password'),
    path('password_reset/<str:token>/', password_reset, name='password_reset'),
    path('email-sent/', email_sent, name='email_sent'),
    #path('remover_grupo/<int:usuario_id>/<int:grupo_id>/', remover_grupo, name='remover_grupo'),
    



    #CRUD
    path('add/', add,name = "add"),
    path('update/<id>/', update,name = "update"),
    path('delete/<id>/', delete, name= "delete"),
    path('cartadd/<id>/', cartadd, name="cartadd"),
    path('cart/cartdel/<id>/', cartdel, name="cartdel"),
    path('cart/cartadd/<id>',cartadd, name="cartaddd"),
    path('cart/cartdelete/<id>',cartdelete, name="cartdelete"),
    path('add_compra/', add_compra, name="add_compra"),
    path('suscribir/<id>/', agregar_suscriptor, name="suscribir"),
    
    

    path('productos_bodega/', productos_bodega, name='productos_bodega'),
    path('gestionar_pedidos/', gestionar_pedidos, name='gestionar_pedidos'),
    path('actualizar_pedido/<int:pedido_id>/', actualizar_pedido, name='actualizar_pedido'),
    path('ordenes_pedidos/', ordenes_pedidos, name='ordenes_pedidos'),
    path('preparar_pedidos/', preparar_pedidos, name='preparar_pedidos'),
    path('ordenar_pedidos/', ordenar_pedidos, name='ordenar_pedidos'),
    path('confirmar_pagos/', confirmar_pagos, name='confirmar_pagos'),
    path('registrar_entregas/', registrar_entregas, name='registrar_entregas'),

    path('aceptar-pedido/<int:pedido_id>/', aceptar_pedido, name='aceptar_pedido'),
    path('rechazar-pedido/<int:pedido_id>/', rechazar_pedido, name='rechazar_pedido'),
    path('ordenar_pedidos/', ordenar_pedidos, name='ordenar_pedidos'),
    path('ordenes_pedidos/', ordenes_pedidos, name='ordenes_pedidos'),
    path('ReportesVentas/', ReportesVentas, name='ReportesVentas'),
    path('transferencia_bancaria/', transferencia_bancaria, name='transferencia_bancaria'),
    path('monedas_data/', monedas_data, name='monedas_data'),
]

