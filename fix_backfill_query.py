# Fix the backfill SQL query to use event centroid instead of episode centroid

# The issue: fire_episodes table doesn't have centroid column
# Solution: Use AVG of event centroids for episode location

fixed_query = """
            SELECT ep.id, ep.status, ep.created_at,
                   COUNT(fe.id) as event_count,
                   MAX(fe.start_date) as latest_fire_date,
                   AVG(ST_Y(fe.centroid::geometry)) as lat,
                   AVG(ST_X(fe.centroid::geometry)) as lon,
                   CASE WHEN ep.status = 'active' THEN 1
                        WHEN ep.status = 'monitoring' THEN 2
                        ELSE 3 END as status_priority
            FROM fire_episodes ep
            JOIN fire_episode_events fee ON ep.id = fee.episode_id
            JOIN fire_events fe ON fee.event_id = fe.id
            WHERE fe.centroid IS NOT NULL
            GROUP BY ep.id, ep.status, ep.created_at
            ORDER BY status_priority, ep.created_at DESC
            LIMIT :max_episodes
        """

print("Fixed SQL Query:")
print(fixed_query)
