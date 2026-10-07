from django.shortcuts import render


def index(request):
    return render(request, "frontend/app.html")


def login_page(request):
    return render(request, "frontend/login.html")
