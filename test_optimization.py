from workers.tasks.recovery import analyze_recovery

# Test the optimized VAE service with ImageCollection.median()
# Use the original test event that we know exists
test_event_id = "eee06dee-f626-4c4e-a1da-12bb3a4d3480"  # Original test event

result = analyze_recovery.delay(test_event_id)
print(f'Test Task ID: {result.id}')
print(f'Status: {result.status}')
print(f'Testing ImageCollection.median() optimization...')
