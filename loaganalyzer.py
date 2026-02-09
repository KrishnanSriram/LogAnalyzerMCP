import re
import requests
from pathlib import Path

# ============================================================================
# CONFIGURATION: Specify which sections you want to extract
# ============================================================================
SECTIONS_TO_CAPTURE = [
    "prepare_executor",
    "prepare_script",
    "get_sources",
    "step_script",
    "tf_init",
    "tf_plan",
    "tf_scan",
    "after_script",
    "upload_artifacts_on_failure",
    "cleanup_file_variables",
    # Add more section names here as needed
]

# Set to True to capture ALL sections, False to use the list above
CAPTURE_ALL_SECTIONS = False

# Set to True to also extract final status after cleanup_file_variables
EXTRACT_FINAL_STATUS = True


# ============================================================================

def fetch_log_from_url(url):
    """
    Fetch log content from a URL.

    Args:
        url (str): URL to fetch the log from

    Returns:
        str: Log content
    """
    try:
        print(f"Fetching log from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        print(f"Successfully fetched {len(response.text)} characters")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching log: {e}")
        return None


def extract_sections(log_content, sections_to_capture=None, capture_all=False):
    """
    Extract specified sections from GitLab CI log between section_start and section_end markers.

    Args:
        log_content (str): The complete log content
        sections_to_capture (list): List of section names to extract, or None to extract all
        capture_all (bool): If True, extract all sections regardless of the list

    Returns:
        dict: Dictionary with section names as keys and section content as values
    """
    sections = {}

    # Find all section starts with their positions
    start_pattern = r'section_start:(\d+):([^\]\s\[]+)'
    end_pattern = r'section_end:(\d+):([^\]\s\[]+)'

    starts = {}
    ends = {}

    # Build dictionaries of section names to their positions
    for m in re.finditer(start_pattern, log_content):
        section_name = m.group(2)
        starts[section_name] = m.end()

    for m in re.finditer(end_pattern, log_content):
        section_name = m.group(2)
        ends[section_name] = m.start()

    print(f"\nDebug: Found {len(starts)} section starts")
    print(f"Debug: Found {len(ends)} section ends")

    # Show all section names found
    print("\nAll sections available in log:")
    all_sections = sorted(set(list(starts.keys()) + list(ends.keys())))
    for name in all_sections:
        has_start = "✓" if name in starts else "✗"
        has_end = "✓" if name in ends else "✗"
        will_capture = "📥" if (capture_all or (sections_to_capture and name in sections_to_capture)) else "⏭️"
        print(f"  {will_capture} {has_start} start | {has_end} end : {name}")

    # Determine which sections to extract
    sections_to_extract = set()
    if capture_all:
        sections_to_extract = set(starts.keys())
        print(f"\nCapturing ALL {len(sections_to_extract)} sections")
    elif sections_to_capture:
        sections_to_extract = set(sections_to_capture)
        print(f"\nCapturing {len(sections_to_extract)} specified sections")

        # Warn about sections that were requested but not found
        not_found = sections_to_extract - set(starts.keys())
        if not_found:
            print(f"\nWarning: These requested sections were not found in the log:")
            for name in not_found:
                print(f"  - {name}")
    else:
        print("\nNo sections specified and capture_all is False. Nothing to extract.")
        return sections

    # Extract content for sections that match our criteria
    extracted_count = 0
    for section_name in sections_to_extract:
        if section_name in starts and section_name in ends:
            start_pos = starts[section_name]
            end_pos = ends[section_name]

            # Extract content between start and end
            content = log_content[start_pos:end_pos]
            # Clean up ANSI escape codes
            content = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', content)
            content = re.sub(r'\[0K|\[0;m|\[[\d;]+m', '', content)
            sections[section_name] = content.strip()
            extracted_count += 1
        elif section_name in starts:
            print(f"\nWarning: Section '{section_name}' has start but no end - skipping")
        elif section_name in ends:
            print(f"\nWarning: Section '{section_name}' has end but no start - skipping")

    print(f"\nSuccessfully extracted {extracted_count} sections")
    return sections


def extract_final_status(log_content):
    """
    Extract the final status section after cleanup_file_variables to end of log.

    Args:
        log_content (str): The complete log content

    Returns:
        str: Final status content or None if not found
    """
    # Find the end of cleanup_file_variables section
    cleanup_end_pattern = r'section_end:\d+:cleanup_file_variables'
    match = re.search(cleanup_end_pattern, log_content)

    if match:
        # Extract everything from the end of cleanup_file_variables to the end
        start_pos = match.end()
        final_content = log_content[start_pos:]

        # Clean up ANSI escape codes
        final_content = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', final_content)
        final_content = re.sub(r'\[0K|\[0;m|\[[\d;]+m', '', final_content)

        print(f"\nFound final status section ({len(final_content)} characters)")
        return final_content.strip()
    else:
        print("\nWarning: Could not find end of cleanup_file_variables section")
        return None


def save_sections_to_files(sections, output_dir='log_sections'):
    """
    Save each section to a separate text file.

    Args:
        sections (dict): Dictionary of section names and content
        output_dir (str): Directory to save the files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for section_name, content in sections.items():
        # Create safe filename
        safe_filename = re.sub(r'[^\w\-_]', '_', section_name)
        file_path = output_path / f"{safe_filename}.txt"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Saved: {file_path} ({len(content)} characters)")


def save_final_status(final_status, output_dir='log_sections'):
    """
    Save the final status section to a file.

    Args:
        final_status (str): Final status content
        output_dir (str): Directory to save the file
    """
    if final_status:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        file_path = output_path / "final_status.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_status)

        print(f"Saved final status: {file_path} ({len(final_status)} characters)")


def save_full_log(log_content, filename='full_log.txt'):
    """Save the full log for inspection."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(log_content)
    print(f"Full log saved to: {filename}")


# Main execution
if __name__ == "__main__":
    # URL of the log file
    log_url = "https://gist.githubusercontent.com/KrishnanSriram/501648189605ac2c522a73a0be25c222/raw/2665015c92d603a46dd90664b033ed8b6ac38417/build%20logs"

    # Fetch the log content from URL
    log_content = fetch_log_from_url(log_url)

    if log_content:
        # Save full log for inspection
        save_full_log(log_content)

        # Extract sections based on configuration
        sections = extract_sections(
            log_content,
            sections_to_capture=SECTIONS_TO_CAPTURE if not CAPTURE_ALL_SECTIONS else None,
            capture_all=CAPTURE_ALL_SECTIONS
        )

        # Extract final status if configured
        final_status = None
        if EXTRACT_FINAL_STATUS:
            final_status = extract_final_status(log_content)

        print(f"\n{'=' * 60}")

        if sections:
            # Save to files
            print("Saving sections to files...")
            save_sections_to_files(sections)

            # Save final status
            if final_status:
                save_final_status(final_status)

            print(f"\n✅ All requested sections saved to 'log_sections/' directory")
            if final_status:
                print("✅ Final status section saved as 'final_status.txt'")
        else:
            print("\n⚠️  No sections were extracted.")
    else:
        print("❌ Failed to fetch log content. Exiting.")
