# Generated by Django 3.1.2 on 2024-07-14 03:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_auto_20240713_2101'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobado', 'aprobado'), ('En proceso', 'En proceso'), ('completado', 'Completado'), ('cancelado', 'Cancelado'), ('Enviado', 'Enviado'), ('Entregado', 'Entregado')], default='pendiente', max_length=20),
        ),
    ]
