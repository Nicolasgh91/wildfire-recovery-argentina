from workers.tasks.recovery import batch_episode_recovery_analysis

print("🚀 === TRIGGERING HISTORICAL BACKFILL ===")
print("🚀 This will process up to 500 episodes from 2015-2025")
print("🚀 Expected GEE requests: ~2,500 (5 requests per episode)")
print("🚀 Expected processing time: ~1 hour for 500 episodes")
print("🚀 Total episodes to process: ~2,133")
print()

result = batch_episode_recovery_analysis.delay(
    max_episodes=500, 
    recent_only=False
)

print(f'✅ Backfill Task ID: {result.id}')
print(f'✅ Status: {result.status}')
print()
print("🔍 Monitor with:")
print(f"   docker logs -f forestguard-worker-vae")
print()
print("🔍 Check progress every 30 seconds")
