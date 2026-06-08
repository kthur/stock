import random

fails = 0
for _ in range(10000):
    w_dict = {f"k{i}": random.random() for i in range(100)}
    s = sum(w_dict.values())
    w_dict = {k: v/s for k, v in w_dict.items()}
    
    # find max
    largest_k = max(w_dict, key=w_dict.get)
    # move to end
    w_dict[largest_k] = w_dict.pop(largest_k)
    
    # adjust the last element
    # We can do this safely:
    w_dict[largest_k] = 1.0 - sum(list(w_dict.values())[:-1])
    
    fails += (sum(w_dict.values()) != 1.0)
    
print("Fails with re-insertion:", fails)
