from workers.tasks.recovery import batch_recovery_analysis

# Process recent events (last 12 months) with conservative batch size
result = batch_recovery_analysis.delay(max_events=15)
print(f'Batch Task ID: {result.id}')
print(f'Status: {result.status}')
print(f'This will process up to 15 recent events')
