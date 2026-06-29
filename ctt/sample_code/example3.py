def compute(arr):
    total = 0

    for i in range(len(arr)):
        total += arr[i] * arr[i]  
        total += len(arr)          

    return total


def main():
  
    arr = list(range(200000))  

    result = compute(arr)
    print("Result:", result)


if __name__ == "__main__":
    main()