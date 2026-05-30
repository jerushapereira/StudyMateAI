import json
import re
from dataclasses import dataclass
from typing import Any

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError


class RoadmapServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class GroqCareerService:
    api_key: str
    model: str = "llama-3.3-70b-versatile"
    mock_when_no_key: bool = True

    def __post_init__(self):
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def generate_roadmap(self, profile: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            if self.mock_when_no_key:
                return self._mock_roadmap(profile)
            raise RoadmapServiceError("Groq API key is not configured.", 503)

        prompt = f"""
Create a personalized AI career roadmap for this student profile.

Profile:
- Name: {profile.get("name") or "Student"}
- Current skills: {profile.get("skills")}
- Experience level: {profile.get("experienceLevel")}
- Target role: {profile.get("targetRole")}

Return only valid JSON with this exact shape:
{{
  "profileSummary": "short personalized summary",
  "targetRole": "role",
  "estimatedTimeline": "timeline",
  "roadmap": [
    {{
      "id": "phase-1",
      "title": "phase title",
      "duration": "weeks or months",
      "goal": "phase goal",
      "topics": ["topic 1", "topic 2"],
      "resources": ["resource type or source idea"],
      "milestone": "checkpoint outcome",
      "projects": [
        {{
          "name": "project name",
          "description": "brief description",
          "techStack": ["tool 1", "tool 2"],
          "difficulty": "Beginner | Intermediate | Advanced"
        }}
      ]
    }}
  ],
  "skillGaps": [
    {{
      "skill": "missing skill",
      "priority": "Must-learn | Optional",
      "reason": "why it matters",
      "suggestedAction": "what to do next"
    }}
  ],
  "weeklyPlan": [
    {{
      "week": "Week 1",
      "focus": "main focus",
      "tasks": ["task 1", "task 2"],
      "deliverable": "proof of work"
    }}
  ],
  "portfolioTips": ["tip 1", "tip 2"]
}}

Make the roadmap realistic for internships and include basics-to-advanced sequencing.
Do not reuse generic software-engineering advice for every target role. Tailor topics,
skill gaps, tech stacks, interview preparation, and project ideas specifically to the
target role and the student's current skills.
"""
        return self._json_completion(
            system_message=(
                "You are a senior career mentor for computer science students. "
                "You produce practical, internship-ready learning plans as strict JSON."
            ),
            user_message=prompt,
        )

    def analyze_skills(self, profile: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            if self.mock_when_no_key:
                return {"skillGaps": self._mock_roadmap(profile)["skillGaps"]}
            raise RoadmapServiceError("Groq API key is not configured.", 503)

        prompt = f"""
Analyze the skill gaps for a student targeting {profile.get("targetRole")}.
Current skills: {profile.get("skills")}
Experience level: {profile.get("experienceLevel")}

Return only valid JSON:
{{
  "skillGaps": [
    {{
      "skill": "missing skill",
      "priority": "Must-learn | Optional",
      "reason": "short explanation",
      "suggestedAction": "specific next step"
    }}
  ],
  "strengths": ["strength 1"],
  "nextBestSkill": "single most important next skill"
}}
"""
        return self._json_completion(
            system_message="You are an expert technical recruiter and learning advisor. Return strict JSON.",
            user_message=prompt,
        )

    def chat(self, message: str, profile: dict[str, Any], roadmap_context: dict[str, Any]) -> dict[str, str]:
        if not self.client:
            if self.mock_when_no_key:
                return {
                    "reply": (
                        "Based on your roadmap, focus on the next unchecked must-learn skill, then turn it into "
                        "a small portfolio project. If you are asking about internships, you are usually ready to "
                        "start applying once you can explain two solid projects, use Git confidently, and solve "
                        "basic role-specific interview problems."
                    )
                }
            raise RoadmapServiceError("Groq API key is not configured.", 503)

        context = json.dumps(
            {
                "profile": profile,
                "roadmapSummary": {
                    "targetRole": roadmap_context.get("targetRole"),
                    "estimatedTimeline": roadmap_context.get("estimatedTimeline"),
                    "skillGaps": roadmap_context.get("skillGaps", [])[:6],
                },
            },
            ensure_ascii=True,
        )
        completion = self._completion(
            system_message=(
                "You are an encouraging AI career mentor. Give concise, actionable answers. "
                "Use the student's roadmap context when available."
            ),
            user_message=f"Context: {context}\n\nStudent question: {message}",
            temperature=0.55,
            max_tokens=550,
        )
        return {"reply": completion}

    def _json_completion(self, system_message: str, user_message: str) -> dict[str, Any]:
        try:
            raw = self._completion(
                system_message=system_message,
                user_message=user_message,
                temperature=0.35,
                max_tokens=3200,
                response_format={"type": "json_object"},
            )
        except RoadmapServiceError as exc:
            if exc.status_code != 502:
                raise
            raw = self._completion(
                system_message=system_message,
                user_message=f"{user_message}\n\nImportant: return only raw JSON, with no markdown.",
                temperature=0.35,
                max_tokens=3200,
            )
        return self._parse_json(raw)

    def _completion(
        self,
        system_message: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, str] | None = None,
    ) -> str:
        if not self.client:
            if self.mock_when_no_key:
                return "{}"
            raise RoadmapServiceError("Groq API key is not configured.", 503)

        try:
            params: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                params["response_format"] = response_format

            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
        except RateLimitError as exc:
            raise RoadmapServiceError("Groq rate limit reached. Please try again in a moment.", 429) from exc
        except APIConnectionError as exc:
            raise RoadmapServiceError("Could not connect to Groq. Check your network and try again.", 503) from exc
        except APIStatusError as exc:
            raise RoadmapServiceError(f"Groq API error: {exc.status_code}", 502) from exc

    def _parse_json(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise RoadmapServiceError("AI response was not valid JSON. Please try again.", 502)
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise RoadmapServiceError("AI response JSON could not be parsed. Please try again.", 502) from exc

    def _mock_roadmap(self, profile: dict[str, Any]) -> dict[str, Any]:
        name = profile.get("name") or "Student"
        target_role = profile.get("targetRole") or "AI Engineer"
        level = profile.get("experienceLevel") or "Beginner"
        current_skills = self._skill_set(profile.get("skills") or "")
        blueprint = self._role_blueprint(target_role)
        missing_skills = [skill for skill in blueprint["must_skills"] if skill.lower() not in current_skills]
        optional_skills = [skill for skill in blueprint["optional_skills"] if skill.lower() not in current_skills]

        return {
            "profileSummary": (
                f"{name} is targeting a {target_role} role at a {level.lower()} level. "
                f"This plan prioritizes {blueprint['domain']} skills, role-specific projects, "
                "and internship-ready proof of work."
            ),
            "targetRole": target_role,
            "estimatedTimeline": blueprint["timeline"],
            "roadmap": [
                {
                    "id": "phase-1",
                    "title": blueprint["phase_titles"][0],
                    "duration": "Weeks 1-4",
                    "goal": blueprint["phase_goals"][0],
                    "topics": blueprint["topics"][0],
                    "resources": blueprint["resources"][0],
                    "milestone": blueprint["milestones"][0],
                    "projects": [
                        {
                            "name": blueprint["projects"][0]["name"],
                            "description": blueprint["projects"][0]["description"],
                            "techStack": blueprint["projects"][0]["techStack"],
                            "difficulty": "Beginner",
                        }
                    ],
                },
                {
                    "id": "phase-2",
                    "title": blueprint["phase_titles"][1],
                    "duration": "Weeks 5-10",
                    "goal": blueprint["phase_goals"][1],
                    "topics": blueprint["topics"][1],
                    "resources": blueprint["resources"][1],
                    "milestone": blueprint["milestones"][1],
                    "projects": [
                        {
                            "name": blueprint["projects"][1]["name"],
                            "description": blueprint["projects"][1]["description"],
                            "techStack": blueprint["projects"][1]["techStack"],
                            "difficulty": "Intermediate",
                        }
                    ],
                },
                {
                    "id": "phase-3",
                    "title": blueprint["phase_titles"][2],
                    "duration": "Weeks 11-16",
                    "goal": blueprint["phase_goals"][2],
                    "topics": blueprint["topics"][2],
                    "resources": blueprint["resources"][2],
                    "milestone": blueprint["milestones"][2],
                    "projects": [
                        {
                            "name": blueprint["projects"][2]["name"],
                            "description": blueprint["projects"][2]["description"],
                            "techStack": blueprint["projects"][2]["techStack"],
                            "difficulty": "Advanced",
                        }
                    ],
                },
            ],
            "skillGaps": self._skill_gaps(missing_skills, optional_skills, blueprint),
            "weeklyPlan": [
                {
                    "week": "Week 1",
                    "focus": blueprint["weekly_focus"][0],
                    "tasks": blueprint["weekly_tasks"][0],
                    "deliverable": blueprint["weekly_deliverables"][0],
                },
                {
                    "week": "Week 2",
                    "focus": blueprint["weekly_focus"][1],
                    "tasks": blueprint["weekly_tasks"][1],
                    "deliverable": blueprint["weekly_deliverables"][1],
                },
                {
                    "week": "Week 3",
                    "focus": blueprint["weekly_focus"][2],
                    "tasks": blueprint["weekly_tasks"][2],
                    "deliverable": blueprint["weekly_deliverables"][2],
                },
                {
                    "week": "Week 4",
                    "focus": blueprint["weekly_focus"][3],
                    "tasks": blueprint["weekly_tasks"][3],
                    "deliverable": blueprint["weekly_deliverables"][3],
                },
            ],
            "portfolioTips": [
                f"Write one case study explaining how your {target_role} project solves a real problem.",
                f"Use a README section that maps each project feature to a {target_role} skill.",
                "Add screenshots, setup steps, and a short demo video for internship reviewers.",
            ],
        }

    def _skill_set(self, skills: str) -> set[str]:
        return {part.strip().lower() for part in re.split(r"[,;\n]+", skills) if part.strip()}

    def _skill_gaps(self, missing_skills: list[str], optional_skills: list[str], blueprint: dict[str, Any]):
        gaps = []
        for skill in missing_skills[:4]:
            gaps.append(
                {
                    "skill": skill,
                    "priority": "Must-learn",
                    "reason": blueprint["skill_reasons"].get(skill, f"{skill} is expected for this role."),
                    "suggestedAction": f"Practice {skill} through the phase projects and document what you learned.",
                }
            )
        for skill in optional_skills[:2]:
            gaps.append(
                {
                    "skill": skill,
                    "priority": "Optional",
                    "reason": blueprint["skill_reasons"].get(skill, f"{skill} can strengthen your profile."),
                    "suggestedAction": f"Add {skill} after the must-learn skills are comfortable.",
                }
            )
        return gaps or [
            {
                "skill": "Portfolio polish",
                "priority": "Must-learn",
                "reason": "You already listed many relevant skills, so presentation becomes the differentiator.",
                "suggestedAction": "Deploy one project, write a clear README, and prepare a two-minute explanation.",
            }
        ]

    def _role_blueprint(self, target_role: str) -> dict[str, Any]:
        role = target_role.lower()
        if any(word in role for word in ["data analyst", "business analyst", "analytics"]):
            return self._data_analyst_blueprint()
        if any(word in role for word in ["ai", "machine learning", "ml", "deep learning"]):
            return self._ai_engineer_blueprint()
        if any(word in role for word in ["frontend", "front end", "react", "ui developer"]):
            return self._frontend_blueprint()
        if any(word in role for word in ["cyber", "security", "soc"]):
            return self._cybersecurity_blueprint()
        if any(word in role for word in ["cloud", "devops", "sre"]):
            return self._devops_blueprint()
        return self._software_engineer_blueprint()

    def _data_analyst_blueprint(self):
        return {
            "domain": "data cleaning, SQL, dashboards, and business storytelling",
            "timeline": "12 to 18 weeks",
            "must_skills": ["Excel", "SQL", "Data cleaning", "Statistics", "Dashboard design", "Business storytelling"],
            "optional_skills": ["Power BI", "Tableau", "Python automation", "A/B testing"],
            "phase_titles": ["Analytics Foundations", "Dashboard and Insight Building", "Business Portfolio Readiness"],
            "phase_goals": [
                "Learn spreadsheet logic, SQL querying, and basic statistics.",
                "Turn raw datasets into clear dashboards and written insights.",
                "Build portfolio case studies that explain business decisions.",
            ],
            "topics": [
                ["Excel formulas", "SQL SELECT/JOIN/GROUP BY", "Descriptive statistics", "Data cleaning rules"],
                ["Pandas basics", "Dashboard layout", "KPI design", "Data visualization mistakes"],
                ["Case study writing", "Stakeholder questions", "Portfolio presentation", "Analytics interview SQL"],
            ],
            "resources": [
                ["Kaggle Learn SQL", "Excel practice datasets", "Statistics basics videos"],
                ["Pandas docs", "Power BI or Tableau tutorials", "Chart design guides"],
                ["SQL interview sets", "Analytics portfolio examples", "Public datasets"],
            ],
            "milestones": [
                "Analyze one messy CSV and publish cleaned results.",
                "Create one dashboard with 5 to 7 meaningful KPIs.",
                "Publish a case study with problem, process, insight, and recommendation.",
            ],
            "projects": [
                {
                    "name": "Student Performance Analysis",
                    "description": "Clean a student dataset and explain which factors affect grades.",
                    "techStack": ["Excel", "SQL", "Charts"],
                },
                {
                    "name": "Sales KPI Dashboard",
                    "description": "Build an interactive dashboard tracking revenue, categories, and regions.",
                    "techStack": ["Python", "Pandas", "Chart.js", "Flask"],
                },
                {
                    "name": "Customer Churn Insight Report",
                    "description": "Identify churn patterns and write recommendations for a business team.",
                    "techStack": ["SQL", "Pandas", "Power BI", "Markdown"],
                },
            ],
            "weekly_focus": ["SQL and spreadsheet basics", "Cleaning and statistics", "Dashboard building", "Case study polish"],
            "weekly_tasks": [
                ["Write 20 SQL queries", "Practice VLOOKUP/XLOOKUP", "Summarize one dataset"],
                ["Clean missing values", "Calculate averages and distributions", "Create 3 charts"],
                ["Design a KPI dashboard", "Add filters", "Write insight captions"],
                ["Refine the README", "Add screenshots", "Practice explaining recommendations"],
            ],
            "weekly_deliverables": ["SQL notebook", "Cleaned dataset", "Dashboard draft", "Published analytics case study"],
            "skill_reasons": {
                "SQL": "Most analyst internships test SQL because business data usually lives in databases.",
                "Dashboard design": "Analysts must communicate patterns quickly to non-technical teams.",
                "Business storytelling": "Insights matter only when they lead to a decision.",
            },
        }

    def _ai_engineer_blueprint(self):
        return {
            "domain": "Python, machine learning, model evaluation, APIs, and LLM applications",
            "timeline": "16 to 24 weeks",
            "must_skills": ["Python", "Linear algebra basics", "Statistics", "Machine learning", "Model evaluation", "APIs"],
            "optional_skills": ["Deep learning", "Vector databases", "MLOps", "Prompt engineering"],
            "phase_titles": ["Python and Math Foundations", "Machine Learning Systems", "AI Product Portfolio"],
            "phase_goals": [
                "Strengthen Python, math intuition, and dataset handling.",
                "Train, evaluate, and compare machine learning models.",
                "Deploy an AI application with API integration and clear evaluation.",
            ],
            "topics": [
                ["Python functions", "NumPy", "Pandas", "Statistics", "Linear algebra basics"],
                ["Supervised learning", "Feature engineering", "Model evaluation", "Experiment tracking"],
                ["LLM APIs", "Prompt design", "Deployment", "AI safety basics", "Portfolio storytelling"],
            ],
            "resources": [
                ["Python docs", "Kaggle Learn Pandas", "3Blue1Brown linear algebra"],
                ["Scikit-learn docs", "Kaggle competitions", "ML evaluation tutorials"],
                ["Groq docs", "Flask deployment guides", "AI app portfolio examples"],
            ],
            "milestones": [
                "Build a notebook that cleans data and explains features.",
                "Compare at least three ML models and explain metrics.",
                "Deploy an AI app with a live demo and case study.",
            ],
            "projects": [
                {
                    "name": "Dataset Explorer Notebook",
                    "description": "Clean and visualize a dataset while explaining patterns and assumptions.",
                    "techStack": ["Python", "Pandas", "Matplotlib"],
                },
                {
                    "name": "Internship Fit Predictor",
                    "description": "Train models that predict role fit from skills and project history.",
                    "techStack": ["Python", "Scikit-learn", "Flask", "Chart.js"],
                },
                {
                    "name": "AI Career Mentor",
                    "description": "Build a deployed LLM-powered mentor with chat, roadmap generation, and saved progress.",
                    "techStack": ["Flask", "Groq API", "JavaScript", "SQLite"],
                },
            ],
            "weekly_focus": ["Python and data handling", "Math and metrics", "Model training", "AI app deployment"],
            "weekly_tasks": [
                ["Practice Python functions", "Clean a CSV with Pandas", "Visualize 3 patterns"],
                ["Learn train/test split", "Calculate accuracy and F1", "Explain confusion matrices"],
                ["Train 3 models", "Tune one model", "Write model comparison notes"],
                ["Connect Groq API", "Deploy Flask app", "Write a project case study"],
            ],
            "weekly_deliverables": ["EDA notebook", "Metrics explanation", "Model comparison repo", "Deployed AI app"],
            "skill_reasons": {
                "Model evaluation": "AI roles require knowing whether a model is useful, biased, or overfitted.",
                "APIs": "AI engineers often package models or LLM calls into usable applications.",
                "Machine learning": "This is the core technical base for AI engineering internships.",
            },
        }

    def _frontend_blueprint(self):
        return {
            "domain": "HTML, CSS, JavaScript, responsive UI, accessibility, and React-style components",
            "timeline": "10 to 16 weeks",
            "must_skills": ["HTML", "CSS", "JavaScript", "Responsive design", "Accessibility", "API integration"],
            "optional_skills": ["React", "TypeScript", "UI testing", "Design systems"],
            "phase_titles": ["Interface Fundamentals", "Interactive Frontend Apps", "Production UI Portfolio"],
            "phase_goals": [
                "Master semantic HTML, CSS layout, and JavaScript basics.",
                "Build dynamic interfaces with API calls and saved state.",
                "Polish responsive, accessible projects for portfolio review.",
            ],
            "topics": [
                ["Semantic HTML", "Flexbox", "CSS Grid", "JavaScript DOM", "Forms"],
                ["Fetch API", "Local storage", "Component structure", "Loading states"],
                ["Accessibility", "Responsive QA", "Performance basics", "Deployment"],
            ],
            "resources": [
                ["MDN HTML/CSS", "JavaScript.info", "Frontend Mentor"],
                ["MDN Fetch", "Web.dev", "Public APIs"],
                ["WCAG quick reference", "Lighthouse", "Vercel or Netlify docs"],
            ],
            "milestones": [
                "Build a responsive static page with polished layout.",
                "Build an API-powered app with loading and error states.",
                "Deploy a frontend portfolio with accessibility checks.",
            ],
            "projects": [
                {
                    "name": "Responsive Portfolio Homepage",
                    "description": "Create a personal portfolio page with sections, cards, and mobile navigation.",
                    "techStack": ["HTML", "CSS", "JavaScript"],
                },
                {
                    "name": "Job Tracker Dashboard",
                    "description": "Track applications, statuses, notes, and interview dates in local storage.",
                    "techStack": ["JavaScript", "Chart.js", "LocalStorage"],
                },
                {
                    "name": "Design System Playground",
                    "description": "Build reusable UI components with theme switching and accessibility checks.",
                    "techStack": ["React", "CSS Modules", "Storybook"],
                },
            ],
            "weekly_focus": ["HTML/CSS layout", "JavaScript interaction", "APIs and state", "Responsive polish"],
            "weekly_tasks": [
                ["Build a semantic page", "Practice grid and flexbox", "Match a reference layout"],
                ["Add form validation", "Manipulate DOM nodes", "Store settings locally"],
                ["Call a public API", "Handle loading states", "Render dynamic cards"],
                ["Run Lighthouse", "Fix mobile spacing", "Deploy the project"],
            ],
            "weekly_deliverables": ["Responsive page", "Interactive form", "API dashboard", "Deployed frontend app"],
            "skill_reasons": {
                "Responsive design": "Frontend internships expect interfaces that work on phones and desktops.",
                "Accessibility": "Accessible UI shows professional care and improves real usability.",
                "API integration": "Most frontend roles require rendering server or third-party data.",
            },
        }

    def _cybersecurity_blueprint(self):
        return {
            "domain": "networking, Linux, web security, threat analysis, and defensive tooling",
            "timeline": "14 to 22 weeks",
            "must_skills": ["Networking", "Linux", "Web security", "Python scripting", "Log analysis", "OWASP Top 10"],
            "optional_skills": ["SIEM", "Cloud security", "Digital forensics", "Threat intelligence"],
            "phase_titles": ["Security Foundations", "Defensive Analysis Skills", "Cybersecurity Portfolio Labs"],
            "phase_goals": [
                "Learn networking, Linux commands, and security terminology.",
                "Analyze logs, common attacks, and vulnerable web patterns.",
                "Document safe labs and defensive projects for internships.",
            ],
            "topics": [
                ["TCP/IP basics", "Linux filesystem", "Permissions", "Security concepts"],
                ["OWASP Top 10", "Log analysis", "Python automation", "Incident notes"],
                ["SIEM basics", "Threat reports", "Hardening checklist", "Portfolio lab writeups"],
            ],
            "resources": [
                ["TryHackMe beginner paths", "Linux Journey", "Cisco networking basics"],
                ["OWASP docs", "Blue-team lab datasets", "Python scripting guides"],
                ["Splunk free training", "Cloud security docs", "Security writeup examples"],
            ],
            "milestones": [
                "Document basic network and Linux labs.",
                "Analyze sample logs and identify suspicious patterns.",
                "Publish safe, ethical lab writeups with screenshots.",
            ],
            "projects": [
                {
                    "name": "Linux Hardening Checklist",
                    "description": "Create a checklist app for basic Linux account, permission, and update checks.",
                    "techStack": ["Linux", "Bash", "Markdown"],
                },
                {
                    "name": "Suspicious Log Analyzer",
                    "description": "Parse sample logs and flag repeated failures, unusual IPs, and risky events.",
                    "techStack": ["Python", "Regex", "CSV"],
                },
                {
                    "name": "OWASP Learning Lab Report",
                    "description": "Build a safe vulnerable demo and explain risks plus fixes for common web issues.",
                    "techStack": ["Flask", "SQLite", "OWASP Top 10"],
                },
            ],
            "weekly_focus": ["Networking and Linux", "Web security basics", "Log analysis", "Portfolio lab writing"],
            "weekly_tasks": [
                ["Learn ports and protocols", "Practice Linux commands", "Write notes"],
                ["Study OWASP risks", "Identify input validation issues", "Write fixes"],
                ["Parse log files", "Flag suspicious rows", "Summarize patterns"],
                ["Create lab screenshots", "Write ethical scope", "Publish a report"],
            ],
            "weekly_deliverables": ["Networking notes", "OWASP summary", "Log analyzer script", "Security lab writeup"],
            "skill_reasons": {
                "Networking": "Security analysts need to understand traffic, ports, and protocols.",
                "OWASP Top 10": "Web security knowledge is a common internship screening topic.",
                "Log analysis": "Defensive roles rely on spotting suspicious activity in logs.",
            },
        }

    def _devops_blueprint(self):
        return {
            "domain": "Linux, cloud basics, CI/CD, containers, monitoring, and deployment reliability",
            "timeline": "14 to 20 weeks",
            "must_skills": ["Linux", "Git", "Docker", "CI/CD", "Cloud basics", "Monitoring"],
            "optional_skills": ["Kubernetes", "Terraform", "AWS", "GitHub Actions"],
            "phase_titles": ["Systems and Deployment Basics", "Automation and Containers", "Cloud Portfolio Readiness"],
            "phase_goals": [
                "Learn Linux, Git workflows, and app deployment basics.",
                "Containerize projects and automate tests/deployments.",
                "Build a cloud-ready portfolio project with monitoring notes.",
            ],
            "topics": [
                ["Linux commands", "Git branching", "Environment variables", "HTTP basics"],
                ["Dockerfiles", "Docker Compose", "CI pipelines", "Secrets handling"],
                ["Cloud deployment", "Monitoring", "Rollback planning", "Cost awareness"],
            ],
            "resources": [
                ["Linux Journey", "GitHub Skills", "Render/Railway docs"],
                ["Docker docs", "GitHub Actions docs", "12-factor app guide"],
                ["AWS or Azure beginner docs", "Prometheus/Grafana intros", "DevOps roadmap"],
            ],
            "milestones": [
                "Deploy one basic app from GitHub.",
                "Add Docker and a CI workflow to a project.",
                "Document deployment, monitoring, and rollback steps.",
            ],
            "projects": [
                {
                    "name": "One-Click Flask Deployment",
                    "description": "Deploy a Flask app with environment variables and a clear deployment guide.",
                    "techStack": ["Flask", "Git", "Render"],
                },
                {
                    "name": "Dockerized Student API",
                    "description": "Containerize an API and database with local development commands.",
                    "techStack": ["Docker", "Docker Compose", "PostgreSQL"],
                },
                {
                    "name": "CI/CD Portfolio Pipeline",
                    "description": "Run tests automatically and deploy only after successful checks.",
                    "techStack": ["GitHub Actions", "Docker", "Cloud hosting"],
                },
            ],
            "weekly_focus": ["Linux and Git", "Deployment basics", "Docker and CI", "Cloud operations"],
            "weekly_tasks": [
                ["Practice Linux commands", "Create branches", "Use environment variables"],
                ["Deploy a small app", "Write setup docs", "Test config errors"],
                ["Create Dockerfile", "Add CI workflow", "Run checks"],
                ["Add monitoring notes", "Write rollback steps", "Polish README"],
            ],
            "weekly_deliverables": ["Linux/Git notes", "Live deployed app", "Dockerized repo", "CI/CD case study"],
            "skill_reasons": {
                "Docker": "DevOps roles expect repeatable environments and container basics.",
                "CI/CD": "Automation is central to modern release workflows.",
                "Monitoring": "Reliable systems need health checks, logs, and alerting awareness.",
            },
        }

    def _software_engineer_blueprint(self):
        return {
            "domain": "programming fundamentals, data structures, backend APIs, databases, and deployment",
            "timeline": "16 to 24 weeks",
            "must_skills": ["Programming fundamentals", "Data structures", "Algorithms", "Databases", "APIs", "Testing"],
            "optional_skills": ["System design basics", "Cloud deployment", "TypeScript", "Docker"],
            "phase_titles": ["Programming Foundations", "Full-Stack Engineering Skills", "Internship-Ready Portfolio"],
            "phase_goals": [
                "Strengthen coding basics, Git, and problem-solving.",
                "Build API-backed applications with database persistence.",
                "Prepare for interviews and deploy polished projects.",
            ],
            "topics": [
                ["Functions", "OOP basics", "Git and GitHub", "Data structures"],
                ["REST APIs", "SQL databases", "Authentication", "Testing"],
                ["Deployment", "Interview problems", "System design basics", "Project documentation"],
            ],
            "resources": [
                ["Python or JavaScript docs", "GitHub Skills", "DSA practice sets"],
                ["Flask or Express docs", "SQLBolt", "Testing tutorials"],
                ["LeetCode easy/medium", "Render/Railway docs", "Portfolio examples"],
            ],
            "milestones": [
                "Publish two small repos with clean README files.",
                "Build a CRUD app with authentication and database storage.",
                "Deploy a capstone and prepare project explanations.",
            ],
            "projects": [
                {
                    "name": "Personal Task API",
                    "description": "Build a simple CRUD API for tasks with validation and tests.",
                    "techStack": ["Python", "Flask", "SQLite"],
                },
                {
                    "name": "Internship Application Tracker",
                    "description": "Create a full-stack app to manage applications, notes, and statuses.",
                    "techStack": ["Flask", "JavaScript", "SQLite", "Chart.js"],
                },
                {
                    "name": "Collaborative Study Planner",
                    "description": "Build a deployed app with accounts, saved plans, and progress analytics.",
                    "techStack": ["Flask", "PostgreSQL", "JavaScript", "Docker"],
                },
            ],
            "weekly_focus": ["Coding fundamentals", "Data structures", "APIs and databases", "Deployment and interviews"],
            "weekly_tasks": [
                ["Practice functions", "Use Git daily", "Solve 5 easy problems"],
                ["Implement arrays/maps/stacks", "Explain Big O", "Solve 5 DSA problems"],
                ["Build REST endpoints", "Connect SQLite", "Add tests"],
                ["Deploy app", "Write README", "Practice project walkthrough"],
            ],
            "weekly_deliverables": ["Coding repo", "DSA notes", "CRUD API", "Deployed capstone"],
            "skill_reasons": {
                "Data structures": "Software interviews often test arrays, maps, stacks, queues, and trees.",
                "Testing": "Tests show you can build reliable code beyond a demo.",
                "APIs": "Most software roles involve connecting frontends, backends, and data.",
            },
        }
