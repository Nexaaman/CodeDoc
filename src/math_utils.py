# File: D:\Personal\CodeDoc\src\math_utils.py

def factorial(n) -> int:
    """Calculate the factorial of a non-negative integer n.
    
    Args:
        n (int): A non-negative integer for which to calculate the factorial.
    
    Returns:
        int: The factorial of n.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def fibonacci(n) -> int:
    """Calculate the nth Fibonacci number.
    
    Args:
        n (int): The index of the Fibonacci number to calculate.
    
    Returns:
        int: The nth Fibonacci number.
    """
    if n < 0:
        raise ValueError("Fibonacci sequence is not defined for negative numbers")
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def final_answer(result: any) -> any:
    """Provides a final answer to the given problem.
    
    Args:
        result: The final answer to the problem.
    """
    print(f"The final answer is {result}")