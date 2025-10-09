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

#### Main Application (Python/FastAPI)
```bash
# Start the server (from project root)
cd server
uvicorn app:app --host 127.0.0.1 --port 8010

# Or use the batch file (Windows)
Run.bat                    # Opens browser automatically
Run.bat --no-open         # Skip browser auto-open
```

The application runs on `http://127.0.0.1:8010` with the primary frontend in `index.html`.

### Testing
```bash
# All test files are in the "testing stuff" directory
cd "testing stuff"

# Run comprehensive test suite
python test_comprehensive_suite.py

# Run specific test modules
python test_3_layer_system.py      # Test 3-layer architecture
python test_plotly_integration.py  # Test visualization system
python test_rules_system.py        # Test rules management
python test_frontend_integration.py # Test frontend integration
python test_send_button.py         # Test send button functionality
python test_new_architecture.py    # Test validation/serialization/streaming architecture
python test_live_backend.py        # Test against running backend
python test_running_server.py      # Test running server
```

## Architecture Overview

### 3-Layer Processing System
The application implements a sophisticated 3-layer data analysis pipeline with optimized output display:

**Layer 1 (Metadata Extraction)**: Analyzes uploaded files using `metadata_extractor.py` to extract comprehensive metadata, statistics, and data quality indicators.

**Layer 2 (Code Generation & Execution)**: Uses `code_executor.py` to safely execute Python code in a sandboxed environment with restricted imports and timeout protection.

**Layer 3 (Results Commentary)**: Leverages the LLM to provide natural language interpretation of analysis results through `lm_studio_client.py`.

### Response Display Order (v2.3.1+)
Responses are displayed in this optimized sequence:
1. **Analysis** - LLM's explanation of the approach
2. **Python Code Block** - Generated code with syntax highlighting and copy functionality
3. **Plot/Visualization** - Interactive Plotly charts (conditional, when applicable)
4. **Results Block** - Prominent display of final answer with gradient background and skeleton loader during execution
5. **Commentary** - Additional context and interpretation

### WebSocket Streaming Architecture
- **Real-time streaming**: Implements incremental JSON parsing in `lm_studio_client.py` for immediate response rendering
- **Delta-based updates**: Frontend receives only new content chunks, not full responses
- **Field-by-field streaming**: Analysis, code, and results stream independently as they become available
- **Event types**: `start`, `delta`, `replace`, `field_complete`, `end`, `stream_error`, `warnings`

### Key Components

#### Core Backend Modules
- **`server/app.py`**: FastAPI application with WebSocket endpoints for real-time chat. Implements the main request/response loop with 3-layer processing integration.
- **`server/lm_studio_client.py`**: Handles LM Studio API integration with structured response streaming
- **`server/code_executor.py`**: Sandboxed Python execution with security restrictions
- **`server/file_handler.py`**: Manages file uploads and dataframe persistence
- **`server/metadata_extractor.py`**: Extracts comprehensive file metadata
- **`server/rules_manager.py`**: Manages user-defined analysis rules

#### Advanced Architecture Components (Reliability & Validation)
- **`server/validation_engine.py`**: Comprehensive validation for LLM responses, generated code, and execution results. Provides auto-fix capabilities for common corruption patterns (escape sequences, syntax errors, JSON formatting).
- **`server/serialization_engine.py`**: Handles safe serialization of Python objects (DataFrames, Plotly figures, NumPy arrays) for WebSocket transmission. Prevents JSON serialization errors.
- **`server/streaming_controller.py`**: Manages WebSocket streaming with atomic operations. Provides smooth real-time updates with delta-based content delivery (8-character chunks with 20ms delay).
- **`server/response_manager.py`**: Atomic response processing with validation and rollback capabilities. Collects complete responses, validates them, and only streams validated content.
- **`server/error_handler.py`**: Circuit breaker patterns for system components (LM Studio, code executor, file handler). Prevents cascading failures and provides graceful degradation.

#### Frontend
- **`index.html`**: Single-page frontend with Tailwind CSS, collapsible sidebar (Ctrl/Cmd+B), and real-time WebSocket handling with incremental content rendering
- **Skeleton loader animations**: Professional loading states during code execution (v2.3.0+)
- **AI Sima branding**: Integrated logo with consistent visual identity

## Critical Implementation Details

### Data Access in Code Execution
**NEVER use `pd.read_csv()` in generated code** - The uploaded data is pre-loaded as `df`:
```python
# CORRECT - Use the pre-loaded dataframe and assign to 'result'
saudi_patients = df[df['Nationality'].str.contains('Saudi')]
result = len(saudi_patients)  # MUST assign output to 'result' variable

# WRONG - Never try to read files
df = pd.read_csv('filename.csv')  # This will fail!

# WRONG - No result variable
df.head(5)  # Output not captured!
```

**CRITICAL**: Always assign final output to a variable named `result`, `output`, or for Plotly visualizations, `fig`/`figure`. This is how the system captures execution results.

### Security Sandbox Configuration
The code executor restricts imports to:
- Core data libraries: pandas, numpy, plotly
- Essential Python modules: datetime, math, statistics, json, re, itertools
- No file system access except through the pre-loaded `df` variable
- Validation engine automatically detects and blocks dangerous operations (exec, eval, file I/O, os/sys/subprocess calls)

### WebSocket Message Protocol
Messages follow a structured JSON format with streaming support:
```json
{
  "event": "delta",           // Incremental content update
  "field": "initial_response", // Field being updated
  "delta": "new content...",   // 8-character chunks
  "position": 0                // Position in content stream
}

// Final message:
{
  "event": "end",
  "final": {
    "initial_response": "...",
    "generated_code": "...",
    "result_commentary": "..."
  },
  "execution_results": { ... }
}
```

### Plotly Integration
- Frontend uses Plotly 2.30.1 (fixed version for compatibility)
- Backend suppresses `fig.show()` to prevent browser tab spawning
- Visualizations are serialized as JSON and rendered client-side
- Serialization engine handles Plotly figure conversion automatically

### Skeleton Loader Feature (v2.3.0+)
Professional shimmer animation during code execution in Results Block:
- **GPU-accelerated CSS animation** with 2-second cycle
- **Matches Results Block styling** for smooth transitions
- **Dark mode support** with automatic theme adaptation
- **Smart display logic**: Shows during execution, hides when results ready
- Located in Results Block (`#results-skeleton` container)

## File Structure Conventions

### Data Files
- Sample datasets in root: `hospital_patients.csv`, `comprehensive_test_data.csv`
- Uploaded files stored in `uploads/` directory
- Configuration persisted in `config/rules.json` and `server/config/rules.json`

### Frontend Resources
- **Primary Frontend**: Single-page application in root `index.html`
  - Uses CDN resources: Tailwind CSS, Material Icons, Plotly 2.30.1, Prism.js for syntax highlighting
  - WebSocket connection management with automatic reconnection
  - Collapsible sidebar with `Ctrl/Cmd+B` shortcut
  - Professional branding with AI Sima logo

### Directory Structure
- `server/`: Python FastAPI backend application
- `testing stuff/`: All test files and test utilities
- `uploads/`: File upload storage
- `config/`: Configuration files
- `docs/`: Documentation including architecture, changelogs, and feature docs (e.g., `SKELETON_LOADER.md`)

## LM Studio Integration

### Prerequisites
- LM Studio must run on `http://127.0.0.1:1234`
- Load a compatible model (Qwen, Llama, etc.)
- Server checks health on startup and provides fallback handling

### Structured Response Format
The system prompt enforces a specific JSON structure for consistent streaming and parsing. The LLM is instructed to always use the pre-loaded `df` variable and never attempt file I/O operations.

## Advanced Architecture Patterns

### Reliability & Fault Tolerance

**Circuit Breaker Pattern** (`error_handler.py`):
- Monitors component health (LM Studio, code executor, serialization, validation, file handler)
- Automatically opens circuits after repeated failures (configurable thresholds)
- Prevents cascading failures across system components
- Component states: HEALTHY → DEGRADED → FAILING → CIRCUIT_OPEN → RECOVERING

**Atomic Response Processing** (`response_manager.py`):
- Collects complete LLM responses before validation
- Validates all content (syntax, security, structure) before streaming
- Implements automatic recovery for common issues (escape sequences, syntax errors)
- Performs complete rollback if validation fails
- Response states: INITIALIZING → COLLECTING → VALIDATING → VALIDATED → STREAMING → COMPLETED

**Validation Engine** (`validation_engine.py`):
- JSON structure validation with auto-fix for common formatting errors
- Python syntax validation with AST parsing
- Security validation blocking dangerous operations
- Escape sequence cleaning for corrupted code
- Auto-fix capabilities for: trailing backslashes, unclosed structures, malformed escape sequences

**Serialization Engine** (`serialization_engine.py`):
- Safe handling of Plotly figures, DataFrames, NumPy arrays
- NaN/Infinity value handling for JSON compatibility
- Prevention of circular reference errors
- Automatic type conversion for WebSocket transmission

**Streaming Controller** (`streaming_controller.py`):
- Atomic WebSocket operations with error recovery
- Delta-based content streaming (8-character chunks, 20ms delay)
- Stream state tracking and monitoring
- Graceful error handling during streaming

### Response Processing Flow
```
User Query → WebSocket
  ↓
LM Studio (Layer 1: Analysis)
  ↓
Response Manager (Collect & Validate)
  ↓
Validation Engine (Auto-fix if needed)
  ↓
Streaming Controller (Delta streaming)
  ↓
Code Executor (Layer 2: Execution)
  ↓
Serialization Engine (Safe serialization)
  ↓
LM Studio (Layer 3: Commentary)
  ↓
Response Manager (Validate commentary)
  ↓
Streaming Controller (Stream to frontend)
  ↓
WebSocket → Frontend (Incremental rendering)
```

### Error Recovery Strategies
1. **JSON Parsing Errors**: Auto-fix trailing commas, unescaped quotes, missing braces
2. **Code Syntax Errors**: Auto-fix trailing backslashes, unclosed structures, escape sequences
3. **Serialization Errors**: Convert NaN to null, handle circular references, type conversion
4. **LM Studio Failures**: Fallback responses, circuit breaker prevents repeated calls
5. **Code Execution Errors**: Timeout protection, security validation, result capture

## Key Development Considerations

### When Modifying Core Processing
1. **WebSocket Streaming**: Changes to streaming must maintain delta-based updates. The frontend expects incremental 8-character chunks for smooth rendering.
2. **Validation Pipeline**: Always validate before streaming. The `response_manager.py` ensures atomic operations - responses are validated completely before any streaming begins.
3. **Code Execution**: Never modify the pre-loaded `df` variable name or the requirement for `result` variable in generated code. This is fundamental to the system.
4. **Circuit Breakers**: Be aware that repeated failures will open circuits. Test error handling thoroughly to avoid triggering circuit breakers during normal operation.

### When Adding New Features
1. **Component Registration**: Register new components in `error_handler.py` circuit breaker initialization if they can fail
2. **Serialization Support**: Add type handlers to `serialization_engine.py` if introducing new data types
3. **Validation Rules**: Add validation patterns to `validation_engine.py` for new security concerns
4. **WebSocket Events**: Document new event types if extending the WebSocket protocol

### Performance Characteristics
- **Streaming Delay**: 20ms between 8-character chunks (configurable in `streaming_controller.py`)
- **Code Execution Timeout**: Defined in `code_executor.py` (default protection against infinite loops)
- **Circuit Breaker Thresholds**:
  - LM Studio: 3 consecutive failures, 30s timeout
  - Code Executor: 5 consecutive failures, 60s timeout
  - File operations: 5 consecutive failures, 60s timeout

### Auto-loaded Files
- `hospital_patients.csv` is automatically loaded on server startup if present in `../uploads/` directory
- Check server logs for auto-load success/failure messages

### Important System Prompts
The system prompt in `app.py` is critical for proper LLM behavior:
- Instructs LLM to use pre-loaded `df` variable (NEVER `pd.read_csv()`)
- Requires assignment to `result`/`output`/`fig` variables
- Defines the 3-layer response structure
- This prompt should be modified carefully as it affects all LLM-generated code

### Context Truncation
`app.py` implements intelligent context truncation to prevent token overflow:
- Analysis: 2000 chars
- Code: 6000 chars
- Output: 2000 chars
- Result: 2000 chars
- Plotly figures omitted from commentary context with placeholder note

### Batch Scripts (Windows)
- **`Run.bat`**: Starts the server with environment validation
  - Checks for virtual environment and LM Studio availability
  - Auto-opens browser by default (use `--no-open` to skip)
  - Provides helpful error messages for missing dependencies
- **`Setup.bat`**: Creates virtual environment and installs dependencies

## Recent Improvements (v2.3.x)

### UI/UX Enhancements
- Skeleton loader animations with GPU-accelerated shimmer effect
- Premium input design with improved animations
- Enhanced commentary handling with reveal functions and timers
- Optimized response display order prioritizing code visibility

### Architecture Refinements
- Comprehensive context truncation to manage token limits
- Improved error handling in response processing
- Enhanced result extraction and formatting
- Better separation of Results Block and Commentary sections
