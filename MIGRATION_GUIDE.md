# Migration Guide: AI Data Analysis Application v2.0

This guide provides step-by-step instructions for migrating from the current system to the new robust architecture (v2.0).

## 🎯 Migration Overview

The new architecture introduces significant improvements while maintaining backward compatibility. The migration can be performed with zero downtime using the parallel deployment strategy outlined below.

## 📋 Pre-Migration Checklist

### System Requirements
- [ ] Python 3.8+ with virtual environment
- [ ] All existing dependencies installed
- [ ] LM Studio running on `http://127.0.0.1:1234`
- [ ] Current system backed up

### Verification Steps
- [ ] Run existing tests to ensure current system is working
- [ ] Verify file upload functionality
- [ ] Test WebSocket connections
- [ ] Confirm LM Studio integration

## 🚀 Migration Steps

### Phase 1: Install New Architecture Components

1. **Verify New Components**
   ```bash
   # Test the new architecture
   python test_new_architecture.py
   ```
   
   Expected output: `5/5 tests passed (100.0%)`

2. **Backup Current System**
   ```bash
   # Create backup of current app.py
   cp server/app.py server/app_v1_backup.py
   ```

### Phase 2: Parallel Deployment

1. **Deploy New Application**
   ```bash
   # The new application is in server/app_v2.py
   # Test it on a different port first
   cd server
   uvicorn app_v2:app --host 127.0.0.1 --port 8011
   ```

2. **Test New System**
   - Open browser to `http://127.0.0.1:8011`
   - Upload test data file
   - Run Saudi patient analysis query
   - Verify no JSON serialization errors
   - Confirm code blocks display correctly

3. **Compare Performance**
   - Test the same queries on both systems
   - Verify new system handles NaT values correctly
   - Confirm no code corruption issues

### Phase 3: Production Cutover

1. **Stop Current System**
   ```bash
   # Stop the current application (Ctrl+C if running in terminal)
   ```

2. **Replace Main Application**
   ```bash
   # Replace the main app with the new version
   cp server/app_v2.py server/app.py
   ```

3. **Start New System**
   ```bash
   # Start the new application
   cd server
   uvicorn app:app --host 127.0.0.1 --port 8010
   ```

### Phase 4: Verification

1. **Health Check**
   ```bash
   # Check system health
   curl http://127.0.0.1:8010/health
   ```
   
   Expected response should include:
   ```json
   {
     "status": "healthy",
     "version": "2.0.0",
     "system_health": {
       "overall_health": "healthy"
     }
   }
   ```

2. **Component Statistics**
   ```bash
   # Check component statistics
   curl http://127.0.0.1:8010/stats
   ```

3. **Test Critical Use Cases**
   - Upload hospital_patients.csv
   - Run: "I want you to deeply analyze and compare the admission rate changes between 2024 and 2025 for Saudi patients"
   - Verify no "NaTType is not JSON serializable" errors
   - Confirm code blocks display properly
   - Check that generated code executes without corruption

## 🔧 Configuration Changes

### New Environment Variables (Optional)
```bash
# Circuit breaker configuration
export CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
export CIRCUIT_BREAKER_TIMEOUT=60

# Validation settings
export VALIDATION_AUTO_FIX_ENABLED=true
export SERIALIZATION_STATS_ENABLED=true
```

### New Endpoints
- `GET /health` - Enhanced health check with component status
- `GET /stats` - Comprehensive system statistics

## 🚨 Rollback Plan

If issues are encountered, you can quickly rollback:

1. **Stop New System**
   ```bash
   # Stop the new application
   ```

2. **Restore Original**
   ```bash
   # Restore the original application
   cp server/app_v1_backup.py server/app.py
   ```

3. **Restart Original System**
   ```bash
   cd server
   uvicorn app:app --host 127.0.0.1 --port 8010
   ```

## 🧪 Testing Strategy

### Automated Testing
```bash
# Run comprehensive test suite
python test_new_architecture.py

# Run specific component tests
python test_simple_architecture.py
python test_validation_debug.py
```

### Manual Testing Scenarios

1. **Basic Functionality**
   - File upload and metadata extraction
   - Simple data analysis queries
   - Code generation and execution

2. **Error Handling**
   - Upload invalid file formats
   - Send malformed queries
   - Test with LM Studio offline

3. **Saudi Patient Analysis (Critical Test)**
   - Upload comprehensive_test_data.csv
   - Query: "Analyze Saudi patient admission trends"
   - Verify no JSON serialization errors
   - Confirm accurate results

4. **Code Block Styling**
   - Verify syntax highlighting works
   - Test copy-to-clipboard functionality
   - Check responsive design on mobile

## 📊 Success Metrics

### Performance Indicators
- [ ] Zero JSON serialization errors
- [ ] No code corruption in generated responses
- [ ] All WebSocket connections stable
- [ ] Circuit breakers functioning correctly
- [ ] Response validation passing 100%

### User Experience
- [ ] Code blocks display with proper styling
- [ ] Copy functionality works correctly
- [ ] Real-time streaming maintains smooth updates
- [ ] Error messages are clear and actionable

## 🔍 Monitoring

### Key Metrics to Monitor
- Component health status
- Circuit breaker states
- Validation success rates
- Serialization statistics
- Error frequencies by component

### Log Locations
- Application logs: Console output
- Component statistics: `GET /stats` endpoint
- Health status: `GET /health` endpoint

## 🆘 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure all new modules are in the correct location
   ls server/serialization_engine.py
   ls server/validation_engine.py
   ls server/response_manager.py
   ls server/streaming_controller.py
   ls server/error_handler.py
   ```

2. **Circuit Breaker Issues**
   ```bash
   # Reset circuit breakers via health endpoint
   curl -X POST http://127.0.0.1:8010/health/reset
   ```

3. **Validation Failures**
   - Check validation statistics in `/stats`
   - Review validation warnings in logs
   - Verify code syntax is correct

### Support Contacts
- Architecture issues: Review component documentation
- Performance issues: Check circuit breaker states
- Data issues: Verify serialization statistics

## 📚 Additional Resources

- [Architecture Overview](README.md#architecture-overview)
- [Component Documentation](server/)
- [Test Suite](test_new_architecture.py)
- [Changelog](CHANGELOG.md)

---

**Migration completed successfully when:**
- All tests pass (5/5)
- Health check returns "healthy" status
- Saudi patient analysis works without errors
- Code blocks display with proper styling
- No JSON serialization errors in logs
