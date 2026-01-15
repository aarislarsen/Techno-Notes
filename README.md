# PDF LLM Processor

> 🚀 Automated PDF document analysis using local LLM (Ollama). Zero-configuration setup for Ubuntu/WSL.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- 🔒 **Privacy-First**: All processing happens locally - your data never leaves your machine
- 🚀 **Fully Automated Setup**: One-click installation of all dependencies including Ollama
- 🎯 **Simple Interface**: Beautiful drag-and-drop web UI with customizable prompts
- 🛡️ **Security Hardened**: Input validation, rate limiting, sanitization, and secure file handling
- 📦 **Self-Contained**: Isolated virtual environment with dependency management
- ⚡ **Multiple Models**: Support for Llama, Mistral, Phi, and more

## 🚀 Quick Start

### Prerequisites

- Ubuntu 20.04+ or WSL2 with Ubuntu
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- Internet connection (for initial setup)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-llm-processor.git
cd pdf-llm-processor

# Run automated setup
chmod +x setup.sh
./setup.sh
```

The setup script automatically:
- ✅ Installs Python 3 and system dependencies
- ✅ Creates isolated virtual environment
- ✅ Installs Python packages (Flask, PyPDF2, requests)
- ✅ Sets up application structure with proper permissions

### First Run
```bash
./run.sh
```

Open your browser to: **http://localhost:5000**

Click **"Start Automatic Setup"** to:
1. Install Ollama automatically
2. Download your selected LLM model (choose smaller models like phi or llama3.2:1b for faster setup)
3. Start the service

⏱️ **Note**: Initial setup downloads 1-8GB of model data depending on model choice.

### Subsequent Runs
```bash
./run.sh
```

System starts immediately with no setup required.

## 📖 Usage

### Basic Workflow

1. **Configure Analysis Prompt**
   - Edit the prompt in the web interface to customize how the AI analyzes documents
   - Default prompt provides comprehensive summaries with key points

2. **Upload PDF**
   - Drag and drop PDF file (max 50MB, 100 pages)
   - Or click to browse and select file

3. **Wait for Processing**
   - Processing time varies by model size and document length
   - Typically 30 seconds to 3 minutes

4. **Download Results**
   - Analysis automatically downloads as a text file
   - Original filename preserved with "_output.txt" suffix

### Custom Prompts

Edit the prompt to analyze documents for specific purposes:

**Executive Summary:**
```
Provide an executive summary of this document including:
- Key business objectives
- Main findings
- Financial implications
- Recommended actions
```

**Technical Analysis:**
```
Analyze the technical aspects of this document:
- Technical specifications
- Implementation details
- Potential challenges
- Technology stack recommendations
```

**Legal Review:**
```
Review this document focusing on:
- Key contractual obligations
- Risk factors
- Compliance requirements
- Recommended legal actions
```

## 🤖 Supported Models

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| llama3.2:1b | 1B | ⚡⚡⚡⚡ | ⭐ | Ultra-fast, testing |
| phi | 2.7B | ⚡⚡⚡ | ⭐⭐ | Quick analysis |
| llama3.2:3b | 3B | ⚡⚡⚡ | ⭐⭐ | Balanced speed/quality |
| llama2 | 7B | ⚡⚡ | ⭐⭐⭐ | **Recommended default** |
| mistral | 7B | ⚡⚡ | ⭐⭐⭐ | Efficient processing |
| codellama | 7B | ⚡⚡ | ⭐⭐⭐ | Code-heavy documents |
| llama2:13b | 13B | ⚡ | ⭐⭐⭐⭐ | High quality analysis |

## 🏗️ Architecture
```
pdf-llm-processor/
├── app.py                 # Flask application with security hardening
├── templates/
│   └── index.html        # Modern responsive web interface
├── uploads/              # Temporary upload storage (auto-cleanup)
│   └── .gitkeep
├── outputs/              # Generated analysis files (auto-cleanup)
│   └── .gitkeep
├── logs/                 # Application logs
│   └── .gitkeep
├── prompt.txt            # Customizable analysis prompt
├── llm_config.json       # Configuration (auto-generated)
├── venv/                 # Isolated Python environment
├── requirements.txt      # Python dependencies
├── setup.sh              # Automated setup script
├── run.sh                # Application launcher
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
└── README.md            # This file
```

## 🔒 Security Features

### Input Validation
- ✅ Filename sanitization and path traversal prevention
- ✅ Model name whitelist validation
- ✅ File size limits (50MB max)
- ✅ File type verification (PDF only)
- ✅ Text length limits at multiple checkpoints

### Data Protection
- ✅ All processing happens locally (no external API calls)
- ✅ Automatic file cleanup (1-hour retention)
- ✅ Restrictive file permissions (0600)
- ✅ Secure session management
- ✅ XSS prevention with HTML escaping

### Network Security
- ✅ Ollama service bound to localhost only (127.0.0.1)
- ✅ Flask application configurable binding
- ✅ Rate limiting (10 requests/minute per IP)
- ✅ Request timeout enforcement

### Application Security
- ✅ No shell injection vulnerabilities
- ✅ Comprehensive error logging
- ✅ Graceful shutdown handling
- ✅ Process isolation
- ✅ Input sanitization on all endpoints

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>
```

### Ollama Service Won't Start
```bash
# Check if Ollama is installed
ollama --version

# Manually start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Model Download Fails
```bash
# Check disk space
df -h

# Manually download model
ollama pull llama2

# Verify download
ollama list
```

### WSL Network Issues

**Can't access from Windows browser:**

1. Get WSL IP address:
```bash
   ip addr show eth0 | grep inet
```

2. Access via: `http://<WSL_IP>:5000`

**Or** use `localhost:5000` (usually works by default in WSL2).

### Out of Memory

**Solutions:**
- Use smaller model (phi, llama3.2:1b)
- Close other applications
- Increase WSL memory limit (edit `.wslconfig` in Windows user folder)
- Process smaller PDF files

### PDF Text Extraction Fails

**Common causes:**
- Scanned PDFs (image-only, no text layer)
- Encrypted/password-protected PDFs
- Corrupted PDF files

**Solutions:**
- Use OCR to convert scanned PDFs to text-based PDFs
- Remove password protection before upload
- Try re-saving the PDF in a different viewer

## ⚙️ Advanced Configuration

### Environment Variables
```bash
# Change Ollama host (if needed)
export OLLAMA_HOST=127.0.0.1:11434
```

### Custom Model Installation
```bash
# Download specific model version
ollama pull llama2:13b

# List available models
ollama list

# Remove unused models to free space
ollama rm <model-name>
```

### Systemd Service (Optional)

Run as a system service that starts automatically:
```bash
# Create service file
sudo nano /etc/systemd/system/pdf-llm-processor.service
```

Add this content (replace YOUR_USERNAME with your actual username):
```ini
[Unit]
Description=PDF LLM Processor
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/pdf-llm-processor
ExecStart=/home/YOUR_USERNAME/pdf-llm-processor/venv/bin/python3 app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable pdf-llm-processor
sudo systemctl start pdf-llm-processor
sudo systemctl status pdf-llm-processor

# View logs
sudo journalctl -u pdf-llm-processor -f
```

### Logging Configuration

Logs are stored in `logs/app.log`. To adjust log level, edit `app.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for verbose logging
    # ...
)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/pdf-llm-processor.git
cd pdf-llm-processor

# Run setup
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Make your changes to app.py or other files

# Test your changes
./run.sh
```

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes thoroughly
4. Ensure security best practices are followed
5. Update documentation if needed
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📊 API Endpoints

For developers who want to integrate programmatically:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/setup_status` | GET | Get system setup status |
| `/auto_setup` | POST | Start automatic Ollama setup |
| `/process_pdf` | POST | Upload and process PDF |
| `/download/<file>` | GET | Download analysis result |
| `/get_prompt` | GET | Get current analysis prompt |
| `/save_prompt` | POST | Save custom analysis prompt |
| `/list_models` | GET | List available models |
| `/set_model` | POST | Change active model |

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM runtime that makes this possible
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework
- [PyPDF2](https://pypdf2.readthedocs.io/) - PDF processing library
- [Meta AI](https://ai.meta.com/) - Llama models
- [Mistral AI](https://mistral.ai/) - Mistral models

## 📞 Support

- 📖 [Documentation](https://github.com/yourusername/pdf-llm-processor/wiki)
- 💬 [Discussions](https://github.com/yourusername/pdf-llm-processor/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/pdf-llm-processor/issues)

## 🔐 Security

Found a security vulnerability? Please email security@yourproject.com instead of opening a public issue.

## 📊 Project Status

- ✅ Core functionality complete
- ✅ Security hardening applied
- ✅ Documentation complete
- ✅ Ready for production use
- 🔄 Ongoing maintenance and updates

## 🗺️ Roadmap

Future planned features:

- [ ] Support for more document formats (DOCX, TXT, Markdown)
- [ ] Batch processing capabilities
- [ ] API-only mode (headless operation)
- [ ] Docker container support
- [ ] Multi-language support for UI
- [ ] Custom model fine-tuning guide
- [ ] Cloud deployment guides (AWS, Azure, GCP)
- [ ] Export to multiple formats (PDF, DOCX, Markdown)

## 💡 Use Cases

### Business
- Contract analysis and review
- Report summarization
- Meeting minutes extraction
- Proposal evaluation

### Academic
- Research paper summarization
- Literature review assistance
- Thesis chapter analysis
- Citation extraction

### Legal
- Document discovery
- Contract clause identification
- Compliance checking
- Legal brief analysis

### Technical
- Technical documentation analysis
- API documentation extraction
- Code comment generation from specs
- Architecture decision records

## ⚡ Performance Tips

1. **Choose the right model**: Smaller models (phi, llama3.2:1b) for quick analysis, larger models (llama2:13b) for quality
2. **Optimize PDFs**: Text-based PDFs process much faster than scanned documents
3. **Limit page count**: The tool processes up to 100 pages; for longer documents, split into sections
4. **Close other applications**: Free up RAM for better performance
5. **Use SSD storage**: Faster model loading and processing

## 🔧 Customization

### Custom Analysis Templates

Create specialized analysis templates by modifying the prompt. Examples:

**Financial Analysis:**
```
Analyze this financial document and extract:
- Revenue figures and trends
- Cost structures
- Profit margins
- Key financial ratios
- Risk factors mentioned
- Future projections
```

**Medical Records:**
```
Summarize this medical document including:
- Patient symptoms
- Diagnoses
- Treatment plans
- Medications prescribed
- Follow-up recommendations
- Critical findings
```

**Security Consultant Focused:**
```
Analyze this document from a security perspective:
- Identify security requirements
- List vulnerabilities or risks mentioned
- Extract compliance requirements
- Note security controls discussed
- Highlight security recommendations
- Flag any security gaps
```

## 🌐 Language Support

While the interface is in English, the LLM models support multiple languages for document analysis. You can customize prompts in different languages:

**Spanish:**
```
Analiza este documento PDF y proporciona un resumen completo...
```

**French:**
```
Analysez ce document PDF et fournissez un résumé complet...
```

**German:**
```
Analysieren Sie dieses PDF-Dokument und erstellen Sie eine umfassende Zusammenfassung...
```

## ⭐ Star History

If you find this project useful, please consider giving it a star on GitHub!

## 📈 Changelog

### v1.0.0 (2024-01)
- Initial release
- Automated setup for Ubuntu/WSL
- Support for multiple LLM models (Llama, Mistral, Phi)
- Security hardening with input validation and rate limiting
- Comprehensive logging system
- WSL network compatibility
- Beautiful responsive web interface
- Drag-and-drop PDF upload
- Customizable analysis prompts
- Automatic file cleanup
- One-click Ollama installation

---

## 📝 FAQ

**Q: Does this work on Windows?**  
A: Yes, via WSL2 (Windows Subsystem for Linux). Native Windows support is not currently available but is on the roadmap.

**Q: Can I use this offline?**  
A: Yes! After initial setup and model download, the entire system works completely offline.

**Q: How much disk space do I need?**  
A: At minimum 10GB: ~2GB for Ollama, 4-8GB for models, rest for system and working space.

**Q: Is my data secure?**  
A: Yes. All processing happens locally on your machine. No data is sent to external servers.

**Q: Can I process multiple PDFs at once?**  
A: Currently one at a time. Batch processing is planned for a future release.

**Q: Which model should I choose?**  
A: For most users, `llama2` (7B) offers the best balance. Use `phi` or `llama3.2:1b` for speed, `llama2:13b` for quality.

**Q: Can I use custom/fine-tuned models?**  
A: Yes! Any model compatible with Ollama can be used. Import it with `ollama pull <model-name>`.

**Q: Does it work on ARM/Apple Silicon?**  
A: Not officially tested, but Ollama supports ARM. May work on Apple Silicon via Rosetta or native ARM build.

---

**Made with ❤️ for the open-source community**

**Privacy-First | Security-Focused | User-Friendly**
