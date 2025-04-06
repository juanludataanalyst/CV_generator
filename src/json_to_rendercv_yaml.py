import json
import yaml

def convert(json_path: str, yaml_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    basics = data.get("basics", {})
    location = basics.get("location") or {}

    cv = {
        "name": basics.get("name", ""),
        "email": basics.get("email", ""),
        "phone": basics.get("phone", ""),
        "location": location.get("address", ""),
        "website": basics.get("url", ""),
        "social_networks": [],
        "sections": {}
    }

    if basics.get("profiles"):
        for profile in basics["profiles"]:
            cv["social_networks"].append({
                "network": profile.get("network", ""),
                "username": profile.get("username", "")
            })

    # Summary section
    if basics.get("summary"):
        cv["sections"]["Summary"] = [basics.get("summary")]

    # Experience section
    experience_list = []
    for job in data.get("work", []):
        experience_list.append({
            "company": job.get("company", ""),
            "position": job.get("position", ""),
            "start_date": job.get("startDate", ""),
            "end_date": job.get("endDate", ""),
            "location": job.get("location", ""),
            "summary": job.get("summary", ""),
            "highlights": job.get("highlights", [])
        })
    if experience_list:
        cv["sections"]["Experience"] = experience_list

    # Education section
    education_list = []
    for edu in data.get("education", []):
        start = edu.get("startDate", "")
        end = edu.get("endDate", "Present")
        degree = edu.get("studyType", "")
        area = edu.get("area", "")
        education_list.append({
            "institution": edu.get("institution", ""),
            "area": area,
            "degree": degree,
            "start_date": start,
            "end_date": end,
            "date": f"{start} - {end}",
            "location": edu.get("location", ""),
            "summary": f"{degree} in {area}" if degree and area else degree or area,
            "highlights": []
        })
    if education_list:
        cv["sections"]["Education"] = education_list

    # Skills section as OneLineEntry
    skills_str = ", ".join(skill.get("name", "") for skill in data.get("skills", []))
    if skills_str:
        cv["sections"]["Skills"] = [{
            "label": "Skills",
            "details": skills_str
        }]

    # Projects section
    projects_list = []
    for project in data.get("projects", []):
        projects_list.append({
            "name": project.get("name", ""),
            "summary": project.get("description", ""),
            "url": project.get("url", "")
        })
    if projects_list:
        cv["sections"]["Projects"] = projects_list

    yaml_data = {
        "cv": cv,
        "design": {
            "theme": "classic",
            "page": {
                "size": "us-letter",
                "top_margin": "2cm",
                "bottom_margin": "2cm",
                "left_margin": "2cm",
                "right_margin": "2cm",
                "show_page_numbering": True,
                "show_last_updated_date": True
            }
        },
        "locale": {
            "language": "en"
        },
        "rendercv_settings": {
            "date": "2025-04-06",
            "bold_keywords": []
        }
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, allow_unicode=True, sort_keys=False)

    print(f"Converted {json_path} to {yaml_path}")

if __name__ == "__main__":
    convert("../parsed_resume.json", "cv_rendercv.yaml")
