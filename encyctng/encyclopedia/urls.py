from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('contents/', views.contents, name='encyc-contents'),
]
