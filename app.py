"""Streamlit web interface for Company Research Agent V2.8."""

import streamlit as st
import json
import time
import sys
import io
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from urllib.parse import urlparse

from company_research.schema import ResearchBrief, ResearchState
from company_research.agents.graph import build_graph
from company_research.storage import save_state
from company_research import logger
from company_research.logger import format_size


# Page configuration
st.set_page_config(
    page_title="Company Research Agent V2.8",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'research_complete' not in st.session_state:
    st.session_state.research_complete = False
    st.session_state.report_md = None
    st.session_state.report_json = None
    st.session_state.company_name = None
    st.session_state.elapsed_time = None
    st.session_state.final_state = None


class StreamlitLogger:
    """Capture print output and stream to Streamlit container."""

    def __init__(self, container):
        self.container = container
        self.log_buffer = []
        self.last_update = time.time()
        self.update_interval = 0.1  # Update every 100ms

    def write(self, text):
        if text.strip():
            self.log_buffer.append(text.rstrip())

            # Throttle updates to avoid overwhelming Streamlit
            now = time.time()
            if now - self.last_update > self.update_interval:
                self.flush()
                self.last_update = now

    def flush(self):
        if self.log_buffer:
            # Join all logs and display
            full_log = '\n'.join(self.log_buffer)
            self.container.code(full_log, language='')


def validate_urls(urls_text):
    """Validate and parse URLs from text input."""
    if not urls_text.strip():
        return None, "Please provide at least one seed URL"

    urls = [url.strip() for url in urls_text.strip().split('\n') if url.strip()]

    if not urls:
        return None, "Please provide at least one valid URL"

    # Basic URL validation
    for url in urls:
        if not url.startswith('http://') and not url.startswith('https://'):
            return None, f"Invalid URL (must start with http:// or https://): {url}"

    return urls, None


def run_research(company_name, research_question, seed_urls, verbose=True):
    """Execute the research workflow."""

    # Extract allowed domains
    allowed_domains = sorted(set(urlparse(u).netloc for u in seed_urls))

    # Create research brief
    brief = ResearchBrief(
        company_name=company_name,
        main_question=research_question.strip(),
        sub_questions=[],  # Filled by planning_node
        seed_urls=seed_urls,
        allowed_domains=allowed_domains,
        constraints=[
            "Only use content from the scoped URLs and their domains.",
            "Use citations for every factual statement.",
        ],
    )

    # Set verbose mode
    logger.set_verbose(verbose)

    # Create state and graph
    state = ResearchState(brief=brief)
    app = build_graph()

    # Execute workflow
    start_time = time.time()
    final_state = app.invoke({"state": state})
    elapsed = time.time() - start_time

    # Extract results
    research_state = final_state["state"]
    save_state(research_state)

    return research_state, elapsed


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.title("🔍 Company Private Investing Research Agent")
st.caption("V2.8 - Powered by Multi-Agent System with MCP Intelligent Search")

st.markdown("---")

# Check if results exist
if st.session_state.research_complete:
    # Show results
    st.success("✅ Research Complete!")

    # Statistics
    st.subheader("📊 Research Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Time", f"{st.session_state.elapsed_time:.1f}s")
    with col2:
        st.metric("Pages Scraped", len(st.session_state.final_state.pages))
    with col3:
        st.metric("Sub-Agents", len(st.session_state.final_state.sub_agent_results))
    with col4:
        if st.session_state.report_md:
            st.metric("Report Size", format_size(len(st.session_state.report_md)))
        else:
            st.metric("Report Size", "N/A")

    st.markdown("---")

    # Markdown Report
    st.subheader("📄 Markdown Report")
    if st.session_state.report_md:
        st.markdown(st.session_state.report_md, unsafe_allow_html=False)
    else:
        st.warning("No markdown report generated")

    st.markdown("---")

    # Download buttons
    st.subheader("⬇ Download Reports")
    col1, col2 = st.columns(2)

    safe_company_name = st.session_state.company_name.lower().replace(' ', '_')

    with col1:
        if st.session_state.report_md:
            st.download_button(
                label="📥 Download Markdown Report",
                data=st.session_state.report_md,
                file_name=f"{safe_company_name}_private_investing_report.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.button("📥 Download Markdown Report", disabled=True, use_container_width=True)

    with col2:
        if st.session_state.report_json:
            st.download_button(
                label="📥 Download JSON Report",
                data=json.dumps(st.session_state.report_json, indent=2),
                file_name=f"{safe_company_name}_private_investing_report.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.button("📥 Download JSON Report", disabled=True, use_container_width=True)

    # JSON Data Expander
    if st.session_state.report_json:
        with st.expander("🔍 View Structured JSON Data"):
            st.json(st.session_state.report_json)

    st.markdown("---")

    # Run new research button
    if st.button("🔄 Run New Research", type="primary", use_container_width=True):
        st.session_state.research_complete = False
        st.rerun()

else:
    # Input interface
    st.subheader("📝 Configure Research")

    # Tabs for input methods
    tab1, tab2 = st.tabs(["✍ Manual Input", "📁 Upload Config"])

    # ========================================================================
    # TAB 1: MANUAL INPUT
    # ========================================================================
    with tab1:
        with st.form("manual_input_form"):
            company_name = st.text_input(
                "Company Name",
                value="Wellington Management",
                help="Name of the company to research"
            )

            research_question = st.text_area(
                "Research Question",
                value="Analyze Wellington Management's private markets and investing activities, including strategies, portfolio, team, and recent news.",
                height=100,
                help="What do you want to research about this company?"
            )

            seed_urls_text = st.text_area(
                "Seed URLs (one per line)",
                value="""https://www.wellington.com/en/capabilities/private-investing
https://www.wellington.com/en/capabilities/private-investing/our-team
https://www.wellington.com/en/capabilities/private-investing/early-stage-venture
https://www.wellington.com/en/capabilities/private-investing/climate-growth
https://www.wellington.com/en/capabilities/private-investing/late-stage-biotechnology#accordion-e6d946989a-item-d2db1cee14
https://www.wellington.com/en/capabilities/private-investing/late-stage-biotechnology/case-study
https://www.wellington.com/en/capabilities/private-investing/late-stage-growth
https://www.wellington.com/en/capabilities/private-investing/late-stage-growth/case-study
https://www.wellington.com/en/capabilities/private-investing/private-credit
https://www.wellington.com/en/capabilities/private-investing/value-creation""",
                height=200,
                help="Provide seed URLs - research will be limited to these URLs and their domains"
            )

            verbose = st.checkbox(
                "Enable verbose logging",
                value=True,
                help="Show detailed progress logs during research"
            )

            submitted = st.form_submit_button("▶ Start Research", type="primary", use_container_width=True)

            if submitted:
                # Validate inputs
                if not company_name.strip():
                    st.error("❌ Please provide a company name")
                elif not research_question.strip():
                    st.error("❌ Please provide a research question")
                else:
                    # Validate URLs
                    urls, error = validate_urls(seed_urls_text)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        # Run research
                        st.info(f"🚀 Starting research for {company_name}...")
                        st.info(f"📊 Analyzing {len(urls)} seed URLs")

                        # Create log container
                        log_container = st.empty()

                        try:
                            # Capture stdout
                            log_writer = StreamlitLogger(log_container)

                            with redirect_stdout(log_writer), redirect_stderr(log_writer):
                                research_state, elapsed = run_research(
                                    company_name=company_name,
                                    research_question=research_question,
                                    seed_urls=urls,
                                    verbose=verbose
                                )

                            # Flush final logs
                            log_writer.flush()

                            # Store results
                            st.session_state.research_complete = True
                            st.session_state.report_md = research_state.report_markdown
                            st.session_state.report_json = research_state.report_json
                            st.session_state.company_name = company_name
                            st.session_state.elapsed_time = elapsed
                            st.session_state.final_state = research_state

                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Research failed: {str(e)}")
                            with st.expander("🐛 Debug Information"):
                                st.exception(e)

    # ========================================================================
    # TAB 2: CONFIG FILE UPLOAD
    # ========================================================================
    with tab2:
        uploaded_file = st.file_uploader(
            "Upload config.json",
            type=['json'],
            help="Upload a JSON configuration file (same format as config.json)"
        )

        if uploaded_file:
            try:
                config = json.load(uploaded_file)

                # Preview
                st.success("✅ Config file loaded successfully")

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Company:** {config.get('company_name', 'N/A')}")
                with col2:
                    st.info(f"**Seed URLs:** {len(config.get('seed_urls', []))}")

                # Show config preview
                with st.expander("👀 View Full Configuration"):
                    st.json(config)

                verbose_upload = st.checkbox(
                    "Enable verbose logging",
                    value=True,
                    help="Show detailed progress logs during research",
                    key="verbose_upload"
                )

                if st.button("▶ Start Research from Config", type="primary", use_container_width=True):
                    # Validate config
                    if 'company_name' not in config or 'seed_urls' not in config:
                        st.error("❌ Invalid config file: missing 'company_name' or 'seed_urls'")
                    else:
                        company_name = config['company_name']
                        research_question = config.get('request', "Analyze private markets and investing activities")
                        seed_urls = config['seed_urls']

                        # Run research
                        st.info(f"🚀 Starting research for {company_name}...")
                        st.info(f"📊 Analyzing {len(seed_urls)} seed URLs")

                        # Create log container
                        log_container = st.empty()

                        try:
                            # Capture stdout
                            log_writer = StreamlitLogger(log_container)

                            with redirect_stdout(log_writer), redirect_stderr(log_writer):
                                research_state, elapsed = run_research(
                                    company_name=company_name,
                                    research_question=research_question,
                                    seed_urls=seed_urls,
                                    verbose=verbose_upload
                                )

                            # Flush final logs
                            log_writer.flush()

                            # Store results
                            st.session_state.research_complete = True
                            st.session_state.report_md = research_state.report_markdown
                            st.session_state.report_json = research_state.report_json
                            st.session_state.company_name = company_name
                            st.session_state.elapsed_time = elapsed
                            st.session_state.final_state = research_state

                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Research failed: {str(e)}")
                            with st.expander("🐛 Debug Information"):
                                st.exception(e)

            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON file: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error loading config: {str(e)}")

        else:
            st.info("👆 Upload a config.json file to get started")
            st.markdown("""
            **Example config.json format:**
            ```json
            {
              "company_name": "Wellington Management",
              "request": "Analyze private markets activities",
              "seed_urls": [
                "https://www.wellington.com/en/capabilities/private-investing",
                "https://www.wellington.com/en/capabilities/private-investing/our-team"
              ]
            }
            ```
            """)

# Footer
st.markdown("---")
st.caption("Company Private Investing Research Agent V2.8 | Multi-Agent System with MCP Intelligent Search")
