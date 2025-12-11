import os
import glob
from pathlib import Path
from typing import List, Dict
import re
from loguru import logger

class KnowledgeBaseLoader:
    """Load documents from knowledge base directory"""
    
    def __init__(self, data_dir: str = None):
        # Get the directory of THIS file (loader.py)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        
        if data_dir is None:
            # Look for sample_data relative to this file
            possible_paths = [
                os.path.join(current_file_dir, 'sample_data'),  # src/app/knowledge_base/sample_data
                os.path.join(current_file_dir, '..', 'sample_data'),  # src/app/sample_data
                os.path.join(current_file_dir, '..', '..', 'sample_data'),  # src/sample_data
                os.path.join(current_file_dir, '..', '..', '..', 'sample_data'),  # sample_data (project root)
                os.path.join(os.getcwd(), 'sample_data'),  # Current working directory
            ]
            
            for path in possible_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    self.data_dir = path
                    logger.info(f"✅ Found knowledge base directory: {path}")
                    break
            else:
                # Create in same directory as loader.py
                self.data_dir = os.path.join(current_file_dir, 'sample_data')
                os.makedirs(self.data_dir, exist_ok=True)
                logger.warning(f"⚠️  Created knowledge base directory: {self.data_dir}")
        else:
            self.data_dir = data_dir
        
        logger.info(f"📁 Knowledge base directory set to: {os.path.abspath(self.data_dir)}")
        
        # Verify it exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            logger.info(f"📁 Created directory: {self.data_dir}")
    
    def load_all_documents(self) -> List[Dict]:
        """Load all documents from the knowledge base directory"""
        documents = []
        
        logger.info(f"🔍 Looking for files in: {os.path.abspath(self.data_dir)}")
        
        # Find all markdown files
        md_files = glob.glob(os.path.join(self.data_dir, "*.md"))
        
        logger.info(f"📄 Found {len(md_files)} markdown files:")
        for md_file in md_files:
            logger.info(f"   • {os.path.basename(md_file)}")
        
        if not md_files:
            logger.warning("⚠️  No markdown files found! Creating sample files...")
            self._create_sample_files()
            md_files = glob.glob(os.path.join(self.data_dir, "*.md"))
        
        for md_file in md_files:
            try:
                # Extract filename without extension
                filename = Path(md_file).stem
                
                # Read markdown file
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse markdown frontmatter and content
                parsed_content = self._parse_markdown(content)
                
                # Create document with proper structure
                document = {
                    'content': parsed_content['content'],
                    'metadata': {
                        'id': filename,
                        'title': parsed_content.get('title', filename.replace('_', ' ').title()),
                        'category': parsed_content.get('category', 'general'),
                        'source': md_file,
                        'type': 'faq' if 'faq' in filename.lower() else 'product' if 'product' in filename.lower() else 'general',
                        'filename': filename,
                        'updated': parsed_content.get('updated', 'unknown')
                    }
                }
                
                documents.append(document)
                logger.info(f"✅ Loaded: {document['metadata']['title']} ({len(document['content'])} chars)")
                
            except Exception as e:
                logger.error(f"❌ Error loading {md_file}: {e}")
        
        logger.info(f"📚 Total documents loaded: {len(documents)}")
        
        # Log summary
        for doc in documents:
            title = doc['metadata']['title']
            category = doc['metadata']['category']
            content_length = len(doc['content'])
            logger.info(f"   📖 {title} - {category} ({content_length} chars)")
        
        return documents
    
    def _parse_markdown(self, markdown_text: str) -> Dict:
        """Parse markdown with frontmatter"""
        lines = markdown_text.strip().split('\n')
        
        metadata = {}
        content_lines = []
        
        # Check if there's frontmatter (between ---)
        if lines and lines[0].strip() == '---':
            in_frontmatter = True
            for line in lines[1:]:
                if line.strip() == '---':
                    in_frontmatter = False
                    continue
                
                if in_frontmatter and ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'').strip()
                elif not in_frontmatter:
                    content_lines.append(line)
        else:
            content_lines = lines
        
        # Convert markdown content to plain text
        plain_text = self._markdown_to_text('\n'.join(content_lines))
        
        return {
            **metadata,
            'content': plain_text
        }
    
    def _markdown_to_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text - SIMPLIFIED VERSION"""
        if not markdown_text:
            return ""
        
        # remove excessive whitespace
        text = markdown_text
        
        # Remove frontmatter if present
        text = re.sub(r'^---.*?---\n', '', text, flags=re.DOTALL)
        
        # Basic cleanup
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r' {2,}', ' ', text)      # Multiple spaces to single
        
        return text.strip()
    
    def _create_sample_files(self):
        """Create sample markdown files if none exist"""
        sample_dir = self.data_dir
        
        # Simple sample files
        products_content = """COB Enterprise Suite: Business management platform. Features: Financial management, CRM, HR, inventory. Pricing: $99/month.
COB Analytics Pro: Data analytics platform. Features: Real-time dashboards, predictive analytics. Pricing: $149/month."""
        
        faqs_content = """Business hours: Monday-Friday 9AM-6PM EST. Contact: support@cobcompany.com.
Products: COB Enterprise Suite and COB Analytics Pro.
Support: 24/7 support available."""
        
        with open(os.path.join(sample_dir, "products.md"), "w", encoding="utf-8") as f:
            f.write(products_content)
        
        with open(os.path.join(sample_dir, "faqs.md"), "w", encoding="utf-8") as f:
            f.write(faqs_content)
        
        logger.info(f"📝 Created sample files in: {sample_dir}")