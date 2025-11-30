# Streamlit Web Interface for Company Research Agent V2.8

A simple, user-friendly web interface for the Company Private Investing Research Agent.

## Features

- ✅ **Two Input Methods**: Manual form entry OR config file upload
- ✅ **Live Progress Tracking**: Real-time log streaming shows all research phases
- ✅ **Inline Report Preview**: View markdown reports directly in the browser
- ✅ **Download Reports**: Download both markdown and JSON formats
- ✅ **Structured Data View**: Expandable JSON viewer for detailed data
- ✅ **Performance Metrics**: See execution time, pages scraped, and report size

## Installation

### 1. Install Streamlit

```bash
pip install -r requirements-streamlit.txt
```

### 2. Verify Installation

```bash
streamlit --version
```

## Usage

### Starting the App

From the project root directory:

```bash
streamlit run app.py
```

The app will automatically open in your default browser at `http://localhost:8501`.

### Manual Input Method

1. Open the **Manual Input** tab
2. Fill in the form:
   - **Company Name**: e.g., "Wellington Management"
   - **Research Question**: e.g., "Analyze private markets activities"
   - **Seed URLs**: One URL per line (e.g., company website pages)
3. Check **Enable verbose logging** to see detailed progress
4. Click **▶ Start Research**

**Example:**
```
Company Name: Wellington Management

Research Question: Analyze Wellington Management's private markets and investing
activities, including strategies, portfolio, team, and recent news.

Seed URLs:
https://www.wellington.com/en/capabilities/private-investing
https://www.wellington.com/en/capabilities/private-investing/our-team
https://www.wellington.com/en/capabilities/private-investing/portfolio
```

### Config File Upload Method

1. Open the **Upload Config** tab
2. Click **Browse files** and select your `config.json` file
3. Preview the configuration
4. Check **Enable verbose logging** to see detailed progress
5. Click **▶ Start Research from Config**

**Config File Format:**
```json
{
  "company_name": "Wellington Management",
  "request": "Analyze private markets and investing activities",
  "seed_urls": [
    "https://www.wellington.com/en/capabilities/private-investing",
    "https://www.wellington.com/en/capabilities/private-investing/our-team",
    "https://www.wellington.com/en/capabilities/private-investing/portfolio"
  ]
}
```

## Live Progress

When verbose logging is enabled, you'll see real-time progress:

```
================================================================================
PHASE 1: PLANNING
================================================================================

💭 Checking if clarification needed...
✓ No clarification needed

📝 Generating research sub-questions...

================================================================================
PHASE 2: RESEARCH SUPERVISOR
================================================================================

🌐 [1/4] Fetching seed URLs...
   🔗 Fetching: https://www.wellington.com/...
   ✓ Fetched 10/10 pages (total: 3.2 MB)

🤖 [3/4] Executing 6 sub-agents in parallel (3 workers)...
  → Sub-agent working on: q_0
  ✓ Sub-agent completed: q_0 (confidence: high)

================================================================================
PHASE 2.5: TARGETED REFINEMENT
================================================================================

🔍 [2/3] Creating targeted follow-up tasks...
   Refinement for q_5:
      Gap: Missing aspects: news items
      MCP Patterns: news_dates
```

## Viewing Results

### Statistics

After research completes, you'll see:

| Metric | Description |
|--------|-------------|
| **Total Time** | Total execution time in seconds |
| **Pages Scraped** | Number of web pages fetched and processed |
| **Sub-Agents** | Number of sub-agent research tasks executed |
| **Report Size** | Size of the generated markdown report |

### Markdown Report

The full markdown report is displayed inline with proper formatting:
- Headings, tables, lists
- Inline citations [1], [2], [3]
- Company overview, team, portfolio, news, etc.

### Download Reports

Two download buttons are provided:
- **📥 Download Markdown Report**: `.md` file for viewing/editing
- **📥 Download JSON Report**: `.json` file for programmatic access

### Structured JSON Data

Click the expander to view the structured data:
```json
{
  "company_name": "Wellington Management",
  "executive_summary": "...",
  "key_decision_makers": [...],
  "portfolio_companies": [...],
  "news_announcements": [...]
}
```

## Research Phases

The agent executes in 4 phases:

1. **PLANNING**: Generates research sub-questions
2. **RESEARCH**: Supervisor coordinates 6 parallel sub-agents
3. **REFINEMENT**: MCP intelligent search fills gaps (if needed)
4. **WRITING**: Generates markdown + JSON reports

## Tips

### For Best Results

✅ **Provide specific seed URLs**: Include pages for team, portfolio, news, etc.
✅ **Enable verbose logging**: See exactly what the agent is doing
✅ **Use good research questions**: Be specific about what you want to know
✅ **Limit scope to company website**: Better results when focused

### Example Seed URLs

For a company website, include:
- `/about` - Company overview
- `/team` - Leadership/decision makers
- `/portfolio` - Portfolio companies
- `/news` - Recent announcements
- `/private-investing` - Investment strategies

### Performance Expectations

| Metric | Typical Range |
|--------|--------------|
| **Execution Time** | 60-120 seconds |
| **Pages Scraped** | 10-15 pages |
| **Sub-Agents** | 6-8 (including refinements) |
| **Report Size** | 30-60 KB |

## Troubleshooting

### App Won't Start

```bash
# Reinstall Streamlit
pip install --upgrade streamlit

# Check for port conflicts
streamlit run app.py --server.port 8502
```

### Research Fails

1. **Check seed URLs**: Make sure URLs are accessible
2. **Check API quota**: Ensure OpenAI API has quota
3. **View debug info**: Expand the "Debug Information" section
4. **Check logs**: Verbose logging shows where it failed

### Slow Performance

- **Reduce seed URLs**: Start with 5-10 URLs max
- **Limit scope**: Focus on specific pages
- **Check network**: Slow fetching may indicate network issues

## Advanced Usage

### Custom Port

```bash
streamlit run app.py --server.port 8080
```

### Headless Mode (Server Deployment)

```bash
streamlit run app.py --server.headless true
```

### External Access

```bash
streamlit run app.py --server.address 0.0.0.0
```

## Architecture

```
User Interface (Streamlit)
    ↓
Research Workflow
    ├─ Planning Agent
    ├─ Supervisor + 6 Sub-Agents (Parallel)
    ├─ Refinement (MCP Search)
    └─ Writer Agent
    ↓
Reports (Markdown + JSON)
```

## Files

- `app.py` - Main Streamlit application
- `requirements-streamlit.txt` - Streamlit dependencies
- `README-STREAMLIT.md` - This file

## Support

For issues or questions:
1. Check verbose logs for error details
2. Review the command-line version: `python -m company_research.main --help`
3. Ensure all dependencies are installed
4. Check OpenAI API key is configured

## Version

**Current Version**: V2.8
**Features**:
- Multi-agent research system
- MCP intelligent search
- Iterative refinement
- Comprehensive verbose logging

---

**Enjoy researching! 🔍**
