import json
import yaml

def convert(json_path: str, yaml_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    basics = data.get("basics", {})
    location = basics.get("location") or {}

    cv = {
        "name": basics.get("name", "") or "",
        "email": basics.get("email", "") or "",
        "phone": basics.get("phone", "") or "",
        "location": location.get("address", "") or "",
        "website": basics.get("url", "") or None,
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
        end_date = job.get("endDate", "").strip()
        if not end_date:
            end_date = "present"
        experience_list.append({
            "company": job.get("company", ""),
            "position": job.get("position", ""),
            "start_date": job.get("startDate", ""),
            "end_date": end_date,
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
        institution = edu.get("institution", "")

        # Map degree to abbreviation (max ~5 chars)
        degree_lower = degree.lower()
        if "bachelor" in degree_lower:
            degree_short = "BSc"
        elif "postgraduate" in degree_lower:
            degree_short = "PG"
        elif "master" in degree_lower:
            degree_short = "MSc"
        elif "doctor" in degree_lower or "phd" in degree_lower:
            degree_short = "PhD"
        elif "associate" in degree_lower:
            degree_short = "Assoc"
        else:
            degree_short = degree[:5]

        education_list.append({
            "institution": institution,
            "area": area,
            "degree": degree_short,
            "start_date": start,
            "end_date": end,
            "date": f"{start} - {end}",
            "location": edu.get("location", ""),
            "summary": "",
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
            },
            "section_titles": {
                "vertical_space_above": "1cm",
                "vertical_space_below": "0.7cm"
            },
            "entries": {
                "vertical_space_between_entries": "2.5em"
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
