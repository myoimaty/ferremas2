from django.shortcuts import render, redirect
from .models import *
from .forms import *
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from rest_framework import viewsets
from .serializers import *
import requests 
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import Group
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.timezone import make_aware, utc
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.http import HttpResponse
from openpyxl import Workbook
from datetime import datetime


#LOGICAS API

API_URL = "http://127.0.0.1:5000"


def checkdata(request):
    if request.method == 'POST':
        form = Checkdata(request.POST)
        if form.is_valid():
            form.save()
            return redirect('core/checkout')  # Redirige a una página de éxito
    else:
        form = Checkdata()
    
    return render(request, 'core/checkout.html', {'form': form})


@login_required
def checkout(request):
    carro_compras = CarroCompras.objects.get(usuario=request.user)
    items = carro_compras.items.all()
    
    items_data = []
    total_productos = 0

    for item in items:
        producto_detalles = obtener_detalles_producto(item.producto_id_api)
        if producto_detalles:
            precio = float(producto_detalles.get('precio', 0))
            subtotal = precio * item.cantidad
            total_productos += subtotal
            items_data.append({
                'producto': producto_detalles,
                'cantidad': item.cantidad,
                'subtotal': subtotal,
                'id': item.producto_id_api
            })

    
    total_final = total_productos 

    # Obtener valor del dólar
    respuesta = requests.get('https://mindicador.cl/api/dolar')
    if respuesta.status_code == 200:
        valor_usd = float(respuesta.json()['serie'][0]['valor'])
        total_final_usd = total_final / valor_usd if valor_usd else 0
    else:
        valor_usd = 0
        total_final_usd = 0


    data = {
        'items': items_data,
        'total_productos': total_productos,
        'total_final': total_final,
        'total_final_usd': round(total_final_usd, 2)
    }

    if request.method == 'POST':
        # Crear la compra
        compra = Compra.objects.create(usuario=request.user, total=total_final)
        for item in items:
            CompraItem.objects.create(compra=compra, producto=item.producto, cantidad=item.cantidad)
        
        # Crear el pedido
        Pedido = Pedido.objects.create(
            usuario=request.user,
            total=total_final,
            estado='pendiente'  # O cualquier otro estado inicial que desees
        )

        carro_compras.items.clear()

        messages.success(request, "¡Pago realizado correctamente!")
        return redirect('order_history')

    return render(request, 'core/checkout.html', data)

def obtener_detalles_producto(producto_id_api):
    url = f"http://127.0.0.1:5000/productos/{producto_id_api}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def paypal_confirm(request):
    if request.method == 'POST':
        paypal_payment_id = request.POST.get('paypal_payment_id')
        if not paypal_payment_id:
            messages.error(request, "ID de pago de PayPal no encontrado.")
            return redirect('checkout')
        
        try:
            # Obtener el carrito de compras del usuario
            carro_compras = CarroCompras.objects.get(usuario=request.user)

            # Calcular el total de la compra
            total_compra = 0
            items = carro_compras.items.all()
            for item in items:
                response = requests.get(f"{API_URL}/productos/{item.producto_id_api}")
                if response.status_code == 200:
                    producto = response.json()
                    precio = float(producto.get('precio', 0))
                    cantidad = item.cantidad
                    subtotal = precio * cantidad
                    total_compra += subtotal
                else:
                    print(f"Error al obtener producto {item.producto_id_api}")

            # Crear una instancia de compra con el total calculado
            compra = Compra.objects.create(usuario=request.user, total=total_compra)

            # Crear una instancia de pedido con los datos necesarios
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=total_compra,
                estado='aprobado'  # Establece el estado del pedido a "aprobado"
            )

            # Procesar los elementos del carrito
            for item in items:
                producto_id_api = item.producto_id_api
                cantidad = item.cantidad
                
                # Llamar a la función para actualizar el stock en la API
                try:
                    actualizar_stock(producto_id_api, cantidad)
                except Exception as e:
                    print(f"Error al actualizar el stock para el producto {producto_id_api}: {e}")
                    messages.error(request, f"Error al actualizar el stock para el producto {producto_id_api}: {e}")

                response = requests.get(f"{API_URL}/productos/{producto_id_api}")
                if response.status_code == 200:
                    producto = response.json()
                    compra_item = CompraItem.objects.create(
                        compra=compra,
                        carro_item=item
                    )
                else:
                    print(f"No se pudo obtener información del producto {producto_id_api} de la API")

                item.delete()

            carro_compras.delete()

            messages.success(request, "¡Pago realizado correctamente!")
            return redirect('index')
        except Exception as e:
            print(f"Error al procesar la compra: {e}")
            messages.error(request, "Ocurrió un error al procesar la compra. Por favor, inténtalo de nuevo más tarde.")
            return redirect('index')

    return redirect('/')

@login_required
def compra_confirm(request):
    try:
        # Obtener el carrito de compras del usuario
        carro_compras = CarroCompras.objects.get(usuario=request.user)

        # Calcular el total de la compra
        total_compra = 0
        items = carro_compras.items.all()
        for item in items:
            response = requests.get(f"{API_URL}/productos/{item.producto_id_api}")
            if response.status_code == 200:
                producto = response.json()
                precio = float(producto.get('precio', 0))
                cantidad = item.cantidad
                subtotal = precio * cantidad
                total_compra += subtotal
            else:
                print(f"Error al obtener producto {item.producto_id_api}")

        # Crear una instancia de compra con el total calculado
        compra = Compra.objects.create(usuario=request.user, total=total_compra)

        # Crear una instancia de pedido con los datos necesarios
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total_compra
        )

        # Procesar los elementos del carrito
        for item in items:
            producto_id_api = item.producto_id_api
            cantidad = item.cantidad
            
            
            # Llamar a la función para actualizar el stock en la API
            try:
                actualizar_stock(producto_id_api, cantidad)
            except Exception as e:
                # Manejar cualquier error que pueda ocurrir durante la actualización del stock
                print(f"Error al actualizar el stock para el producto {producto_id_api}: {e}")
                # Puedes agregar un mensaje de error si lo deseas
                messages.error(request, f"Error al actualizar el stock para el producto {producto_id_api}: {e}")

            # Obtener los datos del producto de la API
            response = requests.get(f"{API_URL}/productos/{producto_id_api}")
            if response.status_code == 200:
                producto = response.json()
                # Guardar los datos del producto en la tabla CompraItem
                compra_item = CompraItem.objects.create(
                    compra=compra,
                    carro_item=item
                )
            else:
                print(f"No se pudo obtener información del producto {producto_id_api} de la API")
                # Agregar mensaje de registro para indicar que no se pudo obtener información del producto

            # Eliminar el elemento del carrito
            item.delete()

        # Eliminar el carrito después de la compra
        carro_compras.delete()

        # Redirigir al usuario a la página de inicio
        return redirect('index')
    except Exception as e:
        # Manejar cualquier otra excepción que pueda ocurrir
        print(f"Error al procesar la compra: {e}")
        messages.error(request, "Ocurrió un error al procesar la compra. Por favor, inténtalo de nuevo más tarde.")
        return redirect('index')  # Redirigir al usuario a la página de inicio en caso de error
    

        
def actualizar_stock(producto_id_api, cantidad):
    try:
        # Construir la URL de la API para actualizar el stock del producto
        url = f"http://127.0.0.1:5000/productos/{producto_id_api}"
        
        # Obtener el stock actual del producto desde la API
        response = requests.get(url)
        if response.status_code == 200:
            producto = response.json()
            stock_actual = producto.get('stock')
            if stock_actual is not None:
                # Calcular el nuevo stock restando la cantidad comprada al stock actual
                nuevo_stock = stock_actual - cantidad
                
                # Actualizar el stock del producto llamando al endpoint PATCH de la API
                response = requests.patch(f"{url}?stock={nuevo_stock}")

                # Verificar si la solicitud fue exitosa
                if response.status_code == 200:
                    # Retornar la respuesta JSON de la API si es necesario
                    return response.json()
                else:
                    # Manejar cualquier error en caso de que la solicitud no sea exitosa
                    raise Exception(f"Error al actualizar el stock del producto {producto_id_api}: {response.text}")
            else:
                raise Exception(f"No se pudo obtener el stock actual del producto {producto_id_api} de la API")
        else:
            raise Exception(f"No se pudo obtener el producto {producto_id_api} de la API")
    except Exception as e:
        # Manejar cualquier excepción que pueda ocurrir durante el proceso
        raise Exception(f"Error al actualizar el stock del producto {producto_id_api}: {str(e)}")
    

def add(request):
    data = {
        'form': ProductoForm()
    }
    if request.method == 'POST':
        formulario = ProductoForm(request.POST, files=request.FILES)
        if formulario.is_valid():
            # Extraer datos del formulario
            producto_data = {
                'id': formulario.cleaned_data['id'],  # Cambiado a 'id'
                'nombre': formulario.cleaned_data['nombre'],
                'cod_marca': formulario.cleaned_data['cod_marca'],
                'nombre_marca': formulario.cleaned_data['nombre_marca'],
                'precio': formulario.cleaned_data['precio'],
                'stock': formulario.cleaned_data['stock'],
                'imagen_url': formulario.cleaned_data.get('imagen_url')  # Si tienes campo para la URL de la imagen
            }

            # Enviar datos a la API
            response = requests.post(f"{API_URL}/productos", json=producto_data)

            if response.status_code == 200:
                messages.success(request, "Producto almacenado correctamente")
                return redirect('index')  # Redirigir a la página de productos o a donde prefieras
            else:
                messages.error(request, f"Error al almacenar el producto: {response.text}")

    return render(request, 'core/add-product.html', data)

def update(request, id):
    try:
        if request.method == 'POST':
            form = ProductoForm(request.POST)  # Obtener los datos del formulario enviado por el usuario
            if form.is_valid():
                # Si el formulario es válido, enviar los datos actualizados a la API para actualizar el producto
                url = f"http://127.0.0.1:5000/productos/{id}"
                response = requests.put(url, json=form.cleaned_data)
                if response.status_code == 200:
                    messages.success(request, '¡El producto se ha actualizado correctamente!')
                    # Si la actualización en la API fue exitosa, redirigir al usuario a la página de detalles del producto
                    return redirect('index')
                else:
                    # Manejar el caso en que la actualización en la API falle
                    data = {'error': 'No se pudo actualizar el producto en la API'}
                    return render(request, 'core/update-product.html', data)
        else:
            # Si la solicitud no es POST, obtener los detalles del producto de la API y mostrar el formulario
            url = f"http://127.0.0.1:5000/productos/{id}"
            response = requests.get(url)
            if response.status_code == 200:
                producto = response.json()
                data = {'form': ProductoForm(initial=producto), 'id': id}
                return render(request, 'core/update-product.html', data)
            else:
                data = {'error': 'No se pudo obtener el producto de la API'}
                return render(request, 'core/update-product.html', data)
    except Exception as e:
        # Manejar cualquier error que ocurra durante el proceso
        data = {'error': str(e)}
        return render(request, 'core/update-product.html', data)

def delete(request, id):
    try:
        # Realizar la solicitud DELETE a la API para eliminar el producto
        url = f"http://127.0.0.1:5000/productos/{id}"
        response = requests.delete(url)
        
        if response.status_code == 200:
            # Si la eliminación en la API fue exitosa, redirigir al usuario al índice con un mensaje de éxito
            success_message = '¡El producto se ha eliminado correctamente!'
            return redirect('index')
        else:
            # Manejar el caso en que la eliminación en la API falle
            data = {'error': 'No se pudo eliminar el producto en la API'}
            return render(request, 'core/index.html', data)
    except Exception as e:
        # Manejar cualquier error que ocurra durante el proceso
        data = {'error': str(e)}
        return render(request, 'core/index.html', data)

def cart(request):
    try:
        carro_compras = CarroCompras.objects.get(usuario=request.user)
        items = carro_compras.items.all()
    except CarroCompras.DoesNotExist:
        items = []

    total = 0
    items_data = []

    for item in items:
        response = requests.get(f"{API_URL}/productos/{item.producto_id_api}")
        if response.status_code == 200:
            producto = response.json()
            precio = float(producto.get('precio', 0))
            cantidad = item.cantidad

            if precio and cantidad:
                subtotal = precio * cantidad
                total += subtotal
                items_data.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'subtotal': subtotal,
                    'id': item.producto_id_api
                })
            else:
                print(f"Precio o cantidad no válidos para el producto {producto['nombre']}")
        else:
            print(f"Error al obtener producto {item.producto_id_api}")

    # Obtener valor del dólar
    respuesta = requests.get('https://mindicador.cl/api/dolar')
    if respuesta.status_code == 200:
        valor_usd = float(respuesta.json()['serie'][0]['valor'])
        valor_total = total / valor_usd if valor_usd else 0
    else:
        valor_usd = 0
        valor_total = 0

    data = {
        'total': round(total, 2),
        'total_usd': round(valor_total, 2),
        'items': items_data,
    }

    print(f"Total en CLP: {total}, Total en USD: {valor_total}")

    return render(request, 'core/cart.html', data)
    
@login_required
def cartadd(request, id):
    # Obtener el producto de la API en lugar de la base de datos local
    response = requests.get(f"{API_URL}/productos/{id}")
    if response.status_code != 200:
        # Manejar el caso donde no se puede obtener el producto de la API
        # Puedes redirigir a una página de error o mostrar un mensaje al usuario
        return redirect('index')

    producto = response.json()

    # Crear o obtener el carrito de compras del usuario
    carro_compras, created = CarroCompras.objects.get_or_create(usuario=request.user)

    # Crear o actualizar el elemento del carrito para el producto
    carro_item, item_created = CarroItem.objects.get_or_create(producto_id_api=producto['id'], usuario=request.user)

    if not item_created:
        carro_item.cantidad += 1
        carro_item.save()

    # Agregar el elemento del carrito al carrito de compras
    carro_compras.items.add(carro_item)
    carro_compras.save()

    # No necesitas actualizar el stock del producto aquí, ya que eso se manejará en la API

    # Redirigir al usuario a la página del carrito
    return redirect('cart')


def cartdel(request, id):
    # Realizamos una solicitud a tu API para obtener la información del producto
    response = requests.get(f"{API_URL}/productos/{id}")
    
    if response.status_code == 200:
        producto_data = response.json()
        try:
            # Intentamos obtener el carrito de compras del usuario actual
            carro_compras = CarroCompras.objects.get(usuario=request.user)
            # Buscamos el item en el carrito basado en el ID del producto de la API
            carro_item = carro_compras.items.get(producto_id_api=id)
            
            # Verificamos si hay más de un producto en el carrito
            if carro_item.cantidad > 1:
                # Si hay más de un producto, simplemente disminuimos la cantidad
                carro_item.cantidad -= 1
                carro_item.save()
            else:
                # Si hay solo un producto, lo eliminamos del carrito
                carro_compras.items.remove(carro_item)
                carro_item.delete()

                # Incrementar el stock del producto cuando se elimina del carrito
                # (suponiendo que tengas un endpoint en tu API para realizar esta acción)
                # Esto es opcional y depende de cómo manejes tu API
                requests.post(f"{API_URL}/incrementar_stock/{id}")

        except CarroCompras.DoesNotExist:
            # Manejar el caso en que no se encuentre el carrito de compras del usuario actual
            # Esto puede suceder si el usuario no ha agregado ningún producto al carrito antes
            pass

        return redirect('cart')
    else:
        # Manejar el caso en que no se pueda obtener la información del producto desde la API
        # Por ejemplo, mostrar un mensaje de error al usuario
        return HttpResponse("Error al obtener la información del producto de la API", status=response.status_code)


def singleproduct(request, id):
    response = requests.get(f'http://127.0.0.1:5000/productos/{id}')  
    producto = response.json()  # Asumiendo que la respuesta es un objeto único de producto
    data = {
        'producto': producto
    }
    return render(request, 'core/single-product.html', data)


def grupo_requerido(nombre_grupo):
	def decorator(view_func):
		@user_passes_test(lambda user: user.groups.filter(name=nombre_grupo).exists())
		def wrapper(request, *args, **kwargs):
			return view_func(request, *args, **kwargs)
		return wrapper
	return decorator



# ViewSets para los modelos
class ProductoViewset(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class MarcaViewset(viewsets.ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer

class CarroItemViewset(viewsets.ModelViewSet):
    queryset = CarroItem.objects.all()
    serializer_class = CarroItemSerializer

class CarroComprasViewset(viewsets.ModelViewSet):
    queryset = CarroCompras.objects.all()
    serializer_class = CarroComprasSerializer

class CompraViewset(viewsets.ModelViewSet):
    queryset = Compra.objects.all()
    serializer_class = CompraSerializer

class CompraItemViewset(viewsets.ModelViewSet):
    queryset = CompraItem.objects.all()
    serializer_class = CompraItemSerializer

	
    
def indexapi(request):
    # Realizamos la solicitud a la API de productos
    respuesta = requests.get('http://127.0.0.1:8000/api/productos/')
    # Realizamos la solicitud a la API de mindicator
    respuesta2 = requests.get('https://mindicador.cl/api')
    # Realizamos la solicitud a la API de Rick and Morty (por ejemplo)
    respuesta3 = requests.get('https://rickandmortyapi.com/api/character')
    
    # Transformamos el JSON
    productos = respuesta.json()
    monedas = respuesta2.json()
    aux = respuesta3.json()
    personajes = aux['results']

    # Extraer los valores de UF y Dólar
    uf_value = monedas.get('uf', {}).get('valor', 'N/A')
    dolar_value = monedas.get('dolar', {}).get('valor', 'N/A')

    data = {
        'listaProductos': productos,
        'monedas': {
            'uf': uf_value,
            'dolar': dolar_value,
        },
        'personajes': personajes,
    }

    return render(request, 'core/indexapi.html', data)
	#API ANIMALES
def blogapi(request):
	#Solicitud al api
	respuesta4 = requests.get('https://dog.ceo/api/breeds/image/random')
	#TRANSFORMAMOS A JSON
	animales = respuesta4.json()

	data = {
		'animales' : animales,
	}
	return render(request, 'core/blogapi.html', data)

def index(request):
    try:
        # Obtener datos de la API
        respuesta2 = requests.get('https://mindicador.cl/api')
        response = requests.get('http://127.0.0.1:5000/productos')
        response.raise_for_status()  # Lanza una excepción si la solicitud no es exitosa
        productos_api = response.json()

        # Paginar los productos
        monedas = respuesta2.json()
        paginator = Paginator(productos_api, 8)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Determinar roles del usuario
        user = request.user
        roles = {
            'is_admin': user.groups.filter(name='administrador').exists(),
            'is_vendedor': user.groups.filter(name='vendedor').exists(),
            'is_bodeguero': user.groups.filter(name='bodeguero').exists(),
            'is_contador': user.groups.filter(name='contador').exists(),
        }
        dolar_value = monedas.get('dolar', {}).get('valor', 'N/A')

    except Exception as e:
        print(f"Error al obtener datos de la API: {e}")
        raise Http404

    data = {
        'page_obj': page_obj,
        'roles': roles,
        'monedas': {
            'dolar': dolar_value,
        },
    }
    return render(request, 'core/index.html', data)

def blog(request):
	return render(request, 'core/blog.html')


def transferencia_bancaria(request):
    if request.method == 'POST':
        # Obtener el archivo de comprobante de transferencia desde el formulario
        comprobante_transferencia = request.FILES.get('comprobante_transferencia')

        # Obtener el carrito de compras del usuario
        carro_compras = CarroCompras.objects.get(usuario=request.user)
        
        # Calcular el total de la compra
        total_compra = 0
        items = carro_compras.items.all()
        for item in items:
            producto_detalles = obtener_detalles_producto(item.producto_id_api)
            if producto_detalles:
                precio = float(producto_detalles.get('precio', 0))
                subtotal = precio * item.cantidad
                total_compra += subtotal

        # Crear un nuevo pedido con el comprobante de transferencia y el total calculado
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total_compra,
            comprobante_transferencia=comprobante_transferencia
        )

        # Limpiar el carrito después de crear el pedido
        carro_compras.delete()

        messages.success(request, "¡Comprobante de transferencia bancaria enviado correctamente!")
        return redirect('index')  # Redirige a donde desees después de subir el comprobante

    return render(request, 'core/transferencia_bancaria.html')

def ReportesVentas(request):
    # Obtener datos de ventas mensuales (ejemplo: ventas de este mes)
    today = datetime.today()
    start_date = today.replace(day=1)  # Primer día del mes actual
    end_date = today.replace(day=1, month=today.month % 12 + 1)  # Primer día del próximo mes

    # Filtrar pedidos por fecha dentro del rango del mes actual
    pedidos = Pedido.objects.filter(fecha_pedido__gte=start_date, fecha_pedido__lt=end_date)

    # Crear un libro de trabajo y una hoja
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Ventas"

    # Escribir encabezados
    ws.append(['ID', 'Usuario', 'Fecha', 'Total'])

    # Escribir datos de los pedidos
    for pedido in pedidos:
        # Convertir fecha_pedido a formato de cadena sin zona horaria
        fecha_formateada = pedido.fecha_pedido.strftime('%Y-%m-%d %H:%M:%S')

        # Escribir fila en Excel
        ws.append([pedido.id, pedido.usuario.username, fecha_formateada, pedido.total])

    # Generar nombre de archivo
    filename = f'reporte_ventas_{today.strftime("%Y-%m")}.xlsx'

    # Guardar el libro de trabajo en un HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)

    return response

#def cart(request):
    
   #carro_compras = CarroCompras.objects.get(usuario=request.user)
   #tems = carro_compras.items.all()
   #otal = carro_compras.total()

   #ata = {
   #   'items': items,
   #   'total': total,
   #

   #eturn render(request,'core/cart.html',data)
  


def cartUser(request):
	return render(request, 'core/cartUser.html')

def category(request):
	productosAll = Producto.objects.all()
	data = {
		'listaProductos' : productosAll
	}
	return render(request, 'core/category.html', data)	
				
						
def confirmation(request):
    # Obtener todos los pedidos que tienen un comprobante de transferencia bancaria adjunto
    pedidos = Pedido.objects.exclude(comprobante_transferencia='').order_by('-fecha_pedido')

    if request.method == 'POST':
        # Procesar el formulario para cambiar el estado del pedido
        pedido_id = request.POST.get('pedido_id')
        estado_pedido = request.POST.get('estado_pedido')

        try:
            pedido = Pedido.objects.get(id=pedido_id)
            pedido.estado = estado_pedido
            pedido.save()
            messages.success(request, f"Estado del pedido #{pedido_id} actualizado correctamente a {estado_pedido}.")
        except Pedido.DoesNotExist:
            messages.error(request, f"El pedido con ID {pedido_id} no existe.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error al actualizar el estado del pedido: {str(e)}")

        return redirect('confirmation')  # Redirige nuevamente a la página de confirmación después de procesar el formulario

    context = {
        'pedidos': pedidos,
    }

    return render(request, 'core/confirmation.html', context)

def contact(request):
	return render(request, 'core/contact.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        user = User.objects.filter(email=email).first()
        if user:
            reset_url = request.build_absolute_uri(reverse('password_reset', args=[user.pk]))
            send_mail(
                'Cambio de Contraseña',
                f'Por favor, usa este enlace para cambiar tu contraseña: {reset_url}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, 'Se ha enviado un enlace de restablecimiento de contraseña a tu correo.')
            return redirect('login')  # Redirige a la página de login o a otra página
        else:
            messages.error(request, 'No se encontró una cuenta con ese correo electrónico.')
    return render(request, 'core/forgot_password.html')


def send_reset_password_email(user):
    token = 'GENERAR_UN_TOKEN_UNICO_AQUI'
    reset_url = reverse('reset_password', args=[token])
    send_mail(
        'Cambio de Contraseña',
        f'Usa este enlace para cambiar tu contraseña: {reset_url}',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def email_sent(request):
    return render(request, 'core/email_sent.html')

def password_reset(request, token):
    # Asumiendo que el token también incluye información para identificar al usuario
    user_id, token = token.split(":", 1)
    user = User.objects.get(pk=user_id)
    
    if verify_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Tu contraseña ha sido actualizada.')
            return redirect('login')
        # Si no tienes el archivo 'change_password.html', redirige a 'forgot_password.html' o a cualquier otro que tengas
        return render(request, 'core/forgot_password.html')
    else:
        messages.error(request, 'El enlace para restablecer la contraseña no es válido o ha expirado.')
        return redirect('core/forgot_password')	

def indexUser(request):
	return render(request, 'core/indexUser.html')				
						
def indexUserSubscito(request):
	return render(request, 'core/indexUserSubscito.html')	

def login(request):
	return render(request, 'core/login.html')
		
def perfil(request):
	return render(request, 'core/perfil.html')	

def register(request):
	return render(request, 'core/register.html')

def singleblog(request):
	return render(request, 'core/single-blog.html')

    

def subsForm(request):
	return render(request, 'core/subsForm.html')

def trackingorder(request):
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        pedido = get_object_or_404(Pedido, id=pedido_id)
        return render(request, 'tracking-order.html', {'pedido': pedido})
    return render(request, 'core/tracking-order.html')


#crud

    




def registro(request):
    data = {
        'form': CustomUserCreationForm()
    }
    if request.method == 'POST':
        formulario = CustomUserCreationForm(data=request.POST)
        if formulario.is_valid():
            user = formulario.save()
            messages.success(request, "Te has registrado correctamente")
            return redirect(to="index")  # Redirige al usuario al index después de registrarse
        data["form"] = formulario

    return render(request, 'registration/registro.html', data)




    

@login_required
def order_history(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_pedido')
    return render(request, 'core/order_history.html', {'pedidos': pedidos})




import requests
from django.http import HttpResponse
from .models import CarroCompras






def cartdelete(request, id):
    # Buscar el carro_compras del usuario actual
    carro_compras = CarroCompras.objects.get(usuario=request.user)
    
    # Buscar el carro_item asociado al producto con el identificador recibido
    # del carrito del usuario
    try:
        carro_item = carro_compras.items.get(producto_id_api=id)
    except CarroItem.DoesNotExist:
        # Si el carro_item no existe, simplemente redirige al carrito
        return redirect('cart')

    # Eliminar el carro_item del carrito y guardar los cambios
    carro_compras.items.remove(carro_item)
    carro_item.delete()

    return redirect('cart')

def add_compra(request): 
    carro_compras = CarroCompras.objects.get(usuario = request.user)
    items = carro_compras.items.all()

    compra = Compra.objects.create(usuario = request.user)
    for item in items:
        CompraItem.objects.create(compra = compra, carro_item = item)

    carro_compras.items.clear()
    return redirect(to='confirmation')





def agregar_suscriptor(request, id):
    usuario = User.objects.get(id=id)
    usuario.groups.add(5)
    usuario.save()
    return redirect('index')

@permission_required('core.view_producto')
def subsForm(request):
    if request.method == 'POST':
        form = DonacionForm(request.POST)
        if form.is_valid():
            # Procesa la donación (por ejemplo, guarda la cantidad en la base de datos)
            cantidad = form.cleaned_data['cantidad']
            # Realiza cualquier otro procesamiento necesario

            # Redirige a la página de confirmación de donación exitosa o a la página de PayPal
            return render(request, 'core/confirmation.html')
    else:
        form = DonacionForm()

    return render(request, 'core/subsForm.html', {'form': form})
@login_required
@permission_required('auth.change_user')
def asignar_roles(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        nuevo_rol = request.POST.get('nuevo_rol')
        accion = request.POST.get('accion')

        try:
            usuario = User.objects.get(pk=usuario_id)
            usuario_nombre = usuario.username

            if accion == 'agregar' and nuevo_rol:
                grupo = Group.objects.get(name=nuevo_rol)
                usuario.groups.add(grupo)
                messages.success(request, f"Se asignó el rol '{nuevo_rol}' al usuario '{usuario_nombre}' correctamente.")
            elif accion == 'quitar' and nuevo_rol:
                grupo = Group.objects.get(name=nuevo_rol)
                usuario.groups.remove(grupo)
                messages.success(request, f"Se quitó el rol '{nuevo_rol}' al usuario '{usuario_nombre}' correctamente.")
           
        except User.DoesNotExist:
            messages.error(request, f"El usuario con ID '{usuario_id}' no existe.")
        except Group.DoesNotExist:
            messages.error(request, f"El grupo '{nuevo_rol}' no existe.")

        return redirect(f'{request.path}?usuario_id={usuario_id}')

    usuarios = User.objects.all()
    grupos = Group.objects.all()
    
    roles_usuario = None
    usuario_id = request.GET.get('usuario_id')
    if usuario_id:
        try:
            usuario_seleccionado = User.objects.get(pk=usuario_id)
            roles_usuario = usuario_seleccionado.groups.values_list('name', flat=True)
        except User.DoesNotExist:
            pass

    return render(request, 'core/asignar_roles.html', {'usuarios': usuarios, 'grupos': grupos, 'roles_usuario': roles_usuario})


@login_required
@user_passes_test(lambda u: u.groups.filter(name='vendedor').exists())
def productos_bodega(request):
    productos = Producto.objects.filter(stock__gt=0)
    return render(request, 'core/productos_bodega.html', {'productos': productos})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='vendedor').exists())
def gestionar_pedidos(request):
    # Obtener todos los pedidos ordenados por fecha de pedido descendente
    pedidos = Pedido.objects.all().order_by('-fecha_pedido')
    
    # Si solo quieres los pedidos relacionados con el usuario logueado como vendedor,
    # puedes ajustar el filtro según la lógica de tu aplicación. Por ejemplo:
    # pedidos = Pedido.objects.filter(vendedor=request.user).order_by('-fecha_pedido')
    
    return render(request, 'core/gestionar_pedidos.html', {'pedidos': pedidos})


@login_required
@user_passes_test(lambda u: u.groups.filter(name='vendedor').exists())
def ordenar_pedidos(request):
    pedidos = Pedido.objects.all()
    return render(request, 'core/ordenar_pedidos.html', {'pedidos': pedidos})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='bodeguero').exists())
def ordenes_pedidos(request):
    pedidos = Pedido.objects.all()
    return render(request, 'core/ordenes_pedidos.html', {'pedidos': pedidos})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='bodeguero').exists())
def preparar_pedidos(request):
    pedidos = Pedido.objects.filter(estado='pendiente')
    return render(request, 'core/preparar_pedidos.html', {'pedidos': pedidos})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='contador').exists())
def confirmar_pagos(request):
    pagos = Pago.objects.filter(estado='pendiente')
    return render(request, 'core/confirmar_pagos.html', {'pagos': pagos})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='contador').exists())
def registrar_entregas(request):
    entregas = Entrega.objects.all()
    return render(request, 'core/registrar_entregas.html', {'entregas': entregas})

# Agregar un manejo de excepciones para mostrar un mensaje de error y redirigir al index
def permission_denied_view(request):
    messages.error(request, "No tienes permiso para acceder a esta página.")
    return redirect('index')

def productos_bodega(request):
    try:
        # Obtener datos de la API
        response = requests.get('http://127.0.0.1:5000/productos')
        response.raise_for_status()  # Lanza una excepción si la solicitud no es exitosa
        productos_api = response.json()

        # Paginar los productos
        paginator = Paginator(productos_api, 8)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Renderizar la plantilla con los datos paginados
        return render(request, 'core/productos_bodega.html', {'page_obj': page_obj})

    except RequestException as e:
        # Manejar cualquier error de solicitud de la API
        error_message = f"Error al obtener datos de la API: {str(e)}"
        return render(request, 'core/productos_bodega.html', {'error_message': error_message})
    
        def gestionar_pedidos(request):
            pedidos = Pedido.objects.all()
            return render(request, 'core/gestionar_pedidos.html', {'pedidos': pedidos})
            
def aceptar_pedido(request, pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)
    pedido.estado = 'completado'
    pedido.save()
    return redirect('gestionar_pedidos')

def rechazar_pedido(request, pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)
    pedido.estado = 'cancelado'
    pedido.save()
    return redirect('gestionar_pedidos')

@login_required
@user_passes_test(lambda u: u.groups.filter(name='vendedor').exists())
def actualizar_pedido(request, pedido_id):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, id=pedido_id)
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Pedido.ESTADO_CHOICES):
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, "¡Estado del pedido actualizado correctamente!")
        else:
            messages.error(request, "Estado no válido.")
    return redirect('gestionar_pedidos')

def ordenar_pedidos(request):
    if request.method == 'POST':
        bodeguero_id = request.POST.get('bodeguero')
        descripcion = request.POST.get('descripcion')  # Obtener la descripción de la orden del formulario

        try:
            bodeguero = User.objects.get(pk=bodeguero_id)  # Obtiene el objeto del bodeguero
            # Procesa la orden y guárdala en la base de datos con la descripción proporcionada
            orden = Orden(bodeguero=bodeguero, descripcion=descripcion)
            orden.save()
            # Agrega un mensaje para confirmar que se ha ordenado correctamente
            messages.success(request, 'Se ha ordenado el pedido correctamente.')
        except User.DoesNotExist:
            # Maneja el caso donde no se encuentra al usuario
            messages.error(request, 'El bodeguero seleccionado no existe.')
        
        # Redirige a la misma página para evitar reenvíos de formulario
        return redirect('ordenar_pedidos')
    else:
        # Si la solicitud no es POST, simplemente renderiza la página con la lista de bodegueros
        usuarios_bodegueros = User.objects.filter(groups__name='bodeguero')  # Filtra los usuarios por grupo 'bodeguero'
        historial_ordenes = Orden.objects.all()  # Puedes filtrar el historial según tus necesidades
        return render(request, 'core/ordenar_pedidos.html', {'usuarios_bodegueros': usuarios_bodegueros, 'historial_ordenes': historial_ordenes})
@login_required
@user_passes_test(lambda u: u.groups.filter(name='bodeguero').exists())
def ordenes_pedidos(request):
    if request.method == 'POST':
        vendedor_id = request.POST.get('vendedor')
        mensaje = request.POST.get('mensaje')
        try:
            vendedor = User.objects.get(pk=vendedor_id)
            orden = OrdenB(vendedor=vendedor, descripcion=mensaje)
            orden.save()
            messages.success(request, 'Se ha enviado la orden al vendedor correctamente.')
        except User.DoesNotExist:
            messages.error(request, 'El vendedor seleccionado no existe.')
        return redirect('ordenes_pedidos')
    else:
        vendedores = User.objects.filter(groups__name='vendedor')
        historial_ordenes = OrdenB.objects.all()
        return render(request, 'core/ordenes_pedidos.html', {'vendedores': vendedores, 'historial_ordenes': historial_ordenes})
        
