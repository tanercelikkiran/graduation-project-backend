# Edifica - Language Learning Backend

A comprehensive FastAPI backend for the Edifica language learning platform, providing AI-powered vocabulary training, pyramid sentence exercises, and writing evaluation features.

## 🌟 Features

### Core Learning Modules

- **🔤 Vocabulary Training**: AI-generated vocabulary lists with difficulty tracking and hint systems
- **📐 Pyramid Exercises**: Interactive sentence manipulation exercises (expand, shrink, replace, paraphrase)
- **✍️ Writing Evaluation**: AI-powered writing assessment with detailed feedback and scoring

### User Management

- **🔐 Authentication**: JWT-based authentication with refresh tokens
- **👤 User Profiles**: Customizable learning preferences (language, level, purpose)
- **📊 Progress Tracking**: XP system, statistics, and performance analytics
- **🏆 Leaderboards**: Community engagement and competition

### AI Integration

- **🤖 Google Gemini**: Advanced language processing for content generation and evaluation
- **🌐 Multi-language Support**: Supports multiple learning and system languages
- **📈 Adaptive Learning**: Content difficulty adjustment based on user performance

## 🏗️ Architecture

### Technology Stack

- **Backend Framework**: FastAPI
- **Database**: MongoDB with PyMongo
- **AI Services**: Google Gemini AI
- **Authentication**: JWT with bcrypt password hashing
- **Environment**: Python 3.10+

### Project Structure

```text
src/
├── api_clients/           # AI service integrations
│   ├── api.py            # Client configurations
│   ├── pyramid_prompts.py # Pyramid exercise generation
│   ├── vocabulary_prompts.py # Vocabulary generation
│   └── writing_prompts.py # Writing evaluation
├── database/             # Database configuration
│   └── database.py       # MongoDB connection and collections
├── models/               # Pydantic data models
│   ├── user.py          # User models
│   ├── vocabulary.py    # Vocabulary models
│   ├── pyramid.py       # Pyramid exercise models
│   └── writing.py       # Writing evaluation models
├── routes/               # API endpoints
│   ├── authentication.py # Auth endpoints
│   ├── user.py          # User management
│   ├── vocabulary.py    # Vocabulary exercises
│   ├── pyramid.py       # Pyramid exercises
│   ├── writing.py       # Writing evaluation
│   └── [other routes]   # Additional features
├── services/             # Business logic
│   ├── authentication_service.py
│   ├── vocabulary_service.py
│   ├── pyramid_service.py
│   ├── writing_service.py
│   └── [other services]
└── settings.py           # Configuration management
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MongoDB instance
- Google Gemini API key

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd graduation-project-backend
   ```

2. **Set up virtual environment**

   ```bash
   python -m venv env
   # On Windows
   env\Scripts\activate
   # On macOS/Linux
   source env/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r src/requirements.txt
   ```

5. **Run the application**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

```bash
# Build the image
docker build -t edifica-backend .

# Run the container
docker run -d -p 8000:8000 --env-file .env edifica-backend
```

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

### Key Endpoints

#### Authentication

- `POST /login` - User login
- `POST /user/register` - User registration
- `POST /user/refresh-token` - Token refresh

#### Vocabulary Module

- `POST /vocabulary/create` - Generate new vocabulary list
- `POST /vocabulary/track-hint` - Track hint usage for analytics
- `POST /vocabulary/track-attempt` - Track learning attempts
- `GET /vocabulary/difficult-words` - Get words user struggles with

#### Pyramid Module

- `POST /pyramid/create` - Create new pyramid exercise
- `POST /pyramid/preview/next-step-options` - Preview next exercise steps
- `POST /pyramid/append-step` - Add step to pyramid
- `POST /pyramid/complete` - Complete pyramid exercise

#### Writing Module

- `POST /writing/evaluate` - Evaluate writing submission
- `POST /writing/answer` - Submit answer to writing question
- `GET /writing/questions/{level}` - Get writing questions by level

## 🧠 AI-Powered Features

### Vocabulary Generation

- **Adaptive Content**: AI generates vocabulary based on user level, purpose, and learning history
- **Difficulty Tracking**: Machine learning algorithms track word difficulty based on user interactions
- **Multi-language Support**: Supports vocabulary generation in multiple languages with native translations

### Pyramid Exercises

The pyramid exercise system helps users learn sentence structure through four operations:

- **Expand**: Add words to make sentences more detailed
- **Shrink**: Remove words while maintaining meaning
- **Replace**: Substitute words with synonyms or alternatives
- **Paraphrase**: Rewrite sentences with different structures

### Writing Evaluation

- **Comprehensive Scoring**: Evaluates content (1-5), organization (1-5), and language usage (1-5)
- **Detailed Feedback**: Provides specific suggestions for grammar, spelling, punctuation, and style
- **Multi-criteria Assessment**: Analyzes relevance, clarity, structure, flow, and technical correctness

## 🔧 Configuration

### Database Collections

- `User` - User profiles and authentication
- `Vocabulary` - Generated vocabulary lists
- `Pyramid` - Pyramid exercise data
- `Writing` / `WritingAnswer` - Writing exercises and responses
- `UserEvent` - User activity tracking
- `VocabularyStatistic` - Learning analytics
- `TranslationCache` - Translation caching

## 🎯 Learning Analytics

The platform includes comprehensive analytics to track user progress:

- **XP System**: Users earn experience points for completing exercises
- **Difficulty Tracking**: Algorithms identify words users struggle with
- **Performance Metrics**: Success rates, time spent, hint usage
- **Progress Monitoring**: Weekly goals and achievement tracking
- **Leaderboards**: Community ranking and engagement

## 🛡️ Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Security**: bcrypt hashing with complexity requirements
- **Content Filtering**: AI-powered inappropriate content detection
- **Rate Limiting**: Built-in protection against API abuse
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 🌐 Multi-language Support

The platform supports learning multiple languages:

- **Dynamic Content Generation**: AI creates content in target languages
- **Language-specific Grammar**: Evaluation follows target language rules
- **Cultural Context**: Content adapted to cultural contexts
- **Native Feedback**: Feedback provided in user's preferred language

## 🔄 Event Tracking

Comprehensive event logging for analytics:

- User authentication events (login, logout, token refresh)
- Learning session events (vocabulary, pyramid, writing)
- Progress tracking events (XP gains, level advancement)
- Performance analytics (hint usage, success rates)

## 📈 Performance Optimization

- **Database Indexing**: Optimized MongoDB queries
- **Caching**: Translation and content caching
- **Async Operations**: Non-blocking I/O for better performance
- **Error Handling**: Robust error handling and logging
- **Retry Logic**: Automatic retry for AI API calls

## 🔗 Related Projects

This backend is designed to work with:

- **Edifica Mobile App**: React Native frontend application

Built with ❤️ for language learners worldwide
