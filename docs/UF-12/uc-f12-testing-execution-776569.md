# UC-F12 Historical Data Processing Execution Plan

This plan outlines the step-by-step execution of UC-F12 testing and manual worker execution within the production VM to populate the vegetation_monitoring and land_use_changes tables for historical data from 2015-2025, requiring special precautions for large-scale processing.

## Historical Data Scale Considerations

- **Time Range**: 2015-01-01 to 2025-10-31 (nearly 11 years of fire detection data)
- **Data Source**: FIRMS raw data files confirmed in `data\raw\firms\`
  - `0_historical_detections_2015_2026.csv` (185MB, 2015-01-01 to 2025-10-31)
  - Recent 2025-2026 supplemental files
- **Estimated Events**: Potentially thousands of fire events from ~185MB of detection data
- **GEE Quota Impact**: ~2-3 requests per event (baseline + current + land use)
- **Processing Time**: Several hours to multiple days for complete historical backfill
- **Memory/Resources**: Extended worker load and database operations

## Prerequisites

- SSH access to production VM as `opc` user
- VM host details (PROD_VM_HOST) - to be provided by user
- Admin JWT token for API testing
- Docker Compose services running on VM

## Phase 1: Infrastructure Verification

### 1.1 Check Worker Status
- SSH into production VM
- Verify worker-vae container is running
- Check celery-beat container status
- Confirm worker-vae is listening to 'vae' queue

### 1.2 Database State Verification
- Check vegetation_monitoring table (expected: 0 rows)
- Check land_use_changes table (expected: 0 rows)  
- Verify eligible fire events exist (should be > 0)
- Confirm UNIQUE constraints and RLS policies exist

### 1.3 API Endpoint Testing
- Test GET /monitoring/recovery/summary without JWT (expect 401)
- Test GET /monitoring/recovery/summary with JWT (expect 200)
- Verify POST /monitoring/recovery/trigger endpoint accessibility

## Phase 2: Strategic Historical Data Processing

### 2.1 Data Assessment (Critical First Step)
- Count total eligible fire events from 2015-2025 with centroid geometry
- Estimate processing time and GEE quota requirements
- Identify any data quality issues upfront

### 2.2 Phased Processing Strategy (Recommended)
**Phase 2A: Recent Events (Last 12 months)**
- Process recent events first for immediate testing
- Validate worker functionality and data quality
- Test frontend components with real data

**Phase 2B: Historical Events (2015-2024)**
- Process in yearly batches to manage load (2015-2024: 10 years)
- Monitor GEE quota consumption carefully  
- Allow for recovery windows between batches
- Prioritize by fire significance/province if needed

### 2.3 Batch Processing Options

**Option A: Conservative Batch Processing**
- Use modified batch function with reduced max_events (20-30)
- Process by year ranges to control GEE quota
- Include delays between batches to prevent rate limiting

**Option B: Single Event Validation First**
- Test with 5-10 diverse events across different years
- Validate data quality and processing accuracy
- Then proceed with batch processing

**Option C: Custom Historical Batch**
- Create specialized task for 2015-2025-10-31 range
- Implement progressive backoff on GEE errors
- Use smaller batch sizes (10-15 events) for stability
- Consider processing by province or fire severity to optimize

## Phase 3: Frontend Verification

### 3.1 Recovery Panel Testing
- Test authenticated user view on /fires/<id>
- Verify RecoveryStatusBadge displays correctly
- Check metric cards (baseline NDVI, current NDVI, recovery %)
- Validate NDVI chart rendering

### 3.2 Empty State Testing
- Test /fires/<id> for events without data
- Verify "Análisis de recuperación pendiente" message
- Confirm panel hides for unauthenticated users

### 3.3 Integration Testing
- Check Home feed for recovery badges
- Verify map markers for potential violations
- Test episode detail view behavior

## Phase 4: Large-Scale Execution Precautions

### 4.1 GEE Quota Management
- **Daily Quota**: 50,000 requests/day (free tier)
- **Per Event Cost**: ~2-3 requests (baseline + current + land use)
- **Safe Batch Size**: 15-20 events per batch
- **Quota Monitoring**: Track consumption between batches
- **Rate Limiting**: Implement delays if approaching limits

### 4.2 Worker Resource Management
- **Memory Monitoring**: Watch worker container memory usage
- **Concurrency Control**: Consider reducing worker concurrency during large batches
- **Error Handling**: Monitor for GEE timeouts and connection issues
- **Log Management**: Ensure adequate log rotation for extended processing

### 4.3 Database Performance
- **Connection Pooling**: Monitor database connection usage
- **Transaction Management**: Use appropriate batch sizes for DB operations
- **Index Performance**: Verify new indexes are being used effectively
- **Storage Planning**: Monitor database growth during processing

### 4.4 Error Recovery Strategies
- **Checkpoint Processing**: Track completed batches to resume on failure
- **Partial Failure Handling**: Isolate problematic events
- **Retry Logic**: Leverage built-in worker retry mechanisms
- **Manual Intervention**: Plan for manual troubleshooting of edge cases

### 4.5 Monitoring and Alerting
- **Progress Tracking**: Log batch completion rates
- **Error Alerts**: Monitor for increased failure rates
- **Performance Metrics**: Track processing time per event
- **Resource Alerts**: Monitor VM memory and CPU usage

## Troubleshooting Procedures

- Worker startup issues (check GEE environment variables)
- Task execution failures (GEE auth, DB connection, geometry)
- Frontend display issues (authentication, routing, data format)

## Phase 5: Execution Timeline and Success Criteria

### 5.1 Recommended Execution Timeline
**Day 1: Infrastructure & Validation**
- Phase 1 verification (2-3 hours)
- Single event testing (1 hour)
- Recent events processing (2-4 hours)

**Day 2-4: Historical Processing**
- Yearly batch processing (6-8 hours per day)
- Progress monitoring and adjustments
- Error recovery and troubleshooting

**Day 5: Final Validation**
- Complete frontend testing
- Performance validation
- Documentation of results

### 5.2 Success Criteria
- [ ] vegetation_monitoring table populated with 2015-01-01 to 2025-10-31 data
- [ ] land_use_changes table populated with applicable events
- [ ] RecoveryPanel displays correctly for authenticated users
- [ ] All API endpoints respond with historical data
- [ ] No critical errors in worker logs
- [ ] GEE quota remains within acceptable limits
- [ ] Database performance remains stable
- [ ] Processing completes within reasonable timeframe (2-5 days)

### 5.3 Risk Mitigation
- **GEE Rate Limiting**: Implement automatic delays and backoff
- **Memory Issues**: Monitor VM resources and adjust batch sizes
- **Data Quality**: Validate sample results during processing
- **Time Constraints**: Prioritize recent data if time is limited

## Required Information from User

1. Production VM host address (PROD_VM_HOST)
2. Admin JWT token for API testing  
3. Preferred processing approach (conservative batch vs single event validation first)
4. Time constraints for completion (2-5 days expected for full historical processing)
