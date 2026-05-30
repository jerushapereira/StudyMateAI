# StudyMate AI

StudyMate AI is a beginner-to-intermediate AI-powered study assistant made with HTML, CSS, JavaScript, Python Flask, REST APIs, and the Groq API.

It is designed to look like a realistic college portfolio project: clean, useful, modern, and easy to explain in interviews.

## Features

- Paste study notes manually
- Upload `.txt` or `.md` notes files
- Generate AI summaries
- Generate quiz questions
- Generate flashcards
- Generate a 3-day study plan
- Ask AI doubts related to your notes
- Loading spinner while waiting for AI
- Error messages for missing notes or failed API requests
- Responsive layout for laptop and mobile
- Dark mode toggle
- Pomodoro timer
- Save and load summaries using `localStorage`
- Autosave pasted note drafts using `localStorage`
- Copy the latest AI response
- Download summary as a `.txt` file
- Simple study progress tracker

## Tech Stack

Frontend:

- HTML
- CSS
- JavaScript

Backend:

- Python
- Flask

API:

- REST API routes in Flask
- Groq API
- Model: `llama-3.3-70b-versatile`

## Folder Structure

```text
studymate-ai/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## Setup Instructions

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate the virtual environment:

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file by copying `.env.example`:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

5. Add your Groq API key inside `.env`:

```env
GROQ_API_KEY=your_real_groq_api_key_here
```

6. Run the Flask app:

```bash
python app.py
```

7. Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Groq API Setup

1. Create or log in to your Groq account.
2. Generate an API key from the Groq dashboard.
3. Paste the key into your `.env` file.
4. Keep the `.env` file private and do not upload it to GitHub.

## REST API Routes

### `POST /api/summarize`

Accepts notes as form data and returns a summary.

Response example:

```json
{
  "success": true,
  "summary": "Generated summary text"
}
```

### `POST /api/quiz`

Accepts notes as form data and returns quiz questions.

Response example:

```json
{
  "success": true,
  "quiz": "Generated quiz text"
}
```

### `POST /api/ask`

Accepts JSON with notes and a question.

Request example:

```json
{
  "notes": "Your notes here",
  "question": "Your doubt here"
}
```

### `POST /api/flashcards`

Accepts notes as form data and returns quick revision flashcards.

Response example:

```json
{
  "success": true,
  "flashcards": "Generated flashcards"
}
```

### `POST /api/study-plan`

Accepts notes as form data and returns a 3-day study plan.

Response example:

```json
{
  "success": true,
  "study_plan": "Generated study plan"
}
```

Response example:

```json
{
  "success": true,
  "answer": "Generated answer text"
}
```

## Interview Explanation

This project uses Flask as the backend server. The frontend sends requests with `fetch()` and `async/await` to Flask API routes. Flask validates the notes, sends prompts to the Groq API, and returns JSON responses. JavaScript updates the page dynamically without reloading.

The project also includes practical features like dark mode, a Pomodoro timer, flashcards, study plans, local summary saving, note autosave, copy/download actions, and a simple progress tracker to make it feel useful without becoming too complex.

## Important Notes

- Only `.txt` and `.md` uploads are supported to keep the project beginner-friendly.
- PDF upload is not included because it needs extra parsing libraries and more error handling.
- The `.env` file should not be committed to GitHub.
