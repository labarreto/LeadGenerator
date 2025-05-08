# Lead Generator

A web application that analyzes business websites to generate potential sales leads with contact information using AI.

## Features

- Website scraping and content extraction
- Company analysis using LLMs (locally or via APIs)
- Lead identification and contact information retrieval
- Simple web interface for inputting target websites and viewing results
- Personalized outreach suggestions for each lead

## Demo

![Lead Generator Demo](https://via.placeholder.com/800x400?text=Lead+Generator+Demo)

## Technologies Used

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **AI/ML**: Local LLMs via Ollama, Hugging Face Transformers
- **Data Processing**: BeautifulSoup, NLTK, Pandas
- **Deployment**: Local or Google Colab with GPU acceleration

## Setup

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LeadGenerator.git
cd LeadGenerator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Ollama (for local LLM processing):
```bash
# Mac/Linux
curl -fsSL https://ollama.com/install.sh | sh
# Then pull the model
ollama pull phi3
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys if using external services
```

5. Run the application:
```bash
python app.py
```

### Google Colab Setup

1. Open the `colab_setup.py` file for detailed instructions
2. Follow the step-by-step guide to set up the project in Google Colab
3. Take advantage of Colab's GPU for faster processing

## Project Structure

```
LeadGenerator/
├── app.py                 # Main Flask application
├── colab_setup.py         # Google Colab setup instructions
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── scraper/               # Website scraping modules
│   └── website_scraper.py
├── analyzer/              # Content analysis modules
│   └── content_analyzer.py
├── lead_finder/           # Lead identification modules
│   └── lead_generator.py
├── utils/                 # Utility functions
│   └── helpers.py
├── templates/             # HTML templates
│   ├── index.html
│   └── results.html
└── static/                # Static assets
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Usage

1. Enter a target business website URL
2. The system will analyze the website and identify potential leads
3. View and export the generated leads with contact information
4. Use the personalized outreach suggestions for each lead

## Limitations

- The contact information is predicted based on patterns and may not be 100% accurate
- Website scraping may be limited by robots.txt restrictions
- Performance depends on the hardware/GPU available

## Future Improvements

- Integration with email verification APIs
- Support for more complex website structures
- Enhanced lead scoring algorithms
- CRM integration for direct export

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Uses [Ollama](https://ollama.ai/) for local LLM inference
- Inspired by modern lead generation techniques
