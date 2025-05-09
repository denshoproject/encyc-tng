from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('contents/', views.articles, name='encyc-articles'),
    path('categories/', views.topics, name='encyc-topics'),  # TODO fix link in nav
    path('topics/', views.topics, name='encyc-topics'),
    path('authors/', views.authors, name='encyc-authors'),
    path('authors/<int:author_id>/', views.author, name='encyc-author'),
    path('sources/<str:source_type>/<int:source_id>/', views.source, name='encyc-source'),
    path('index/', views.index, name='encyc-index'),
]
