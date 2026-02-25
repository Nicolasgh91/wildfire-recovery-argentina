from workers.tasks.recovery import batch_episode_recovery_analysis

# Execute complete historical backfill for all episodes (2015-2025)
# This will process all 2,133 episodes using the optimized median approach

result = batch_episode_recovery_analysis.delay(
    max_episodes=500, 
    recent_only=False
)

print(f'Historical Backfill Task ID: {result.id}')
print(f'Status: {result.status}')
print(f'This will process up to 500 episodes from 2015-2025')
print(f'Expected GEE requests: ~2,500 (5 requests per episode)')
print(f'Expected processing time: ~1 hour for 500 episodes')
print(f'Total episodes to process: ~2,133')
