import requests
from bs4 import BeautifulSoup, Comment
from pydantic_ai import Agent
from job_to_cv_parser import get_model


def get_filtered_content(url: str) -> str:
    """
    Downloads and filters the HTML content of a job posting page, removing menus, headers, footers, and other irrelevant parts.

    Args:
        url (str): The URL of the job posting.

    Returns:
        str: The filtered plain text content, or an error message.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove irrelevant tags
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form", "iframe"]):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Heuristic: find the main content block by keywords or size
        content = None
        main_tags = ["main", "article", "section", "div"]
        keywords = ["description", "job", "responsibilities", "details", "requirements"]

        for tag_name in main_tags:
            for tag in soup.find_all(tag_name):
                if any(
                    keyword in str(tag.get("class", "")).lower()
                    or keyword in str(tag.get("id", "")).lower()
                    or keyword in tag.get_text().lower()
                    for keyword in keywords
                ):
                    content = tag
                    break
                elif not content and tag.get_text(strip=True):
                    if len(tag.get_text().split()) > 50:
                        content = tag
            if content:
                break

        if not content:
            content = soup.body

        plain_text = content.get_text(separator="\n", strip=True)
        return plain_text

    except requests.RequestException as e:
        return f"Error extracting content: {str(e)}"


def extract_description_with_llm(plain_text: str, agent: Agent) -> str:
    """
    Uses an LLM agent to extract only the job description from the filtered plain text.

    Args:
        plain_text (str): The filtered plain text content.
        agent (Agent): The pydantic_ai Agent instance.

    Returns:
        str: The extracted job description.
    """
    prompt = f"""
Extract only the main job description from the following text. Ignore menus, footers, ads, or irrelevant content.

If this is not a job posting, respond with exactly: "ERROR: Not a job posting".

Return only the job description without any additional comments:

\"\"\"
{plain_text}
\"\"\"
"""
    import asyncio
    result = asyncio.run(agent.run(prompt))
    return result.data.strip()


def scrape_job_description(url: str, agent: Agent) -> str:
    """
    Extracts the job description from a job posting URL using HTML filtering and an LLM agent.

    Args:
        url (str): The URL of the job posting.
        agent (Agent): The pydantic_ai Agent instance.

    Returns:
        str: The extracted job description or an error message.
    """
    filtered_content = get_filtered_content(url)
    if filtered_content.startswith("Error"):
        return filtered_content

    description = extract_description_with_llm(filtered_content, agent)
    return description


if __name__ == "__main__":
    agent = Agent(get_model())

    url = input("Enter the job posting URL: ")
    description = scrape_job_description(url, agent)

    output_path = "job_description.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(description)

    print(f"\nJob description saved to {output_path}\n")
    print(description)
