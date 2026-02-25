from workers.tasks.recovery import analyze_recovery

result = analyze_recovery.delay('eee06dee-f626-4c4e-a1da-12bb3a4d3480')
print(f'Task ID: {result.id}')
print(f'Status: {result.status}')
