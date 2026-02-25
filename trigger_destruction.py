from workers.tasks.destruction import detect_destruction

result = detect_destruction.delay('eee06dee-f626-4c4e-a1da-12bb3a4d3480')
print(f'Task ID: {result.id}')
print(f'Status: {result.status}')
