# Utility Scripts

Helper scripts and utility functions for debugging, data inspection, and maintenance tasks.

## Scripts Overview

### 🔍 inspcet_log.py
Inspects and analyzes backtest log files.
- Reads JSON log files from backtest runs
- Provides summary statistics and insights
- Helps debug backtest issues
- Validates log file integrity

**Features:**
- Log file validation
- Event type analysis
- Data quality checks
- Performance summary

**Usage:**
```bash
python inspcet_log.py --log_file logs/backtest_20250802.json
```

### 📊 Equity_curve_decomp.py
Decomposes equity curves into components.
- Analyzes equity curve components
- Breaks down performance drivers
- Identifies key performance periods
- Helps understand strategy behavior

**Features:**
- Equity curve decomposition
- Performance attribution
- Risk factor analysis
- Component breakdown

**Usage:**
```bash
python Equity_curve_decomp.py --results_dir results/strategy_20250802
```

## Utility Functions

### Log Analysis
- **Event Parsing**: Extract and analyze log events
- **Data Validation**: Check for data integrity issues
- **Performance Metrics**: Calculate basic performance stats
- **Error Detection**: Identify potential issues in logs

### Data Inspection
- **File Structure**: Analyze data file organization
- **Data Quality**: Check for missing or invalid data
- **Format Validation**: Ensure data format consistency
- **Size Analysis**: Monitor data file sizes

### Debugging Tools
- **Error Tracking**: Identify and log errors
- **Performance Profiling**: Monitor script execution time
- **Memory Usage**: Track memory consumption
- **Resource Monitoring**: Monitor system resources

## Common Use Cases

### During Development
- Use `inspcet_log.py` to debug backtest issues
- Validate log files for data integrity
- Check performance metrics quickly

### During Analysis
- Use `Equity_curve_decomp.py` to understand strategy performance
- Break down complex equity curves
- Identify key performance drivers

### Maintenance
- Monitor log file sizes and cleanup old files
- Validate data quality across the system
- Check for system resource usage

## Best Practices

1. **Regular Inspection**: Run utility scripts regularly to catch issues early
2. **Log Management**: Keep logs organized and clean up old files
3. **Data Validation**: Use utilities to validate data before analysis
4. **Performance Monitoring**: Track script performance and optimize as needed 