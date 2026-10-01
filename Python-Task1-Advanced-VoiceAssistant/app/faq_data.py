"""The built-in questions and answers for the local knowledge base."""

from app.knowledge_base import FAQEntry

# Change this to your preferred display name later if needed.
AUTHOR_NAME = "Harika"


def build_entries():
    return [
        FAQEntry(
            id="what_can_you_do",
            question="What can you do?",
            aliases=(
                "what do you do",
                "what are your features",
                "what are your capabilities",
                "what are you capable of",
                "what are your skills",
            ),
            answer=(
                "I can tell you the time and date, check the current weather for a city, "
                "set and manage reminders, search the web, open websites and a few apps, "
                "help you send an email, and answer questions from my built-in knowledge base. "
                "Say help to see example commands."
            ),
        ),
        FAQEntry(
            id="who_are_you",
            question="Who are you?",
            aliases=(
                "what is your name",
                "introduce yourself",
                "tell me about yourself",
            ),
            answer=(
                "I am the Advanced Voice Assistant, a desktop assistant written in Python. "
                "You can talk to me with your microphone or type your commands."
            ),
        ),
        FAQEntry(
            id="creator",
            question="Who created you?",
            aliases=(
                "who made you",
                "who built you",
                "who developed you",
                "who is your creator",
                "who is your developer",
                "who programmed you",
                "who wrote you",
            ),
            answer=(
                f"I was created by {AUTHOR_NAME} as Task 1 of a Python programming "
                "internship with Oasis Infobyte."
            ),
        ),
        FAQEntry(
            id="how_it_works",
            question="How do you work?",
            aliases=(
                "how do you understand me",
                "how do you understand commands",
                "how does this assistant work",
                "how do you recognize my commands",
            ),
            answer=(
                "When you speak, an online speech recognition service turns your audio into text. "
                "Then I clean up the text, match it against a set of rules to find your intent, "
                "such as weather or reminder, and run the matching command. "
                "My intent detection is rule based. It is not a trained AI model."
            ),
        ),
        FAQEntry(
            id="limits",
            question="Do you know everything?",
            aliases=(
                "can you answer any question",
                "are you connected to the internet",
                "do you have internet access",
                "how much do you know",
                "can you answer anything",
            ),
            answer=(
                "No. My answers to general questions come from a small built-in knowledge base, "
                "so I only know the topics stored in it. I use the internet for speech recognition "
                "and weather, and web searches open in your browser, but I do not browse the "
                "internet to answer questions myself."
            ),
        ),
        FAQEntry(
            id="privacy",
            question="Do you store my voice?",
            aliases=(
                "is my voice stored",
                "is my data safe",
                "what data do you store",
                "what information do you store",
                "do you record my voice",
                "privacy",
            ),
            answer=(
                "I do not save your audio. While you use the microphone, the recording is sent "
                "to an online speech recognition service to be converted to text. Reminders, "
                "custom commands and settings are stored only in a local database file on your "
                "computer. Your weather key and email password stay in a local environment file "
                "and are never shown on screen."
            ),
        ),
        FAQEntry(
            id="how_to_reminder",
            question="How do I set a reminder?",
            aliases=(
                "how to set a reminder",
                "how do reminders work",
                "how can i create a reminder",
            ),
            answer=(
                "Say or type something like: remind me to call mom at 6 PM, or: set a reminder "
                "for tomorrow at 9 AM. You can also say: in 10 minutes. Say list my reminders "
                "to see them, or cancel reminder followed by its number to remove one."
            ),
        ),
        FAQEntry(
            id="how_to_email",
            question="How do I send an email?",
            aliases=(
                "how to send an email",
                "how does email work",
                "how can i email someone",
            ),
            answer=(
                "Say send an email and a form opens where you enter the recipient, subject and "
                "message. Emails are sent through your own email account using an app password "
                "stored in your local environment file."
            ),
        ),
        FAQEntry(
            id="project",
            question="What is this project?",
            aliases=(
                "what is this app",
                "what is this application",
                "tell me about this project",
                "what is this assistant for",
            ),
            keywords=("this project",),
            answer=(
                "This is the Advanced Voice Assistant, Task 1 of a Python programming internship "
                "with Oasis Infobyte. It supports voice and text commands, live weather, reminders, "
                "email, a local knowledge base and safe custom commands."
            ),
        ),
        FAQEntry(
            id="internship",
            question="What is Oasis Infobyte?",
            aliases=(
                "who is oasis infobyte",
                "tell me about oasis infobyte",
                "what is this internship",
            ),
            keywords=("oasis infobyte", "internship"),
            answer=(
                "Oasis Infobyte is the company that runs the internship program this project was "
                "built for. This assistant is Task 1, the Advanced Voice Assistant, of its Python "
                "programming track."
            ),
        ),
        FAQEntry(
            id="technologies",
            question="What technologies are used?",
            aliases=(
                "what technologies does this project use",
                "what is the tech stack",
                "which libraries are used",
                "what are you built with",
                "what language are you written in",
                "which programming language are you written in",
            ),
            answer=(
                "This assistant is written in Python. It uses CustomTkinter for the window, "
                "SpeechRecognition and PyAudio for the microphone, pyttsx3 for speech, requests for "
                "the weather service, SQLite for storage, and pytest for testing."
            ),
        ),
        FAQEntry(
            id="python",
            question="What is Python?",
            aliases=(
                "what is python programming",
                "what is python language",
            ),
            keywords=("python",),
            answer=(
                "Python is a high-level, general-purpose programming language known for its "
                "readable code. It is widely used for web development, automation, data science "
                "and AI. This assistant is written entirely in Python."
            ),
        ),
        FAQEntry(
            id="ai",
            question="What is AI?",
            aliases=("what is artificial intelligence",),
            keywords=("ai", "artificial intelligence"),
            answer=(
                "Artificial intelligence, or AI, is the field of building computer systems that "
                "perform tasks which normally need human intelligence, such as understanding "
                "language, recognizing images, making decisions and learning from data."
            ),
        ),
        FAQEntry(
            id="machine_learning",
            question="What is machine learning?",
            aliases=("what is ml",),
            keywords=("machine learning",),
            answer=(
                "Machine learning is a branch of AI where computers learn patterns from data "
                "instead of following fixed rules. It is used for things like recommending videos, "
                "detecting spam and recognizing speech."
            ),
        ),
        FAQEntry(
            id="api",
            question="What is an API?",
            aliases=("what is api",),
            keywords=("api",),
            answer=(
                "An API, or application programming interface, is a set of rules that lets one "
                "program talk to another. For example, this assistant calls a weather API to get "
                "the current weather."
            ),
        ),
        FAQEntry(
            id="fastapi",
            question="What is FastAPI?",
            keywords=("fastapi",),
            answer=(
                "FastAPI is a modern Python web framework for building APIs quickly. It uses "
                "Python type hints to validate data automatically and creates interactive "
                "documentation for your API."
            ),
        ),
        FAQEntry(
            id="sql",
            question="What is SQL?",
            aliases=("what does sql stand for",),
            keywords=("sql",),
            answer=(
                "SQL, or Structured Query Language, is the standard language for storing, "
                "querying and managing data in relational databases such as SQLite, PostgreSQL "
                "and MySQL."
            ),
        ),
        FAQEntry(
            id="sqlite",
            question="What is SQLite?",
            keywords=("sqlite",),
            answer=(
                "SQLite is a lightweight database that lives in a single file and needs no "
                "server. This assistant uses it to save reminders, custom commands and settings."
            ),
        ),
        FAQEntry(
            id="git",
            question="What is Git?",
            aliases=("what is git version control",),
            keywords=("git",),
            answer=(
                "Git is a version control system that tracks changes to your code, so you can "
                "review history, work on branches and collaborate with other developers."
            ),
        ),
        FAQEntry(
            id="github",
            question="What is GitHub?",
            keywords=("github",),
            answer=(
                "GitHub is a website that hosts Git repositories online, so you can back up your "
                "code, share it and collaborate with other developers."
            ),
        ),
        FAQEntry(
            id="nlp",
            question="What is NLP?",
            aliases=("what is natural language processing",),
            keywords=("nlp", "natural language processing"),
            answer=(
                "Natural language processing, or NLP, is the area of computing that deals with "
                "understanding human language. This assistant uses simple rule-based NLP: it "
                "cleans the text, matches patterns, and picks out details such as cities and times."
            ),
        ),
        FAQEntry(
            id="intent_recognition",
            question="What is intent recognition?",
            aliases=(
                "what is intent detection",
                "what is an intent",
                "what does intent mean",
            ),
            keywords=("intent recognition", "intent detection"),
            answer=(
                "Intent recognition means working out what the user wants from a sentence. "
                "For example, what is the weather in Pune means the weather intent, with Pune "
                "as the city."
            ),
        ),
        FAQEntry(
            id="speech_recognition",
            question="What is speech recognition?",
            aliases=(
                "what is speech to text",
                "how does speech recognition work",
            ),
            keywords=("speech recognition", "speech to text"),
            answer=(
                "Speech recognition converts spoken audio into written text. This assistant "
                "records from your microphone and uses the SpeechRecognition library with an "
                "online service to get the text."
            ),
        ),
        FAQEntry(
            id="text_to_speech",
            question="What is text to speech?",
            aliases=(
                "what is tts",
                "what is speech synthesis",
                "how do you speak",
                "how do you talk",
            ),
            keywords=("text to speech", "tts"),
            answer=(
                "Text to speech turns written text into spoken audio. This assistant uses pyttsx3, "
                "which speaks with the voices already installed on Windows and works offline."
            ),
        ),
        FAQEntry(
            id="threading",
            question="What is multithreading?",
            aliases=(
                "what is threading",
                "what is a thread",
                "why do you use threads",
            ),
            keywords=("threading", "multithreading", "threads"),
            answer=(
                "Threading lets a program do several things at the same time. This assistant uses "
                "background threads for listening, network calls, speaking and checking reminders, "
                "so the window never freezes."
            ),
        ),
    ]
