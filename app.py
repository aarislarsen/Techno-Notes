from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import requests
import os
import json
import subprocess
import sys
import time
import threading
from pathlib import Path
import platform
import shutil
import secrets
import signal
import logging
from datetime import datetime
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
app.config['SECRET_KEY'] = secrets.token_hex(32)
PROMPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompt.txt')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_config.json')
OLLAMA_URL = 'http://127.0.0.1:11434'
ALLOWED_EXTENSIONS = {'pdf'}

# Rate limiting - simple in-memory store
request_times = {}
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

# Create directories with proper permissions
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], 'logs']:
    os.makedirs(folder, mode=0o700, exist_ok=True)

# Whitelist of allowed models
ALLOWED_MODELS = {
    'llama2', 'llama2:7b', 'llama2:13b', 'llama2:70b',
    'llama3', 'llama3:8b', 'llama3.2', 'llama3.2:1b', 'llama3.2:3b',
    'mistral', 'mistral:7b',
    'phi', 'phi:2.7b', 'phi3',
    'codellama', 'codellama:7b',
    'gemma', 'gemma:2b', 'gemma:7b'
}

def rate_limit(f):
    """Simple rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean old entries
        if client_ip in request_times:
            request_times[client_ip] = [t for t in request_times[client_ip] 
                                       if current_time - t < RATE_WINDOW]
        
        # Check rate limit
        if client_ip in request_times and len(request_times[client_ip]) >= RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
        
        # Add current request
        if client_ip not in request_times:
            request_times[client_ip] = []
        request_times[client_ip].append(current_time)
        
        return f(*args, **kwargs)
    return decorated_function

def validate_filename(filename):
    """Validate filename to prevent path traversal"""
    if not filename or not isinstance(filename, str):
        return False
    filename = os.path.basename(filename)
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    if len(filename) > 255:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_model_name(model_name):
    """Validate model name against whitelist"""
    if not model_name or not isinstance(model_name, str):
        return False
    model_name = model_name.lower().strip()
    if len(model_name) > 50:
        return False
    for allowed in ALLOWED_MODELS:
        if model_name == allowed or model_name.startswith(allowed + ':'):
            return True
    return False

def sanitize_input(text, max_length=10000):
    """Sanitize text input"""
    if not isinstance(text, str):
        return ""
    text = text[:max_length]
    text = text.replace('\x00', '')
    # Remove potential XSS vectors
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    return text

def safe_remove_file(filepath):
    """Safely remove a file with error handling"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except OSError as e:
        logger.error(f"Failed to remove file {filepath}: {e}")
    return False

class LLMManager:
    def __init__(self):
        self.config = self.load_config()
        self.ollama_process = None
        self.setup_lock = threading.Lock()
        self.setup_progress = {
            'stage': 'idle',
            'message': '',
            'progress': 0,
            'error': None
        }
    
    def load_config(self):
        """Safely load configuration"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if not isinstance(config, dict):
                        raise ValueError("Invalid config format")
                    if 'model_name' in config and not validate_model_name(config['model_name']):
                        config['model_name'] = 'llama2'
                    return config
        except (json.JSONDecodeError, ValueError, IOError) as e:
            logger.error(f"Config load error: {e}")
        
        return {
            'ollama_installed': False,
            'ollama_path': None,
            'model_name': 'llama2',
            'model_downloaded': False,
            'setup_complete': False
        }
    
    def save_config(self):
        """Safely save configuration"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            try:
                os.chmod(CONFIG_FILE, 0o600)
            except OSError:
                pass  # Ignore on Windows/WSL
        except IOError as e:
            logger.error(f"Config save error: {e}")
    
    def update_progress(self, stage, message, progress):
        """Update setup progress with sanitized values"""
        self.setup_progress = {
            'stage': sanitize_input(str(stage), 50),
            'message': sanitize_input(str(message), 200),
            'progress': max(0, min(100, int(progress))),
            'error': None
        }
        logger.info(f"Setup progress: {stage} - {message} ({progress}%)")
    
    def check_ollama_installed(self):
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(
                ['ollama', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                self.config['ollama_installed'] = True
                self.config['ollama_path'] = self.get_ollama_path()
                self.save_config()
                logger.info(f"Ollama found: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Ollama not found: {e}")
        return False
    
    def get_ollama_path(self):
        """Get Ollama executable path"""
        try:
            result = subprocess.run(
                ['which', 'ollama'],
                capture_output=True, 
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if os.path.isfile(path):
                    return path
        except (subprocess.TimeoutExpired, OSError):
            pass
        return None
    
    def install_ollama(self):
        """Automatically install Ollama"""
        self.update_progress('installing', 'Installing Ollama...', 20)
        
        try:
            install_url = 'https://ollama.com/install.sh'
            install_script = '/tmp/ollama_install.sh'
            
            # Download install script
            self.update_progress('installing', 'Downloading Ollama installer...', 25)
            logger.info("Downloading Ollama install script")
            
            result = subprocess.run([
                'curl', '-fsSL', '--max-time', '60', '--max-filesize', '1000000',
                install_url, '-o', install_script
            ], check=True, timeout=65, capture_output=True)
            
            if not os.path.exists(install_script):
                raise Exception("Install script download failed")
            
            file_size = os.path.getsize(install_script)
            if file_size > 1000000 or file_size < 100:
                safe_remove_file(install_script)
                raise Exception(f"Install script size suspicious: {file_size} bytes")
            
            try:
                os.chmod(install_script, 0o700)
            except OSError:
                pass
            
            # Run install script
            self.update_progress('installing', 'Running Ollama installer...', 40)
            logger.info("Running Ollama installer")

            result = subprocess.run(
                ['sh', install_script],
                check=True,
                timeout=600,
                env={'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')},
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Ollama installer output: {result.stdout[:200]}")
            
            safe_remove_file(install_script)
            
            time.sleep(2)
            if self.check_ollama_installed():
                self.update_progress('installed', 'Ollama installed successfully', 50)
                return True
            else:
                raise Exception("Installation completed but ollama command not found in PATH")
                
        except subprocess.TimeoutExpired:
            self.setup_progress['error'] = "Installation timeout - check network connection"
            logger.error("Ollama installation timeout")
            return False
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            self.setup_progress['error'] = f"Installation failed: {error_msg[:100]}"
            logger.error(f"Ollama installation failed: {error_msg}")
            return False
        except Exception as e:
            self.setup_progress['error'] = str(e)[:200]
            logger.error(f"Ollama installation error: {e}")
            return False
    
    def start_ollama_service(self):
        """Start Ollama service"""
        if self.ollama_process and self.ollama_process.poll() is None:
            logger.info("Ollama service already running")
            return True
        
        try:
            self.update_progress('starting', 'Starting Ollama service...', 60)
            logger.info("Starting Ollama service")
            
            # Kill existing processes
            try:
                subprocess.run(
                    ['pkill', '-9', 'ollama'], 
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                time.sleep(2)
            except (subprocess.TimeoutExpired, OSError):
                pass
            
            # Start service
            env = os.environ.copy()
            env['OLLAMA_HOST'] = '127.0.0.1:11434'
            
            self.ollama_process = subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True
            )
            
            logger.info(f"Ollama process started with PID: {self.ollama_process.pid}")
            
            # Wait for service with better error handling
            for i in range(30):
                try:
                    response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2)
                    if response.status_code == 200:
                        self.update_progress('started', 'Ollama service running', 70)
                        logger.info("Ollama service is ready")
                        return True
                except requests.RequestException:
                    time.sleep(1)
            
            # Check if process died
            if self.ollama_process.poll() is not None:
                stderr = self.ollama_process.stderr.read().decode('utf-8')[:500]
                logger.error(f"Ollama failed to start: {stderr}")
                raise Exception(f"Ollama service failed to start: {stderr[:200]}")
            
            logger.error("Ollama service didn't respond in 30 seconds")
            return False
            
        except Exception as e:
            self.setup_progress['error'] = str(e)[:200]
            logger.error(f"Failed to start Ollama service: {e}")
            return False
    
    def check_model_downloaded(self, model_name=None):
        """Check if model is downloaded"""
        if model_name is None:
            model_name = self.config['model_name']
        
        if not validate_model_name(model_name):
            return False
        
        try:
            response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                for model in models:
                    if model_name in model.get('name', ''):
                        self.config['model_downloaded'] = True
                        self.save_config()
                        logger.info(f"Model {model_name} found")
                        return True
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.debug(f"Error checking model: {e}")
        return False
    
    def download_model(self, model_name=None):
        """Download model with validation"""
        if model_name is None:
            model_name = self.config['model_name']
        
        if not validate_model_name(model_name):
            self.setup_progress['error'] = "Invalid model name"
            return False
        
        self.update_progress('downloading', f'Downloading model {model_name}...', 80)
        logger.info(f"Starting download of model: {model_name}")
        
        try:
            process = subprocess.Popen(
                ['ollama', 'pull', model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            start_time = time.time()
            last_update = time.time()
            
            for line in process.stdout:
                current_time = time.time()
                
                # Timeout check (30 minutes)
                if current_time - start_time > 1800:
                    process.kill()
                    raise Exception("Download timeout (30 minutes exceeded)")
                
                # Update progress message every 2 seconds
                if current_time - last_update > 2:
                    if 'pulling' in line.lower() or 'downloading' in line.lower():
                        clean_line = line.strip()[:200]
                        self.setup_progress['message'] = sanitize_input(clean_line, 200)
                        logger.debug(f"Download progress: {clean_line}")
                        last_update = current_time
            
            process.wait(timeout=60)
            
            if process.returncode == 0:
                self.config['model_name'] = model_name
                self.config['model_downloaded'] = True
                self.save_config()
                self.update_progress('complete', f'Model {model_name} ready', 95)
                logger.info(f"Model {model_name} downloaded successfully")
                return True
            else:
                raise Exception(f"Download failed with exit code {process.returncode}")
                
        except subprocess.TimeoutExpired:
            self.setup_progress['error'] = "Download timeout"
            logger.error("Model download timeout")
            return False
        except Exception as e:
            self.setup_progress['error'] = str(e)[:200]
            logger.error(f"Model download error: {e}")
            return False
    
    def get_status(self):
        """Get system status"""
        ollama_running = False
        try:
            response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2)
            ollama_running = response.status_code == 200
        except requests.RequestException:
            pass
        
        return {
            'ollama_installed': self.config['ollama_installed'],
            'ollama_running': ollama_running,
            'model_downloaded': self.config['model_downloaded'],
            'model_name': self.config['model_name'],
            'setup_complete': self.config.get('setup_complete', False),
            'ready': self.config['ollama_installed'] and ollama_running and self.config['model_downloaded']
        }
    
    def auto_setup(self, model_name='llama2'):
        """Automated model download and service startup"""
        if not validate_model_name(model_name):
            self.setup_progress['error'] = "Invalid model name"
            logger.error(f"Invalid model name requested: {model_name}")
            return False

        with self.setup_lock:
            try:
                logger.info(f"Starting auto-setup for model: {model_name}")

                # Step 1: Check Ollama is installed
                if not self.check_ollama_installed():
                    self.update_progress('error', 'Ollama not installed. Please run ./setup.sh first', 0)
                    logger.error("Ollama not installed - setup.sh must be run first")
                    return False

                self.update_progress('checking', 'Ollama detected', 20)

                # Step 2: Start service
                if not self.start_ollama_service():
                    logger.error("Failed to start Ollama service")
                    return False

                # Step 3: Download model
                if not self.check_model_downloaded(model_name):
                    if not self.download_model(model_name):
                        logger.error("Model download failed")
                        return False
                else:
                    self.update_progress('checking', f'Model {model_name} already downloaded', 90)

                # Mark complete
                self.config['setup_complete'] = True
                self.save_config()
                self.update_progress('complete', 'Setup complete - System ready', 100)
                logger.info("Auto-setup completed successfully")
                return True

            except Exception as e:
                self.setup_progress['error'] = str(e)[:200]
                logger.error(f"Auto-setup error: {e}")
                return False
    
    def cleanup(self):
        """Cleanup on shutdown"""
        if self.ollama_process and self.ollama_process.poll() is None:
            try:
                logger.info("Terminating Ollama process")
                self.ollama_process.terminate()
                self.ollama_process.wait(timeout=5)
            except:
                try:
                    self.ollama_process.kill()
                except:
                    pass

llm_manager = LLMManager()

def read_prompt():
    """Safely read prompt file"""
    try:
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                content = f.read(50000)
                return sanitize_input(content, 10000)
    except IOError as e:
        logger.error(f"Failed to read prompt file: {e}")
    return "Analyze this PDF document and provide a summary."

def save_prompt(prompt_text):
    """Safely save prompt file"""
    try:
        prompt_text = sanitize_input(prompt_text, 10000)
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        try:
            os.chmod(PROMPT_FILE, 0o600)
        except OSError:
            pass
        logger.info("Prompt saved successfully")
        return True
    except IOError as e:
        logger.error(f"Failed to save prompt: {e}")
        raise Exception(f"Failed to save prompt: {e}")

def extract_pdf_text(pdf_path):
    """Safely extract PDF text"""
    try:
        import PyPDF2
    except ImportError:
        raise Exception("PyPDF2 not installed")
    
    if not os.path.isfile(pdf_path):
        raise Exception("PDF file not found")
    
    file_size = os.path.getsize(pdf_path)
    if file_size > 50 * 1024 * 1024:
        raise Exception("PDF file too large (max 50MB)")
    
    logger.info(f"Extracting text from PDF ({file_size} bytes)")
    text = ""
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            max_pages = min(num_pages, 100)
            
            logger.info(f"PDF has {num_pages} pages, processing {max_pages}")
            
            for i in range(max_pages):
                try:
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract page {i+1}: {e}")
                    continue
                
                if len(text) > 500000:
                    logger.info("Text limit reached (500KB)")
                    text = text[:500000]
                    break
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise Exception(f"PDF extraction failed: {str(e)[:100]}")
    
    if not text.strip():
        raise Exception("No text could be extracted from PDF")
    
    logger.info(f"Extracted {len(text)} characters from PDF")
    return sanitize_input(text, 500000)

def query_ollama(prompt, context):
    """Query Ollama with timeout and validation"""
    prompt = sanitize_input(prompt, 10000)
    context = sanitize_input(context, 100000)
    
    payload = {
        "model": llm_manager.config['model_name'],
        "prompt": f"{prompt}\n\nDocument content:\n{context}",
        "stream": False
    }
    
    logger.info(f"Querying Ollama with model: {llm_manager.config['model_name']}")
    
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json=payload,
            timeout=300
        )
        response.raise_for_status()
        
        result = response.json()
        llm_response = result.get('response', '')
        
        logger.info(f"Received response from Ollama ({len(llm_response)} characters)")
        return sanitize_input(llm_response, 1000000)
        
    except requests.Timeout:
        logger.error("Ollama request timeout")
        raise Exception("LLM request timeout (5 minutes)")
    except requests.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        raise Exception(f"LLM request failed: {str(e)[:100]}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid Ollama response: {e}")
        raise Exception("Invalid LLM response format")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup_status', methods=['GET'])
def setup_status():
    status = llm_manager.get_status()
    status['progress'] = llm_manager.setup_progress
    return jsonify(status)

@app.route('/auto_setup', methods=['POST'])
@rate_limit
def auto_setup():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'error': 'Invalid request'}), 400
        
        model_name = data.get('model_name', 'llama2')
        
        if not isinstance(model_name, str):
            return jsonify({'error': 'Invalid model name type'}), 400
        
        if not validate_model_name(model_name):
            return jsonify({'error': 'Invalid model name'}), 400
        
        logger.info(f"Auto-setup requested for model: {model_name}")
        
        thread = threading.Thread(
            target=llm_manager.auto_setup,
            args=(model_name,)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'started'})
        
    except Exception as e:
        logger.error(f"Auto-setup endpoint error: {e}")
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/list_models', methods=['GET'])
def list_models():
    try:
        response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            valid_models = [
                m['name'] for m in models 
                if isinstance(m.get('name'), str) and validate_model_name(m['name'])
            ]
            return jsonify({'models': valid_models})
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Failed to list models: {e}")
    return jsonify({'models': []})

@app.route('/set_model', methods=['POST'])
@rate_limit
def set_model():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'error': 'Invalid request'}), 400
        
        model_name = data.get('model_name')
        
        if not isinstance(model_name, str):
            return jsonify({'error': 'Invalid model name type'}), 400
        
        if not validate_model_name(model_name):
            return jsonify({'error': 'Invalid model name'}), 400
        
        llm_manager.config['model_name'] = model_name
        llm_manager.save_config()
        logger.info(f"Model changed to: {model_name}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Set model error: {e}")
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/get_prompt', methods=['GET'])
def get_prompt():
    return jsonify({'prompt': read_prompt()})

@app.route('/save_prompt', methods=['POST'])
@rate_limit
def update_prompt():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict) or 'prompt' not in data:
            return jsonify({'error': 'Invalid request'}), 400
        
        if not isinstance(data['prompt'], str):
            return jsonify({'error': 'Invalid prompt type'}), 400
        
        save_prompt(data['prompt'])
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Save prompt error: {e}")
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/process_pdf', methods=['POST'])
@rate_limit
def process_pdf():
    filepath = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not validate_filename(file.filename):
            return jsonify({'error': 'Invalid filename'}), 400
        
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files allowed'}), 400
        
        unique_filename = f"{secrets.token_hex(8)}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        logger.info(f"Processing PDF: {filename}")
        file.save(filepath)
        
        if os.path.getsize(filepath) > app.config['MAX_CONTENT_LENGTH']:
            safe_remove_file(filepath)
            return jsonify({'error': 'File too large (max 50MB)'}), 400
        
        try:
            pdf_text = extract_pdf_text(filepath)
            prompt = read_prompt()
            llm_response = query_ollama(prompt, pdf_text)
            
            output_filename = f"{Path(filename).stem}_output.txt"
            output_path = os.path.join(
                app.config['OUTPUT_FOLDER'],
                f"{secrets.token_hex(8)}_{output_filename}"
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(llm_response)
            
            try:
                os.chmod(output_path, 0o600)
            except OSError:
                pass
            
            output_id = os.path.basename(output_path)
            logger.info(f"PDF processed successfully: {output_id}")
            
            return jsonify({
                'status': 'success',
                'output_file': output_id,
                'original_name': output_filename
            })
        
        finally:
            if filepath:
                safe_remove_file(filepath)
                
    except Exception as e:
        logger.error(f"Process PDF error: {e}")
        if filepath:
            safe_remove_file(filepath)
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        safe_filename = secure_filename(filename)
        if not safe_filename or safe_filename != filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
        
        if not os.path.isfile(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        real_path = os.path.abspath(filepath)
        output_dir = os.path.abspath(app.config['OUTPUT_FOLDER'])
        
        if not real_path.startswith(output_dir):
            logger.warning(f"Path traversal attempt: {filename}")
            return jsonify({'error': 'Access denied'}), 403
        
        logger.info(f"Downloading file: {safe_filename}")
        response = send_file(filepath, as_attachment=True)
        
        @response.call_on_close
        def cleanup():
            safe_remove_file(filepath)
        
        return response
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)[:200]}), 500

def cleanup_old_files():
    """Remove files older than 1 hour"""
    try:
        current_time = time.time()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            if not os.path.exists(folder):
                continue
            
            cleaned = 0
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    if current_time - os.path.getmtime(filepath) > 3600:
                        if safe_remove_file(filepath):
                            cleaned += 1
            
            if cleaned > 0:
                logger.info(f"Cleaned {cleaned} old files from {folder}")
                
    except OSError as e:
        logger.error(f"Cleanup error: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutting down gracefully...")
    print("\nShutting down gracefully...")
    llm_manager.cleanup()
    cleanup_old_files()
    sys.exit(0)

def startup_sequence():
    """Startup sequence"""
    print("=== LLM PDF Processor Startup ===")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    logger.info("Application starting")
    
    cleanup_old_files()
    
    if llm_manager.config.get('setup_complete', False):
        print("✓ Setup complete")
        logger.info("Setup already complete")
        
        if llm_manager.start_ollama_service():
            print("✓ Ollama service started")
            print(f"✓ Model '{llm_manager.config['model_name']}' ready")
            print("\n=== System Ready ===")
            print("Access the application at:")
            print("  http://127.0.0.1:5000")
            print("  http://localhost:5000")
            if 'WSL' in platform.uname().release or 'microsoft' in platform.uname().release.lower():
                print("\nWSL Detected: Access from Windows browser at:")
                print("  http://localhost:5000")
            logger.info("System ready")
        else:
            print("✗ Failed to start Ollama service")
            print("Complete setup at http://127.0.0.1:5000")
            logger.warning("Ollama service failed to start")
    else:
        print("First-time setup required")
        print("Access the application at http://127.0.0.1:5000")
        logger.info("First-time setup required")
    
    print("\nPress Ctrl+C to stop")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    startup_sequence()
    
    try:
        logger.info("Starting Flask application on 0.0.0.0:5000")
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
