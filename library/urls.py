from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
    path('accounts/password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('books/', views.books, name='books'),
    path('books/add/', views.book_edit, name='book_add'),
    path('books/<int:book_id>/edit/', views.book_edit, name='book_edit'),
    path('books/<int:book_id>/archive/', views.book_archive, name='book_archive'),
    path('books/<int:book_id>/restore/', views.book_restore, name='book_restore'),
    path('students/', views.students, name='students'),
    path('students/add/', views.student_edit, name='student_add'),
    path('students/<int:student_id>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:student_id>/archive/', views.student_archive, name='student_archive'),
    path('students/<int:student_id>/restore/', views.student_restore, name='student_restore'),
    path('issue/<int:book_id>/', views.issue_book, name='issue_book'),
    path('return/<int:book_id>/', views.return_book, name='return_book'),
    path('book-history/<int:book_id>/', views.book_history, name='book_history'),
    path('loans/', views.loans, name='loans'),
    path('loans/<int:loan_id>/return/', views.loan_return, name='loan_return'),
    path('reservations/', views.reservations, name='reservations'),
    path('books/<int:book_id>/reserve/', views.reserve_book, name='reserve_book'),
    path('reservations/<int:reservation_id>/cancel/', views.reservation_cancel, name='reservation_cancel'),
]
