# Company Private Investing Research Agent

A local Python deep-research agent that scrapes and analyzes company private investing information using a 3-phase LangGraph architecture.

## Features

- **Scoped Web Scraping**: Only analyzes user-provided URLs (no external web search)
- **3-Phase Architecture**: Scope → Research → Write
- **Professional Reports**: Generates markdown reports with citations
- **Company-Agnostic**: Reusable for any private investing firm
- **LangGraph Powered**: Uses LangChain and LangGraph for multi-agent orchestration

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key in `.env`:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Create a configuration file (see `config.example.json` for Wellington Management example)

2. Run the research agent:
```bash
python -m company_research.main config.example.json
```

3. Find the generated report in `artifacts/[company_name]_private_investing_report.md`

## Configuration Format

```json
{
  "company_name": "Wellington Management",
  "request": "Research brief describing what you want to analyze...",
  "seed_urls": [
    "https://www.example.com/page1",
    "https://www.example.com/page2"
  ]
}
```

## Architecture

### Phase 1: Scope (Planning)
- Clarifies the research request
- Generates focused research brief
- Creates sub-questions for investigation

### Phase 2: Research
- Fetches all seed URLs
- Analyzes content for each sub-question
- Generates research notes with citations

### Phase 3: Write
- Compiles all research notes
- Generates professional markdown report
- Includes proper citations and sources

## Output

The system generates:
- **Report**: `artifacts/[company]_private_investing_report.md`
- **Scraped Pages**: `artifacts/pages/*.json`
- **Research State**: `artifacts/state.json`

## Report Sections

1. Executive Summary
2. Private Investing Overview
3. Key Decision Makers
4. Regions and Sectors
5. Assets Under Management
6. Portfolio Companies (with tables)
7. Strategies / Funds / Programs
8. Recent News & Announcements (with tables)
9. Conclusion
10. Sources (with citation mapping)

## Constraints

- Only uses information from provided seed URLs and their domains
- No external knowledge or web search
- All claims must have citations
- Missing information is explicitly stated as "not disclosed"

## Example

Run the Wellington Management example:
```bash
python -m company_research.main config.example.json
```

View the generated report:
```bash
cat artifacts/wellington_management_private_investing_report.md
```

## Customization

To research a different company:
1. Copy `config.example.json` to a new file
2. Update `company_name`, `request`, and `seed_urls`
3. Run with your new config file

## Project Structure

```
company_research/
  __init__.py
  config.py          # LLM configuration
  schema.py          # Pydantic models
  scraping.py        # Web scraping with domain validation
  storage.py         # File I/O helpers
  main.py            # CLI entry point
  agents/
    __init__.py
    planner.py       # Scope phase
    researcher.py    # Research phase
    writer.py        # Write phase
    graph.py         # LangGraph workflow
```

## Requirements

- Python 3.12+
- OpenAI API key
- Internet connection for scraping

## License

See guide for full implementation details.
