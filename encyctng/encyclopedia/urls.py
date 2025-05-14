from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('categories/', views.articles_topic), # TODO edit nav and remove
    path('contents/',   views.articles_az),    # TODO edit nav and remove
    path('articles-topic/', views.articles_topic, name='encyc-articles-topic'),
    path('articles-az/', views.articles_az, name='encyc-articles-az'),
    path('authors/', views.authors, name='encyc-authors'),
    path('authors/<int:author_id>/', views.author, name='encyc-author'),
    path('sources/<str:source_type>/<int:source_id>/', views.source, name='encyc-source'),
    path('index/', views.index, name='encyc-index'),
]
