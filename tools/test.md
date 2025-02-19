# Python装饰器：从基础语法到高级应用

作为一个Python开发者，我发现很多人对装饰器的概念感到困惑。今天，我想和大家分享Python装饰器的知识，从最基础的语法开始，逐步深入到更复杂的用法。

## 1. 装饰器的基本概念

装饰器本质上是一个函数，它接受一个函数作为参数，并返回一个新的函数。我们用`@`符号来使用装饰器。

### 1.1 最简单的装饰器

让我们从最简单的装饰器开始：

```python
def simple_decorator(func):
    def wrapper():
        print("Something is happening before the function is called.")
        func()
        print("Something is happening after the function is called.")
    return wrapper

@simple_decorator
def say_hello():
    print("Hello!")

say_hello()
```

输出：
```
Something is happening before the function is called.
Hello!
Something is happening after the function is called.
```

这个例子展示了装饰器的基本工作原理。`@simple_decorator`语法等同于`say_hello = simple_decorator(say_hello)`。

## 2. 带参数的函数装饰器

### 2.1 装饰带参数的函数

如果被装饰的函数有参数，我们需要在wrapper函数中处理这些参数：

```python
def logging_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Calling function {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Function {func.__name__} returned {result}")
        return result
    return wrapper

@logging_decorator
def sum_two_numbers(a, b):
    return a + b

print(sum_two_numbers(3, 5))
```

输出：
```
Calling function sum_two_numbers
Function sum_two_numbers returned 8
8
```

这里，`*args`和`**kwargs`允许wrapper函数接受任意数量的位置参数和关键字参数。

### 2.2 装饰器本身带参数

有时我们需要装饰器本身能够接受参数。这就需要再添加一层封装：

```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")
```

输出：
```
Hello, Alice!
Hello, Alice!
Hello, Alice!
```

这个例子中，`@repeat(3)`实际上是在调用`repeat`函数，该函数返回真正的装饰器。

## 3. 保留被装饰函数的元信息

当我们使用装饰器时，被装饰函数的一些元信息（如函数名、文档字符串等）可能会丢失。使用`functools.wraps`可以解决这个问题：

```python
from functools import wraps

def preserving_metadata(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        """This is the wrapper function"""
        return func(*args, **kwargs)
    return wrapper

@preserving_metadata
def greet(name):
    """This function greets a person"""
    print(f"Hello, {name}!")

print(greet.__name__)  # 输出: greet
print(greet.__doc__)   # 输出: This function greets a person
```

## 4. 类装饰器

装饰器不仅可以是函数，还可以是类。类装饰器主要依靠类的`__call__`方法来实现装饰器功能：

```python
class CountCalls:
    def __init__(self, func):
        self.func = func
        self.count = 0
    
    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"{self.func.__name__} has been called {self.count} times")
        return self.func(*args, **kwargs)

@CountCalls
def say_hello():
    print("Hello!")

say_hello()
say_hello()
```

输出：
```
say_hello has been called 1 times
Hello!
say_hello has been called 2 times
Hello!
```

## 5. 多个装饰器的应用顺序

当多个装饰器应用到同一个函数时，执行顺序是从下到上的：

```python
def bold(func):
    def wrapper():
        return "<b>" + func() + "</b>"
    return wrapper

def italic(func):
    def wrapper():
        return "<i>" + func() + "</i>"
    return wrapper

@bold
@italic
def greet():
    return "Hello, world!"

print(greet())  # 输出: <b><i>Hello, world!</i></b>
```

这里，`italic`装饰器先被应用，然后是`bold`装饰器。

## 6. 实际应用示例

### 6.1 Flask中的路由装饰器

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Welcome to my website!'

@app.route('/user/<username>')
def user_profile(username):
    return f'User: {username}'
```

### 6.2 自定义认证装饰器

```python
from functools import wraps
from flask import abort, g

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin")
@admin_required
def admin_page():
    return "Welcome, admin!"
```

## 小结

装饰器是Python中非常强大的特性，它允许我们以非侵入式的方式修改或增强函数的行为。从简单的函数装饰器到复杂的参数化类装饰器，我们可以用它们实现各种功能，如日志记录、访问控制、性能测量等。

在实际开发中，特别是在使用Web框架如Flask或Django时，你会经常遇到并使用装饰器。理解和掌握装饰器不仅能让你的代码更加简洁、模块化，还能帮助你更好地理解和使用各种Python框架。

希望这篇文章能帮助你更深入地理解Python装饰器。如果你有任何问题或想法，欢迎在评论区讨论。