width = 2 * 3
height = 10 + 5
seconds_in_day = 60 * 60 * 24

def compute_square(x):
    return x ** 2

def compute_cube(x):
    return x ** 3
    
result = 0
result = 42

a = result * 1
b = result + 0
c = result - 0
d = result ** 1
e = result // 1

flag = True
if flag == True:
    print("Flag is on")
if flag == False:
    print("Flag is off")
if flag != True:
    print("Flag is not on")

def greet(name):
    return f"Hello, {name}"
    print("This will never run")
    x = 100

color = "red"
if color in ["red", "green", "blue"]:
    print("Primary color")
if 5 not in [1, 2, 3, 4]:
    print("Not found")

squares = []
for i in range(10):
    squares.append(i ** 2)

doubled = []
for x in range(5):
    doubled.append(x * 2)

def energy_formula(mass):
    c = 3 * 100000000
    return mass * c ** 2

print("Width:", width)
print("Height:", height)
print("Seconds in a day:", seconds_in_day)
print("Square of 5:", compute_square(5))
print("Cube of 3:", compute_cube(3))
print("Result:", result)
print("a:", a, "b:", b, "c:", c, "d:", d, "e:", e)
print("Greet:", greet("World"))
print("Squares:", squares)
print("Doubled:", doubled)
print("Energy:", energy_formula(1))
