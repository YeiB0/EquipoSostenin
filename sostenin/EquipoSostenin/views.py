from django.shortcuts import render
from django.http import HttpResponse
from .forms import UploadPDFForm
#aca importar librerias para procesar el pdf y crear el excel

def handle_uploaded_pdf(file):
  #aca se pone la logica para procesar el pdf
  print(f"Archivo recibido: {file.name}")
  print(f"Tamaño: {file.size} bytes")
  #aqui se retornaria la respuesta con el excel
  pass

def upload_pdf(request):
    if request.method == 'POST':
        form =  UploadPDFForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['pdf_file']
            handle_uploaded_pdf(pdf_file)#esto llama a la logica para procesar el archivo
            return HttpResponse("PDF recibido y procesado") 
      #por ahora returna un mensaje, posterior se cambia para que retorne el excel
    else:
        form = UploadPDFForm()
    return render(request, 'EquipoSostenin/upload.html', {'form': form})
                        


# Create your views here.
