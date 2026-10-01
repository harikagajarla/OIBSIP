# Advanced Voice Assistant

A desktop-based Advanced Voice Assistant built with Python for the Oasis Infobyte Python Programming Internship — Task 1.

The application supports both voice and text commands and provides features such as speech recognition, text-to-speech, live weather, reminders, email sending, a local knowledge base, safe custom commands, website/app launching, and web search.

## Features

### Voice Assistant
- Voice input using SpeechRecognition and PyAudio
- Text input as an alternative to voice
- Indian English speech recognition (`en-IN`)
- Text-to-speech using pyttsx3
- Microphone availability checking
- Graceful handling of timeout, unintelligible speech, microphone, and speech-service errors

### Natural Language Intent Detection
The assistant uses rule-based natural language intent detection to identify user requests such as:

- Greeting
- Time
- Date
- Weather
- Web search
- Open website
- Open supported applications
- Set reminders
- List reminders
- Cancel reminders
- Send email
- Knowledge-base questions
- Custom commands
- Help
- Unknown commands

### Smart Reminders
- Natural-language reminder creation
- Relative times such as `in 10 minutes`
- Clock times such as `at 6 PM`
- Dates and weekdays
- Reminder listing
- Reminder cancellation
- Background reminder scheduler
- Automatic audible reminder notification

### Email
- GUI email form
- Recipient validation
- Subject and message fields
- Gmail SMTP support
- TLS-secured SMTP connection
- Gmail App Password support
- Background email sending
- Friendly success and error messages

### Local Knowledge Base
The assistant includes a built-in local FAQ knowledge base covering topics such as:

- Python
- Artificial Intelligence
- Machine Learning
- APIs
- FastAPI
- SQL
- SQLite
- Git
- GitHub
- NLP
- Intent Recognition
- Speech Recognition
- Text-to-Speech
- JavaScript
- Project and internship information

The knowledge base is local and does not claim general internet knowledge.

### Custom Commands
Users can create custom commands from the GUI.

Custom commands are stored in SQLite and their actions are passed through the assistant's supported intent system rather than being executed as arbitrary shell commands.

Example:

```text
Command name: python info
Action: what is python