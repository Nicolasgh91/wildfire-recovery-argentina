from workers.tasks.recovery import batch_episode_recovery_analysis

# Execute batch episode recovery for recent episodes
result = batch_episode_recovery_analysis.delay(max_episodes=20, recent_only=True)
print(f'Batch Episode Task ID: {result.id}')
print(f'Status: {result.status}')
print(f'This will process up to 20 recent episodes')
