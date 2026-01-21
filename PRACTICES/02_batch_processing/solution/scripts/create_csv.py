import random

sentiments = [
    'Amazing product, love it!',
    'Terrible service, never again.',
    'Just okay, average quality.',
    'Super fast shipping!',
    'Not worth the money.'
]
with open('large_data.csv', 'w') as f:
    f.write('id,text\n')
    for i in range(10000):
        f.write(f'{i},{random.choice(sentiments)}\n')
print('Created large_data.csv with 10,000 rows')
