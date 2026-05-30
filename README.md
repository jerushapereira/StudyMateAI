# AI Career Roadmap Generator

A modern Flask + HTML/CSS/JavaScript portfolio project that generates personalized career roadmaps with the Groq API. Students enter their current skills, experience level, and target role, then receive a roadmap, skill gap analysis, project ideas, progress tracking, and AI mentor chat.

## Features

- Student profile form with skills, experience level, and target role
- Groq-powered roadmap generation using `llama-3.3-70b-versatile`
- Skill gap analysis with must-learn and optional priorities
- Beginner, intermediate, and advanced project suggestions
- Checklist progress tracker with local storage
- Chart.js progress visualization
- AI mentor chat endpoint
- Login, logout, and create-account flow with Flask sessions
- Responsive SaaS-style dashboard with light/dark mode
- Demo fallback data when no Groq API key is configured

## Folder Structure

```text
ai-career-roadmap-generator/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   └── groq_service.py
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
└── templates/
    └── index.html
```

## Setup

1. Create a virtual environment.

```bash
python -m venv .venv
```

2. Activate it.

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example`.

```bash
cp .env.example .env
```

5. Add your Groq API key.

```env
GROQ_API_KEY=your_real_key
GROQ_MODEL=llama-3.3-70b-versatile
```

6. Run the app.

```bash
python app.py
```

7. Open the app at:

```text
http://127.0.0.1:5000
```

## API Endpoints

### `POST /generate-roadmap`

Generates the full roadmap, weekly plan, skill gaps, portfolio tips, and projects.

Request:

```json
{
  "name": "Aarav",
  "skills": "Python basics, HTML, CSS, SQL, Git",
  "experienceLevel": "Beginner",
  "targetRole": "AI Engineer"
}
```

### `POST /analyze-skills`

Returns a focused skill gap analysis.

### `POST /chat`

Returns an AI mentor response.

### `POST /auth/register`

Creates an account and logs the user in.

### `POST /auth/login`

Logs in an existing user.

### `POST /auth/logout`

Logs out the current user.

Request:

```json
{
  "message": "Am I ready for internships?",
  "profile": {
    "skills": "Python basics, HTML, CSS, SQL, Git",
    "experienceLevel": "Beginner",
    "targetRole": "AI Engineer"
  },
  "roadmapContext": {}
}
```

## Sample Output

```json
{
  "profileSummary": "Aarav is targeting an AI Engineer role and should move from Python foundations to machine learning projects.",
  "targetRole": "AI Engineer",
  "estimatedTimeline": "16 to 24 weeks",
  "roadmap": [
    {
      "title": "Foundations and Core Tools",
      "duration": "Weeks 1-4",
      "goal": "Strengthen programming, Git, and problem-solving basics.",
      "topics": ["Python fundamentals", "Git and GitHub", "Data structures"],
      "projects": [
        {
          "name": "Personal Skill Tracker",
          "description": "A small app that logs skills and weekly reflections.",
          "techStack": ["Python", "Flask", "SQLite"],
          "difficulty": "Beginner"
        }
      ]
    }
  ],
  "skillGaps": [
    {
      "skill": "Model evaluation",
      "priority": "Must-learn",
      "reason": "AI roles require understanding model quality and tradeoffs.",
      "suggestedAction": "Learn accuracy, precision, recall, F1, and confusion matrices."
    }
  ]
}
```

## Notes for Portfolio Use

- Keep `MOCK_AI_WHEN_NO_KEY=True` while recording demos without an API key.
- Set `MOCK_AI_WHEN_NO_KEY=False` for stricter production behavior.
- Target role is a free-text input, so students can enter any career path.
- Add screenshots and a deployed link to make the project internship-ready.
