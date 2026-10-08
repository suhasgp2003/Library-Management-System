from django.core.exceptions import ValidationError

def validate_isbn(value):
    isbn = value.replace('-', '').replace(' ', '').upper()
    valid = False
    if len(isbn) == 13 and isbn.isdigit():
        valid = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(isbn)) % 10 == 0
    elif len(isbn) == 10 and isbn[:9].isdigit() and (isbn[-1].isdigit() or isbn[-1] == 'X'):
        valid = sum((10 - index) * (10 if char == 'X' else int(char)) for index, char in enumerate(isbn)) % 11 == 0
    if not valid:
        raise ValidationError('Enter a valid ISBN-10 or ISBN-13, including its check digit.')
