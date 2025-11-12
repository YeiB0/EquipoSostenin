from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegisterForm
# Create your views here.
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Inicio de sesión exitoso')
            return redirect('home')
    else:
         form = AuthenticationForm()
           
    return render(request, 'account/login.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada correctamente. ¡Ya puedes iniciar sesión!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'account/register.html', {'form': form})

def user_logout(request):
    # Usamos la función de logout de Django
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    
    # Redirigimos al 'home'. Como 'home' está protegido,
    # Django automáticamente redirigirá a la página 'login'.
    return redirect('home')