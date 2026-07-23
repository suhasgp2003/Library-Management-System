from django.db import models

# Create your models here.
class Book(models.Model):
    title=models.CharField(max_length=100)
    author=models.CharField(max_length=50)
    isbn_number=models.CharField(max_length=25)
    category=models.CharField(max_length=50)
    publisher=models.CharField(max_length=100)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    quantity=models.IntegerField()
    published_date=models.DateField()
    available_copies=models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class Student(models.Model):
    student_name=models.CharField(max_length=100)
    usn=models.CharField(max_length=20,unique=True)
    email=models.EmailField()
    phone_number=models.CharField(max_length=10)
    department=models.CharField(max_length=100)
    semester=models.SmallIntegerField()

    def __str__(self):
        return self.student_name

class IssueBook(models.Model):
    student=models.ForeignKey(Student,on_delete=models.CASCADE)
    book=models.ForeignKey(Book,on_delete=models.CASCADE)
    issue_date=models.DateField()
    return_date=models.DateField(null=True,blank=True)
    returned_status=models.BooleanField() 

    def __str__(self):
        return f"{self.student.student_name} - {self.book.title}"   
    


