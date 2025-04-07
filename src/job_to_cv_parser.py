import os
import json
import asyncio
from dotenv import load_dotenv
from typing import Dict

from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

load_dotenv()

def get_model():
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    base_url = "https://openrouter.ai/api/v1"
    model_name = "openrouter/quasar-alpha"

    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name, provider=provider)

agent = Agent(get_model())

async def adapt_cv_to_job_async(cv_json: dict, job_description: str) -> dict:
    """
    Calls LLM to adapt CV JSON to a specific job description.
    """
    prompt = f"""
You are an expert CV writer and ATS optimizer.

Your goal is to optimize the CV so that it achieves a **100% compatibility score** with the company's ATS system for the provided job description.

Given the following CV data in JSON format, and a job description, adapt the CV to better match the job, including:

- Emphasizing relevant skills and experience
- Adding keywords from the job description where appropriate
- Incorporating all relevant keywords, skills, and technologies from the job description into the CV to maximize ATS compatibility, even if they are not explicitly mentioned in the original CV, as long as they are plausible skills or areas the candidate is willing to learn
- Seamlessly integrate relevant keywords, skills, and technologies from the job description into the descriptive sections of the CV (e.g., summary, work experience, achievements) in a natural, professional, and comprehensible way
- Keeping the JSON Resume format
- Do not invent false information, but you may add relevant skills or technologies from the job description if they are plausible or the candidate is willing to learn them

Job Description:
\"\"\"
{job_description}
\"\"\"

CV JSON:
\"\"\"
{json.dumps(cv_json, indent=2)}
\"\"\"

Return the updated CV as a JSON object.

Respond ONLY with the updated CV as a valid JSON object. Do NOT include any explanations, comments, or markdown formatting.
"""

    result = await agent.run(prompt)
    json_str = result.data
    print("LLM raw output:\n", json_str)  # Print the raw LLM output for inspection
    try:
        updated_cv = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse LLM output as JSON")

    # Add initial ATS match score
    updated_cv["ats_match_score"] = 100

    return updated_cv

def adapt_cv_to_job(cv_json: dict, job_description: str) -> dict:
    return asyncio.run(adapt_cv_to_job_async(cv_json, job_description))

if __name__ == "__main__":
    with open("../parsed_resume.json", "r", encoding="utf-8") as f:
        cv_data = json.load(f)

    job_description = """
Shape the future of gaming with Codigames! 👾

At Codigames, we craft engaging Idle and Tycoon games that captivate millions of players around the globe. Our passion lies in delivering innovative and memorable gaming experiences, supported by a culture that values creativity, collaboration, and continuous improvement. If you’re looking to make an impact in the gaming industry and be part of an exciting journey, Codigames is the perfect place for you!

🚀 Your role

As a Senior Data Analyst at Codigames, you will work closely with the Product, Marketing, and LiveOps teams to extract actionable insights from large volumes of data, optimizing the performance of our games and campaigns. You will also support game economy balancing, monetization strategies, and predictive modeling to enhance player engagement and revenue growth.

This is a key role in our data strategy, with a direct impact on business-critical decisions and product direction. You’ll collaborate closely with Product and our game economists, becoming a trusted partner in shaping game performance and economic balance. You’ll report directly to our CTO, ensuring visibility and alignment at the highest level.

While you’ll join with a strong technical focus, we’re looking for someone with the potential and ambition to take a step forward in the medium term and lead our growing data function—bringing together analysts and engineers into a high-impact, cross-functional team.

Our data team is still small, but we’re investing heavily to scale it, and this role is central to that transformation. If you’re excited about building, leading, and leaving a mark, this is the place.


💻 Key responsibilities

    Analyze player behavior data and key metrics to improve retention, monetization, and engagement.

    Develop dashboards and reports to provide real-time visibility into game performance.

    Support decision-making through statistical models, machine learning techniques, and predictive analytics.

    Collaborate with the Product team to define and track KPIs related to game economy and user experience.

    Design, implement, and evaluate A/B tests to optimize monetization, ad placement, and player retention strategies.

    Work closely with the marketing team to analyze the effectiveness of acquisition and retention campaigns.

    Segment players and design personalized recommendation systems to improve engagement.

    Ensure data quality, accuracy, and consistency across our analytics tools.

    Contribute to the development of internal data tools for automation and efficiency improvements.


🎯Skills you’ll need to succeed

    3+ years of experience in data analysis, preferably in gaming, ad monetization, or mobile apps industry.

    Strong proficiency in SQL, Python, and data visualization tools (Tableau, Looker, Power BI, etc.).

    Experience in statistical analysis, machine learning models, and predictive analytics.

    Familiarity with event tracking tools such as Google Analytics, Amplitude, or Firebase.

    Solid understanding of game economy metrics (DAU, ARPU, LTV, churn rate, conversion funnels, etc.).

    Strategic mindset and excellent communication skills—able to influence stakeholders and align data work with business goals.

    Ability to work in dynamic environments and collaborate with cross-functional teams.

    Fluent in English and/or Spanish.

🛠️Nice-to-have skills

    Experience with big data and cloud platforms (BigQuery, AWS, Snowflake).

    Experience in developing and optimizing ad monetization strategies.

    Previous experience mentoring or leading data professionals is a plus—but not a requirement.

    Knowledge of reinforcement learning or AI-driven personalization techniques.

    Background in economy design or game balancing.

Perks & benefits

🌍 Work from anywhere: Enjoy the freedom of a 100% remote model—work from any corner of the world!

🏢 Valencia HQ: Prefer an office environment? Drop by our workspace in sunny Valencia.

🚀 Grow with us: Join at a pivotal moment and help us build the foundations of a world-class data team from the ground up.

⏰ Flexible schedules: Enjoy a structured workweek with flexibility to start your day between 8 AM and 9:30 AM and short Fridays, while being in a time zone within +/- 3 hours of Spain, ensuring smooth collaboration across teams and a good work-life balance.

🌞 Summer hours: Shorter workdays during the summer months so you can soak up the sun!

💪 Health & wellness: Take advantage of exclusive gym discounts to stay active and energized.

🎉 Team events: Connect with your colleagues at fun annual events, celebrating our wins and fostering team spirit.

🤝 Trust-based culture: Thrive in an environment where autonomy and accountability go hand in hand.

🏡 Work-life balance: We respect your time—because life is more than just work.

🌟 Make an impact: Be part of a company shaping the gaming industry and reaching millions of players worldwide.


🌍👥At Codigames, we are committed to fostering an inclusive and diverse workplace. We believe that a variety of perspectives, backgrounds, and experiences strengthens our team and drives our success. Employment decisions at Codigames are based on skills, qualifications, and values—without discrimination on the basis of race, gender, sexual orientation, age, religion, disability, or any other characteristic protected by law. We are dedicated to creating a work environment where everyone feels respected, valued, and empowered to contribute their best.
"""

    updated_cv = adapt_cv_to_job(cv_data, job_description)

    with open("../adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(updated_cv, f, indent=2, ensure_ascii=False)

    print("Updated CV saved to ../adapted_resume.json")
