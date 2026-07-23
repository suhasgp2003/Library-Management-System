from django.shortcuts import render,redirect,get_object_or_404
from django.db.models import Q
from .models import Book,Student,IssueBook
from datetime import datetime
from django.utils import timezone

# Create your views here.
def home(request):
     
    return render(request,'home.html',{'current_time': datetime.now()})


def about(request):
    return render(request,'about.html')

def contact(request):
    return render(request,'contact.html')

def books(request):
    query=request.GET.get('q')
    if query:
        books=Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(category__icontains=query))
    else:
        books=Book.objects.all()
    return render(request,'books.html',{'books':books})

def issue_book(request,book_id):
    book=Book.objects.get(id=book_id)
    if book.available_copies > 0:
        book.available_copies -=1
        book.save()
        IssueBook.objects.create(
            student=Student.objects.first(),
            book=book,
            issue_date=timezone.now().date(),
            return_date=timezone.now().date(),returned_status=False
        )

    return redirect('books')    

        
def return_book(request,book_id):
    book=Book.objects.get(id=book_id)
    book.available_copies +=1
    book.save()
    issue=IssueBook.objects.filter(
        book=book,
        returned_status=False
    ).last()
    if issue:
        issue.returned_status=True
        issue.return_date=timezone.now().date()
        issue.save()
    return redirect('books')

def students(request):
    students=Student.objects.all().order_by('student_name')
    return render(request,'students.html',{'students':students})



def book_history(request,book_id):
    book=get_object_or_404(Book,id=book_id)
    history=IssueBook.objects.filter(book=book).order_by("-id")
    return render(request,"book-history.html",{"book":book,"history":history})