import sys, binascii
target = sys.argv[1]
hex_data = sys.argv[2]
with open(target, 'a', encoding='utf-8') as f:
    f.write(binascii.unhexlify(hex_data).decode('utf-8'))
print('Hex chunk appended successfully')
