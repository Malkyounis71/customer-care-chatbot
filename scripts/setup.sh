#!/bin/bash

echo "Setting up COB Customer Care Chatbot..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger'); nltk.download('vader_lexicon')"

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please update .env file with your configuration"
fi

# Create necessary directories
mkdir -p logs
mkdir -p data/qdrant_storage

# Set execute permissions
chmod +x setup.sh

echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo "Next steps:"
echo "1. Update .env file with your settings"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the application: python -m app.main"
echo "Or use Docker: docker-compose up -d"
