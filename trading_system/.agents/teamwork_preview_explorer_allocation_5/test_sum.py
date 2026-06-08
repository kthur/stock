import random
fails = 0
n = 1000000
for _ in range(n):
    weights = [random.random() for _ in range(10)]
    tot = sum(weights)
    norm = [w/tot for w in weights[:-1]]
    norm.append(1.0 - sum(norm))
    if sum(norm) != 1.0:
        fails += 1
print(f'Fails: {fails}/{n}')
