from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors


def generate_ats_pdf(json_cv: dict, output_path: str) -> None:
    """
    Generates an ATS-friendly PDF CV from JSON Resume data using ReportLab.
    """
    doc = SimpleDocTemplate(output_path, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading1'], fontSize=14, textColor=colors.black, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubSectionHeader', parent=styles['Normal'], fontSize=12, textColor=colors.black, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BulletPoint', parent=styles['Normal'], leftIndent=20, bulletFontName='Helvetica', bulletFontSize=12))
    styles.add(ParagraphStyle(name='ContactInfo', parent=styles['Normal'], alignment=10))

    # Helper function to add a section header
    def add_section_header(title):
        story.append(Paragraph(title, styles['SectionHeader']))
        story.append(Spacer(1, 0.2 * inch))

    # Helper function to add a bullet point
    def add_bullet_point(text):
        story.append(Paragraph(text, styles['BulletPoint']))

    # Basics section
    basics = json_cv.get("basics", {})
    if basics:
        story.append(Paragraph(basics.get("name", "No Name"), styles['Heading1']))
        story.append(Paragraph(f"{basics.get('label', 'No Title')}", styles['Normal']))
        story.append(Spacer(1, 0.1 * inch))

        contact_info = f"{basics.get('email', 'No Email')} | {basics.get('phone', 'No Phone')}"
        story.append(Paragraph(contact_info, styles['ContactInfo']))
        if basics.get("profiles"):
            for profile in basics["profiles"]:
                story.append(Paragraph(f"{profile.get('network', '')}: {profile.get('url', '')}", styles['ContactInfo']))
    story.append(Spacer(1, 0.2 * inch))

    # Summary/Profile section
    if basics.get("summary"):
        add_section_header("Summary")
        story.append(Paragraph(basics["summary"], styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

    # Work experience section
    if json_cv.get("work"):
        add_section_header("Work Experience")
        for job in json_cv["work"]:
            story.append(Paragraph(f"{job.get('position', 'No Position')}, {job.get('company', 'No Company')}", styles['SubSectionHeader']))
            story.append(Paragraph(f"{job.get('startDate', 'No Start Date')} - {job.get('endDate', 'Present')}", styles['Normal']))
            story.append(Paragraph(job.get("summary", "No Summary"), styles['Normal']))
            if job.get("highlights"):
                for highlight in job["highlights"]:
                    add_bullet_point(highlight)
            story.append(Spacer(1, 0.2 * inch))

    # Education section
    if json_cv.get("education"):
        add_section_header("Education")
        for edu in json_cv["education"]:
            story.append(Paragraph(f"{edu.get('studyType', 'No Degree')}, {edu.get('institution', 'No Institution')}", styles['SubSectionHeader']))
            story.append(Paragraph(f"{edu.get('startDate', 'No Start Date')} - {edu.get('endDate', 'Present')}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

    # Skills section
    if json_cv.get("skills"):
        add_section_header("Skills")
        for skill in json_cv["skills"]:
            add_bullet_point(skill.get("name", "No Skill Name"))
        story.append(Spacer(1, 0.2 * inch))

    # Languages section
    if json_cv.get("languages"):
        add_section_header("Languages")
        for lang in json_cv["languages"]:
            story.append(Paragraph(f"{lang.get('language', 'No Language')}, {lang.get('fluency', 'No Fluency')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

    # Projects section
    if json_cv.get("projects"):
        add_section_header("Projects")
        for project in json_cv["projects"]:
            story.append(Paragraph(project.get("name", "No Project Name"), styles['SubSectionHeader']))
            story.append(Paragraph(project.get("description", "No Description"), styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
