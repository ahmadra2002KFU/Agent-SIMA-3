# LLM-Powered Chatbot Web Interface

A comprehensive local LLM-powered chatbot web interface with advanced file processing, real-time streaming, and interactive data analysis capabilities.

## 🌟 Features

### Core Functionality
- **Real-time WebSocket streaming** for live LLM responses
- **File upload support** for CSV and XLSX files with validation, automatic Excel-to-CSV normalization, and real-time progress feedback
- **3-layer processing architecture** for comprehensive data analysis
- **Sandboxed code execution** with security restrictions
- **Interactive Plotly visualizations** with publication-ready styling
- **User-defined rules system** with persistent configuration
- **Modern responsive UI** with dark/light theme support
- **Collapsible sidebar** with toggle button and keyboard shortcuts (Ctrl/Cmd + B)

### Advanced Capabilities
- **Comprehensive metadata extraction** from uploaded datasets
- **Secure Python code execution** with data analysis libraries
- **Real-time streaming responses** with structured JSON output
- **Custom visualization generation** with professional styling
- **Session persistence** for user preferences and rules
- **Complete API ecosystem** for programmatic access
- **Professional branding** with integrated AI Sima logo and consistent visual identity
- **Skeleton loader animations** for polished loading states during code execution

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- LM Studio running locally on port 1234
- Modern web browser with WebSocket support

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Agent-SIMA-3
```

2. **Create and activate virtual environment**:
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install fastapi uvicorn[standard] pandas openpyxl plotly requests aiofiles websockets python-multipart aiohttp
```

4. **Start LM Studio**:
   - Download and install LM Studio
   - Load a compatible model (e.g., Qwen, Llama, etc.)
   - Start the local server on port 1234

5. **Start the application**:
```bash
cd server
uvicorn app:app --host 127.0.0.1 --port 8010
```

6. **Open your browser**:
   Navigate to `http://localhost:8010`


## 🧭 From zero to running (Windows tutorial)

1. Open PowerShell in the project root (Agent-SIMA-3)
2. Create and activate venv:
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
3. Install deps:
   - `pip install -r requirements.txt` if available; otherwise:
   - `pip install fastapi uvicorn[standard] pandas openpyxl plotly requests aiofiles websockets python-multipart aiohttp`
4. Start LM Studio (port 1234) and load a model.
5. Start the server:
   - `cd server` ; `uvicorn app:app --host 127.0.0.1 --port 8010`
6. Open http://127.0.0.1:8010 in your browser.

### Verifying realtime streaming
- Ask: "I want you to deeply analyze and compare the admission rate changes between 2024 and 2025 for Saudi patients".
- Expect:
  - UI shows Analysis/Generated Code/Results sections immediately (~1–2s)
  - Text grows progressively per section
  - No full-response buffering

If LM Studio isn’t running, you’ll see a fallback message; streaming still works, but analysis quality will be limited.

### Troubleshooting streaming
- WebSocket must connect (no 403/upgrade errors). Check Console.
- If text appears all at once, ensure you’re running this repo’s server (not a static file), and confirm `uvicorn app:app` is started from the `server` folder.
- On proxies/CDNs: avoid them in local dev; they may buffer.

## 🏗️ Architecture

### 3-Layer Processing System

The system processes user queries through three distinct layers, with an optimized output format that prioritizes code visibility and provides clear, prominent results.

#### Output Display Order (Updated in v2.3.1)

Responses are displayed in the following optimized sequence:

1. **Analysis** (FIRST)
   - LLM's explanation of the approach
   - Methodology description
   - Provides context before showing implementation
   - Educational insights

2. **Python Code Block** (SECOND)
   - Generated code with syntax highlighting
   - Copy-to-clipboard functionality
   - Shows the exact analysis approach
   - Helps users learn data analysis techniques

3. **Plot/Visualization** (THIRD, conditional)
   - Interactive Plotly charts
   - Only displayed when visualizations are generated
   - Professional styling with responsive design
   - Reduces clutter when not needed

4. **Results Block** (FOURTH, NEW)
   - **Prominent display** of the final answer
   - Large, bold typography with gradient background
   - Automatically extracts primary result (`result`, `output`, `summary`, etc.)
   - Smart number formatting with locale support
   - Visually distinct from commentary
   - Skeleton loader animation during code execution

5. **Commentary** (FIFTH)
   - Additional context and interpretation
   - Insights about the findings
   - Recommendations and next steps
   - Separated from results for clarity

#### Layer 1: Metadata Extraction
- **Purpose**: Comprehensive analysis of uploaded files
- **Features**:
  - Basic file information (rows, columns, size)
  - Column data types and statistics
  - Missing value analysis
  - Data quality indicators
  - Sample data preview

#### Layer 2: Code Generation & Execution
- **Purpose**: Secure Python code execution for data analysis
- **Features**:
  - Sandboxed execution environment
  - Restricted imports (pandas, numpy, plotly only)
  - Security validation
  - Timeout protection
  - Result capture and serialization
  - **Code-first generation** (prioritizes showing code before analysis)

#### Layer 3: Results Commentary
- **Purpose**: Natural language interpretation of analysis results
- **Features**:
  - LLM-powered result interpretation
  - Context-aware commentary
  - Integration with user-defined rules
  - Actionable insights generation
  - **Split display**: Results Block + Commentary for better readability

### Technology Stack

- **Backend**: FastAPI with async WebSocket support
- **Frontend**: HTML5, Tailwind CSS, Material Icons
- **LLM Integration**: LM Studio API with structured responses
- **Data Processing**: Pandas, NumPy, Plotly
- **Security**: Restricted execution environment
- **Persistence**: JSON-based configuration storage

## 🧪 Testing

Run the comprehensive test suite:
```bash
# Run all tests
python test_comprehensive_suite.py

# Run specific test categories
python test_3_layer_system.py      # 3-layer architecture
python test_plotly_integration.py  # Visualization system
python test_rules_system.py        # Rules management
python test_frontend_integration.py # Frontend integration
```

**Test Results**: 89.7% success rate with comprehensive coverage of all components.

## 🔒 Security

### Code Execution Security
- **Sandboxed environment** with restricted imports
- **Limited builtin functions** access
- **Input validation** for all code execution
- **Timeout protection** against infinite loops
- **Memory usage monitoring**

### File Upload Security
- **File type validation** (CSV, XLSX only)
- **Size limits** to prevent abuse
- **Content validation** before processing
- **Temporary file cleanup**

## 📁 Project Structure

```
Agent-SIMA-3/
├── aisimalogo.png          # Official AI Sima logo file
├── index.html              # Main frontend interface
├── server/                 # Backend FastAPI application
│   ├── app.py             # Main application server
│   ├── lm_studio_client.py # LM Studio integration
│   ├── code_executor.py   # Sandboxed code execution
│   ├── file_handler.py    # File upload processing
│   └── ...                # Other backend modules
├── uploads/               # Uploaded file storage
├── config/                # Configuration files
└── README.md              # This file
```

## 🎛️ User Interface Features

### Sidebar Toggle
- **Toggle Button**: Click the hamburger menu (☰) in the header to collapse/expand the sidebar
- **Keyboard Shortcut**: Press `Ctrl+B` (Windows/Linux) or `Cmd+B` (Mac) to toggle
- **State Persistence**: Your sidebar preference is remembered across sessions
- **Responsive Design**:
  - **Desktop**: Sidebar pushes content, main area expands when collapsed
  - **Mobile**: Sidebar overlays content with backdrop, starts collapsed

### Layout Optimization
- **Space Management**: Collapse sidebar to gain 288px of horizontal space for data analysis
- **Focus Mode**: Hide sidebar distractions when working with visualizations
- **Quick Access**: Toggle button always visible in header for easy access

## 📖 Usage

1. **Upload a file**: Drag & drop or select CSV/XLSX files
2. **Add custom rules**: Define analysis preferences in the sidebar
3. **Toggle sidebar**: Use the hamburger menu or Ctrl/Cmd+B to optimize your workspace
4. **Chat with AI**: Ask questions about your data
5. **View results**: See real-time streaming responses in optimized order:
   - **Python Code** - See the generated code first
   - **Visualizations** - Interactive charts (when applicable)
   - **Analysis** - Explanation of the approach
   - **Results** - Prominent display of the final answer
   - **Commentary** - Additional insights and context

### Example Workflow

**Query**: "How many Saudi patients are there?"

**Response Display**:

1. **Code Block**:
```python
saudi_patients = df[df['Nationality'].str.contains('Saudi', case=False, na=False)]
result = len(saudi_patients)
```

2. **Visualization**: _(Skipped - no chart needed for simple count)_

3. **Analysis**: "I filtered the Nationality column using string matching to identify all patients with 'Saudi' nationality, ensuring case-insensitive matching and handling missing values."

4. **Results Block**:
```
54
Primary result from 'result' variable
```
_(Displayed in large, bold text with gradient background)_

5. **Commentary**: "This represents 18% of the total patient population in the dataset. The analysis found patients across multiple departments with varying admission dates."

## 🆘 Troubleshooting

### Common Issues

**LM Studio Connection Failed**:
- Ensure LM Studio is running on port 1234
- Check that a model is loaded and active
- Verify firewall settings

**File Upload Issues**:
- Check file format (CSV/XLSX only)
- Verify file size limits
- Ensure proper encoding (UTF-8)

**WebSocket Connection Problems**:
- Check browser console for errors
- Verify server is running on correct port
- Test with different browsers

## 📄 License

This project is licensed under the MIT License.

