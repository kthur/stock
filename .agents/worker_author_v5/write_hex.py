import sys, binascii
target, hex_data = sys.argv[1], sys.argv[2]
with open(target, 'w', encoding='utf-8') as f:
    f.write(binascii.unhexlify(hex_data).decode('utf-8'))
print('Hex file written successfully')
