from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def generate_ats_pdf(json_cv: dict, output_path: str) -> None:
    """
    Generates an ATS-friendly PDF CV from JSON Resume data.

    Args:
        json_cv (dict): JSON Resume structured data.
        output_path (str): Path to save the generated PDF.
    """
    try:
        c = canvas.Canvas(output_path, pagesize=LETTER)
        c.setFont("Helvetica", 12)
        width, height = LETTER
        y = height - 50

        # Basics section
        basics = json_cv.get("basics", {})
        name = basics.get("name", "")
        email = basics.get("email", "")
        phone = basics.get("phone", "")
        c.drawString(50, y, f"{name}")
        y -= 20
        c.drawString(50, y, f"Email: {email}")
        y -= 20
        c.drawString(50, y, f"Phone: {phone}")
        y -= 30

        # Work experience
        c.drawString(50, y, "Work Experience:")
        y -= 20
        for job in json_cv.get("work", []):
            position = job.get("position", "")
            company = job.get("company", "")
            start_date = job.get("startDate", "")
            end_date = job.get("endDate", "")
            summary = job.get("summary", "")
            c.drawString(60, y, f"{position} at {company} ({start_date} - {end_date})")
            y -= 15
            c.drawString(70, y, summary)
            y -= 25

        # Education
        c.drawString(50, y, "Education:")
        y -= 20
        for edu in json_cv.get("education", []):
            institution = edu.get("institution", "")
            study_type = edu.get("studyType", "")
            start_date = edu.get("startDate", "")
            end_date = edu.get("endDate", "")
            c.drawString(60, y, f"{study_type} at {institution} ({start_date} - {end_date})")
            y -= 20

        # Skills
        c.drawString(50, y, "Skills:")
        y -= 20
        for skill in json_cv.get("skills", []):
            name = skill.get("name", "")
            c.drawString(60, y, f"- {name}")
            y -= 15

        c.save()
    except Exception as e:
        # Reason: PDF generation might fail due to invalid data or file issues
        print(f"Error generating ATS PDF: {e}")
