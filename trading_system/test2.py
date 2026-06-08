import random
fails = 0
for _ in range(10000):
    w = [random.random() for _ in range(100)]
    s = sum(w)
    w = [x/s for x in w]
    others = w[:50] + w[51:]
    w[50] = 1.0 - sum(others)
    fails += (sum(w) != 1.0)
print('Fails:', fails)
