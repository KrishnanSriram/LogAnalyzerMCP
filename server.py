"""
FastMCP Server for GitLab Log Analysis
Uses LangChain for LLM abstraction - supports Ollama, OpenAI, Azure OpenAI, AWS Bedrock, etc.
"""

from fastmcp import FastMCP
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from starlette.responses import JSONResponse

# You can easily swap to other providers:
# from langchain_openai import ChatOpenAI
# from langchain_openai import AzureChatOpenAI
# from langchain_aws import ChatBedrock
# from langchain_anthropic import ChatAnthropic

# Initialize FastMCP server
mcp = FastMCP("GitLab Log Analyzer")


# =============================================================================
# LLM CONFIGURATION - Change this to switch providers
# =============================================================================

def get_llm() -> BaseChatModel:
    """
    Get the configured LLM.
    Change this function to switch between different providers.
    """

    # OPTION 1: Ollama (Local, Free)
    return ChatOllama(
        model="llama3.2",
        base_url="http://localhost:11434",
        temperature=0.1,
    )

    # OPTION 2: OpenAI
    # return ChatOpenAI(
    #     model="gpt-4o-mini",
    #     temperature=0.1,
    #     api_key="your-api-key"
    # )

    # OPTION 3: Azure OpenAI
    # return AzureChatOpenAI(
    #     azure_endpoint="https://your-resource.openai.azure.com/",
    #     api_key="your-api-key",
    #     api_version="2024-02-01",
    #     deployment_name="gpt-4o",
    #     temperature=0.1,
    # )

    # OPTION 4: AWS Bedrock
    # return ChatBedrock(
    #     model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    #     region_name="us-east-1",
    #     temperature=0.1,
    # )

    # OPTION 5: Anthropic Direct
    # return ChatAnthropic(
    #     model="claude-3-5-sonnet-20241022",
    #     api_key="your-api-key",
    #     temperature=0.1,
    # )


# =============================================================================

async def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Call the configured LLM with optional system prompt.

    Args:
        prompt: The user prompt/question
        system_prompt: Optional system prompt for context

    Returns:
        str: LLM response
    """
    llm = get_llm()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    # Use invoke for sync-like call (LangChain handles async internally)
    response = await llm.ainvoke(messages)

    return response.content

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

@mcp.tool()
async def analyze_terraform_init(log_content: str) -> str:
    """
    Analyze terraform init section for initialization issues, provider downloads, and module setup.

    Args:
        log_content: The terraform init log section content

    Returns:
        Analysis of the terraform init process
    """
    system_prompt = """You are an expert DevOps engineer analyzing Terraform initialization logs.
Focus on:
- Provider and module downloads
- Version compatibility issues
- Backend configuration
- Plugin initialization
- Any errors or warnings
Provide a concise, actionable analysis."""

    prompt = f"""Analyze this Terraform init log section and provide insights:

{log_content}

Provide:
1. Status (Success/Failed/Warning)
2. Key findings
3. Any issues or concerns
4. Recommendations (if any)"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def analyze_terraform_plan(log_content: str) -> str:
    """
    Analyze terraform plan section for resource changes, potential issues, and warnings.

    Args:
        log_content: The terraform plan log section content

    Returns:
        Analysis of the terraform plan output
    """
    system_prompt = """You are an expert DevOps engineer analyzing Terraform plan outputs.
Focus on:
- Resources to be created, modified, or destroyed
- Potential breaking changes
- Resource dependencies
- Configuration issues
Provide a concise, actionable analysis."""

    prompt = f"""Analyze this Terraform plan log section:

{log_content}

Provide:
1. Summary of changes (create/update/delete counts)
2. High-risk changes (if any)
3. Potential issues or warnings
4. Recommendations"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def analyze_terraform_scan(log_content: str) -> str:
    """
    Analyze IaC security scan results from Checkov/Bridgecrew for compliance issues.

    Args:
        log_content: The terraform scan log section content

    Returns:
        Analysis of security scan results
    """
    system_prompt = """You are a security expert analyzing IaC security scan results.
Focus on:
- Failed security checks
- Severity levels (HIGH, MEDIUM, LOW)
- Compliance violations
- Security best practices
Provide a concise, actionable analysis."""

    prompt = f"""Analyze this IaC security scan result:

{log_content}

Provide:
1. Overall security status
2. Critical issues (HIGH severity)
3. Summary of failed checks
4. Remediation recommendations"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def analyze_job_failure(log_content: str) -> str:
    """
    Analyze final status section to determine root cause of job failure.

    Args:
        log_content: The final status log section content

    Returns:
        Root cause analysis of the job failure
    """
    system_prompt = """You are an expert DevOps engineer analyzing CI/CD job failures.
Focus on:
- Root cause identification
- Error messages and codes
- Failed steps
- Environmental issues
Provide a concise, actionable analysis."""

    prompt = f"""Analyze this job failure log:

{log_content}

Provide:
1. Root cause of failure
2. Failed step/stage
3. Error details
4. Recommended fix"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def extract_errors(log_content: str) -> str:
    """
    Extract and categorize all errors from a log section.

    Args:
        log_content: The log section content to analyze for errors

    Returns:
        Categorized list of errors with severity assessment
    """
    system_prompt = """You are an expert at parsing and categorizing log errors.
Extract all errors and categorize them by type and severity."""

    prompt = f"""Extract and categorize all errors from this log:

{log_content}

Provide:
1. List of all errors found
2. Error categories (syntax, permission, configuration, etc.)
3. Severity assessment
4. Line numbers or context (if identifiable)"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def summarize_pipeline(
        tf_init: Optional[str] = None,
        tf_plan: Optional[str] = None,
        tf_scan: Optional[str] = None,
        final_status: Optional[str] = None,
        other_sections: Optional[str] = None
) -> str:
    """
    Generate a comprehensive summary of the entire pipeline execution.

    Args:
        tf_init: Terraform init section content
        tf_plan: Terraform plan section content
        tf_scan: Terraform scan section content
        final_status: Final status section content
        other_sections: Any other relevant sections concatenated

    Returns:
        Comprehensive pipeline summary
    """
    system_prompt = """You are an expert DevOps engineer providing pipeline execution summaries.
Provide a high-level overview focusing on the most important information."""

    sections = []
    if tf_init:
        sections.append(f"=== Terraform Init ===\n{tf_init[:500]}...")
    if tf_plan:
        sections.append(f"=== Terraform Plan ===\n{tf_plan[:500]}...")
    if tf_scan:
        sections.append(f"=== Security Scan ===\n{tf_scan[:500]}...")
    if final_status:
        sections.append(f"=== Final Status ===\n{final_status[:500]}...")
    if other_sections:
        sections.append(f"=== Other Sections ===\n{other_sections[:500]}...")

    sections_text = "\n\n".join(sections)

    prompt = f"""Provide a comprehensive summary of this GitLab pipeline execution:

{sections_text}

Provide:
1. Overall status
2. Key stages and their outcomes
3. Main issues encountered
4. Recommendations"""

    analysis = await call_llm(prompt, system_prompt)
    return analysis


@mcp.tool()
async def get_recommendations(analysis_results: str) -> str:
    """
    Generate actionable recommendations based on analysis results.

    Args:
        analysis_results: Combined analysis results from other tools

    Returns:
        Prioritized list of recommendations
    """
    system_prompt = """You are an expert DevOps consultant providing actionable recommendations.
Focus on practical, prioritized steps to resolve issues."""

    prompt = f"""Based on these analysis results, provide actionable recommendations:

{analysis_results}

Provide:
1. Top 3 priority actions
2. Quick wins (easy fixes)
3. Long-term improvements
4. Risk mitigation steps"""

    recommendations = await call_llm(prompt, system_prompt)
    return recommendations

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    # Run the FastMCP server
    mcp.run()