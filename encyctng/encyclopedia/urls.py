from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('articles/', views.articles, name='encyc-articles'),
    path('authors/', views.authors, name='encyc-authors'),
    path('authors/<int:author_id>/', views.author, name='encyc-author'),
    path('sources/<str:source_type>/<int:source_id>/', views.source, name='encyc-source'),
]
