import json
from jinja2 import Environment, FileSystemLoader

def generate_cv(json_path: str, template_path: str, output_html: str):
    # Load JSON Resume data
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_path)

    # Render HTML with data
    html_content = template.render(**data)

    # Save HTML to file
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Rendered CV HTML saved to {output_html}")

if __name__ == "__main__":
    generate_cv("../parsed_resume.json", "src/cv_template.html", "cv_rendered.html")
