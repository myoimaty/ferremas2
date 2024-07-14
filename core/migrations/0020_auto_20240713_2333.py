# Generated by Django 3.1.2 on 2024-07-14 03:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auto_20240713_2323'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobado', 'Aprobado'), ('en_proceso', 'En proceso'), ('completado', 'Completado'), ('cancelado', 'Cancelado'), ('enviado', 'Enviado'), ('entregado', 'Entregado')], default='pendiente', max_length=20),
        ),
    ]
