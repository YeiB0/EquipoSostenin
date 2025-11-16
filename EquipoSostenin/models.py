from django.db import models
from django.contrib.auth.models import User

class Boleta(models.Model):
    SERVICIO_CHOICES = [
        ('Luz', 'Luz'),
        ('Agua', 'Agua'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Procesar'),
        ('PROCESADO', 'Procesado Exitosamente'),
        ('ERROR', 'Error al Procesar'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    servicio = models.CharField(
        max_length=10, 
        choices=SERVICIO_CHOICES,
        help_text="Selecciona el tipo de servicio de la boleta"
    )
    
    archivo_boleta = models.FileField(
        upload_to='boletas/', 
        blank=False, # Significa que no puede estar vacío en el formulario
        null=False, # Significa que no puede ser NULO en la BD
        help_text="Sube el archivo PDF de tu boleta"
    )
 
    monto = models.IntegerField(
        null=True, blank=True,
        help_text="(Se extraerá automáticamente del PDF)"
    ) 

    consumo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, blank=True,
        help_text="(Consumo KWh o m³. Se extraerá automáticamente)"
    )

    fecha_emision = models.DateField(
        null=True, blank=True,
        help_text="(Fecha de emisión. Se extraerá automáticamente)"
    )

    estado_procesamiento = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        help_text="Estado del procesamiento automático del PDF"
    )
    
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha en que se subió el registro"
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.get_servicio_display()} - {self.estado_procesamiento}"