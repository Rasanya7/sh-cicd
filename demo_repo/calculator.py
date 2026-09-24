"""Calculator module used for demo CI/CD pipelines and self-healing tests."""

def add(a, b):
    """Return the sum of a and b."""
    return a + b


def subtract(a, b):
    """Return the difference between a and b."""
    return a - b


def multiply(a, b):
    """Return the product of a and b."""
    return a * b


def divide(a, b):
    """Return the division of a by b with safe zero handling."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b


def power(base, exp):
    """Return base raised to exp."""
    return base ** exp


def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
