def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            # Change the 'raise ValueError' to a print warning
            print("⚠️  WARNING: GEMINI_API_KEY missing. Narrative intelligence features will be disabled.")
            self.client = None
        else:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except ImportError:
                print("⚠️  google-genai not installed. Install with: pip install google-genai")
                self.client = None
            self.model_id = "gemini-2.0-flash" 
            logging.info("Gemini service initialized successfully")