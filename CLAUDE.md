# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] pandas openpyxl plotly requests aiofiles websockets python-multipart aiohttp numpy
```

### Running the Application
```bash
# Start the server (from project root)
cd server
uvicorn app:app --host 127.0.0.1 --port 8010

# Or use the batch file (Windows)
Run.bat                    # Opens browser automatically
Run.bat --no-open         # Skip browser auto-open
```

### Testing
```bash
# Run comprehensive test suite
python test_comprehensive_suite.py

# Run specific test modules
python test_3_layer_system.py      # Test 3-layer architecture
python test_plotly_integration.py  # Test visualization system
python test_rules_system.py        # Test rules management
python test_frontend_integration.py # Test frontend integration
python test_send_button.py         # Test send button functionality
```

## Architecture Overview

### 3-Layer Processing System
The application implements a sophisticated 3-layer data analysis pipeline:

1. **Layer 1 (Metadata Extraction)**: Analyzes uploaded files using `metadata_extractor.py` to extract comprehensive metadata, statistics, and data quality indicators.

2. **Layer 2 (Code Generation & Execution)**: Uses `code_executor.py` to safely execute Python code in a sandboxed environment with restricted imports and timeout protection.

3. **Layer 3 (Results Commentary)**: Leverages the LLM to provide natural language interpretation of analysis results through `lm_studio_client.py`.

### WebSocket Streaming Architecture
- **Real-time streaming**: Implements incremental JSON parsing in `lm_studio_client.py` for immediate response rendering
- **Delta-based updates**: Frontend receives only new content chunks, not full responses
- **Field-by-field streaming**: Analysis, code, and results stream independently as they become available

### Key Components
- **`server/app.py`**: FastAPI application with WebSocket endpoints for real-time chat
- **`server/lm_studio_client.py`**: Handles LM Studio API integration with structured response streaming
- **`server/code_executor.py`**: Sandboxed Python execution with security restrictions
- **`server/file_handler.py`**: Manages file uploads and dataframe persistence
- **`server/metadata_extractor.py`**: Extracts comprehensive file metadata
- **`server/rules_manager.py`**: Manages user-defined analysis rules
- **`index.html`**: Single-page frontend with Tailwind CSS and real-time WebSocket handling

## Critical Implementation Details

### Data Access in Code Execution
**NEVER use `pd.read_csv()` in generated code** - The uploaded data is pre-loaded as `df`:
```python
# CORRECT - Use the pre-loaded dataframe
saudi_patients = df[df['Nationality'].str.contains('Saudi')]

# WRONG - Never try to read files
df = pd.read_csv('filename.csv')  # This will fail!
```

### Security Sandbox Configuration
The code executor restricts imports to:
- Core data libraries: pandas, numpy, plotly
- Essential Python modules: datetime, math, statistics, json, re, itertools
- No file system access except through the pre-loaded `df` variable

### WebSocket Message Protocol
Messages follow a structured JSON format with streaming support:
```json
{
  "initial_response": "Analysis explanation...",
  "generated_code": "Python code string...",
  "result_commentary": "Natural language interpretation..."
}
```

### Plotly Integration
- Frontend uses Plotly 2.30.1 (fixed version for compatibility)
- Backend suppresses `fig.show()` to prevent browser tab spawning
- Visualizations are serialized as JSON and rendered client-side

## File Structure Conventions

### Data Files
- Sample datasets in root: `hospital_patients.csv`, `comprehensive_test_data.csv`
- Uploaded files stored in `uploads/` directory
- Configuration persisted in `config/rules.json`

### Frontend Resources
- Single-page application: `index.html`
- Uses CDN resources: Tailwind CSS, Material Icons, Plotly 2.30.1
- WebSocket connection management with automatic reconnection

## LM Studio Integration

### Prerequisites
- LM Studio must run on `http://127.0.0.1:1234`
- Load a compatible model (Qwen, Llama, etc.)
- Server checks health on startup and provides fallback handling

### Structured Response Format
The system prompt enforces a specific JSON structure for consistent streaming and parsing. The LLM is instructed to always use the pre-loaded `df` variable and never attempt file I/O operations.

## Known Test Coverage
- Simple data analysis: 4/4 tests passing
- Advanced analysis: 3/4 tests passing
- Visualization: 3/4 tests passing
- File operations: 4/4 tests passing
- Rules system: 3/3 tests passing
- Overall success rate: 89.7%