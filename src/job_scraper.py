import requests
from bs4 import BeautifulSoup, Comment
from pydantic_ai import Agent


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

        # Heuristic: find the main content block by keywords
        candidates = []
        keywords = ["description", "job", "responsibilities", "details", "requirements", "posting", "vacancy", "position", "role", "summary", "body", "content"]

        for tag in soup.find_all(["main", "article", "section", "div"]):
            text = tag.get_text(separator=" ", strip=True)
            if not text or len(text.split()) < 30:
                continue
            score = 0
            attrs = (tag.get("class", []) or []) + [tag.get("id", "")]
            attrs_text = " ".join(attrs).lower()
            if any(k in attrs_text for k in keywords):
                score += 2
            if any(k in text.lower() for k in keywords):
                score += 1
            candidates.append((score, len(text), tag))

        # Sort by score and length
        candidates.sort(reverse=True)

        if candidates:
            content = candidates[0][2]
        else:
            content = soup.body

        plain_text = content.get_text(separator="\n", strip=True)
        return plain_text

    except requests.RequestException as e:
        return f"Error extracting content: {str(e)}"


def extract_description_with_llm(plain_text: str, agent: Agent) -> str:
    """
    Uses an LLM agent to extract only the job description from the filtered plain text.
    """
    prompt = f"""
Extract only the main job description from the following text. Ignore menus, footers, ads, or irrelevant content.

If this is not a job posting, respond with exactly: "ERROR: Not a job posting".

Return only the job description without any additional comments:

\"\"\"
{plain_text}
\"\"\"
"""
    from pipeline import run_llm
    result = run_llm(agent, prompt)
    print("LLM response (job_scraper):")
    print(result.data)
    return result.data.strip()


def scrape_job_description(url: str, agent: Agent, log_callback=None) -> str:
    """
    Extracts the job description from a job posting URL using HTML filtering and an LLM agent.
    """
    filtered_content = get_filtered_content(url)

    print(f"[DEBUG] Filtered content length: {len(filtered_content)}")
    print(f"[DEBUG] Filtered content starts with: {filtered_content[:100]}")

    if filtered_content.startswith("Error"):
        return filtered_content

    try:
        with open("job_description.txt", "w", encoding="utf-8") as f:
            f.write(filtered_content)
        print("Saved job_description.txt successfully.")
    except Exception as e:
        print(f"Error saving job_description.txt: {e}")

    print("Filtered content preview:")
    print(filtered_content[:1000])  # primeros 1000 caracteres

    description = extract_description_with_llm(filtered_content, agent)
    return description
