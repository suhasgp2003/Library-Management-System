from django.urls import path
from . import views

urlpatterns=[
    path("",views.home,name="home"),
    path("about/",views.about,name="about"),
    path("contact/",views.contact,name="contact"),
    path("students/",views.students,name="students"),
    path("books/",views.books,name="books"),
    path("issue/<int:book_id>/",views.issue_book,name="issue_book"),
    path("return/<int:book_id>/",views.return_book,name="return_book"),
    path("book-history/<int:book_id>/",views.book_history,name="book_history"),
]