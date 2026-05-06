from django.urls import path, re_path

from . import views

urlpatterns = [
    path('about/', views.about, name='encyc-about'),
    path('history/', views.history, name='encyc-history'),
    path('terminology/', views.terminology, name='encyc-terminology'),
    path('timeline/', views.timeline, name='encyc-timeline'),
]
