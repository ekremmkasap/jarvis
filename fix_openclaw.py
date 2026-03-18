with open(r'C:\Users\sergen\AppData\Roaming\Python\Python311\site-packages\cmdop\exceptions.py', 'a') as f:
    f.write('\ndef TimeoutError(*args):\n    pass\n')
    f.write('class TimeoutError(Exception):\n    pass\n')
print('Fixed!')
