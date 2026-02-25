from workers.tasks.recovery import analyze_recovery

# Test the optimized VAE service with ImageCollection.median()
# Use a recent event to validate the optimization works
test_event_id = "2eafa3c6-2e8a-4c4e-a1da-12bb3a4d3480"  # Recent event from our batch

result = analyze_recovery.delay(test_event_id)
print(f'Test Task ID: {result.id}')
print(f'Status: {result.status}')
print(f'Testing ImageCollection.median() optimization...')
