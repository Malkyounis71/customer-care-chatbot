import json
import hashlib
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
import numpy as np
from loguru import logger
from app.config.settings import settings
import re

class RAGEngine:
    """Enhanced RAG engine with better retrieval and answer generation"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=30
        )
        self._init_collection()
        
        # Query expansion keywords for better retrieval
        self.query_expansions = {
            'price': ['pricing', 'cost', 'plan', 'subscription', 'fee'],
            'product': ['solution', 'service', 'platform', 'tool', 'software'],
            'support': ['help', 'assistance', 'technical', 'customer service'],
            'feature': ['capability', 'function', 'functionality', 'tool']
        }
    
    def _init_collection(self):
        """Initialize Qdrant collection with proper configuration"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if settings.QDRANT_COLLECTION not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=1000
                    )
                )
                logger.info(f"✅ Created collection: {settings.QDRANT_COLLECTION}")
            else:
                logger.info(f"✅ Collection exists: {settings.QDRANT_COLLECTION}")
                
        except Exception as e:
            logger.error(f"❌ Collection initialization error: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with error handling"""
        try:
            embedding = self.embedding_model.encode(text, show_progress_bar=False).tolist()
            return embedding
        except Exception as e:
            logger.error(f"❌ Embedding generation error: {e}")
            return np.random.randn(settings.QDRANT_VECTOR_SIZE).tolist()
    
    def index_document(self, document: Dict, chunk_size: int = 400, chunk_overlap: int = 50):
        """Index document with intelligent chunking"""
        try:
            content = document.get('content', '')
            metadata = document.get('metadata', {})
            
            if not content:
                logger.warning(f"⚠️ Empty content: {metadata.get('title', 'Unknown')}")
                return
            
            logger.info(f"📄 Indexing: {metadata.get('title', 'Unknown')}")
            
            # Intelligent chunking based on content structure
            chunks = self._chunk_content(content, chunk_size, chunk_overlap)
            logger.info(f"   Created {len(chunks)} chunks")
            
            points = []
            for i, chunk in enumerate(chunks):
                if not chunk.strip() or len(chunk.strip()) < 50:
                    continue
                
                embedding = self.generate_embedding(chunk)
                
                # Create unique deterministic ID
                chunk_hash = hashlib.md5(
                    f"{metadata.get('filename', 'doc')}_{i}".encode()
                ).hexdigest()
                
                # Enhanced payload with better metadata
                payload = {
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "title": metadata.get('title', 'Unknown'),
                    "category": metadata.get('category', 'general'),
                    "type": metadata.get('type', 'general'),
                    "source": metadata.get('source', 'unknown'),
                    "filename": metadata.get('filename', 'unknown'),
                    "tags": self._extract_tags(chunk),
                    "char_count": len(chunk)
                }
                
                point = models.PointStruct(
                    id=chunk_hash,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # Batch upload for efficiency
            if points:
                batch_size = 100
                for i in range(0, len(points), batch_size):
                    batch = points[i:i + batch_size]
                    self.qdrant_client.upsert(
                        collection_name=settings.QDRANT_COLLECTION,
                        wait=True,
                        points=batch
                    )
                logger.info(f"✅ Indexed {len(points)} chunks: {metadata.get('title')}")
            
        except Exception as e:
            logger.error(f"❌ Indexing error: {e}")
            import traceback
            traceback.print_exc()
    
    def _chunk_content(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Intelligent content chunking with structure preservation"""
        if not text or len(text) < chunk_size:
            return [text] if text else []
        
        # Strategy 1: Split by markdown headers (preserves document structure)
        header_chunks = self._chunk_by_headers(text)
        
        # If we got reasonable chunks, use them
        if header_chunks and all(len(c) <= chunk_size * 1.5 for c in header_chunks):
            return header_chunks
        
        # Strategy 2: Split by paragraphs
        paragraph_chunks = self._chunk_by_paragraphs(text, chunk_size, overlap)
        if paragraph_chunks:
            return paragraph_chunks
        
        # Strategy 3: Split by sentences (fallback)
        return self._chunk_by_sentences(text, chunk_size, overlap)
    
    def _chunk_by_headers(self, text: str) -> List[str]:
        """Chunk by markdown headers"""
        # Split on headers (##, ###)
        sections = re.split(r'(?=\n#{2,3}\s+)', text)
        chunks = []
        
        for section in sections:
            section = section.strip()
            if section:
                chunks.append(section)
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk by paragraphs with overlap"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_sentences(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk by sentences with overlap"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Add overlap from previous chunk
                if overlap > 0 and chunks:
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + sentence + " "
                else:
                    current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        tags = []
        text_lower = text.lower()
        
        # Product tags
        products = {
            'enterprise_suite': ['cob enterprise suite', 'enterprise suite'],
            'analytics_pro': ['cob analytics pro', 'analytics pro'],
            'cloud_services': ['cob cloud services', 'cloud services'],
            'mobile_app': ['cob mobile app', 'mobile app']
        }
        
        for tag, keywords in products.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        # Category tags
        categories = {
            'pricing': ['pricing', 'price', 'cost', '$', 'plan', 'subscription'],
            'features': ['feature', 'capability', 'function', 'tool'],
            'support': ['support', 'help', 'contact', 'assistance'],
            'integration': ['integration', 'api', 'connect', 'integrate'],
            'security': ['security', 'encryption', 'compliance', 'gdpr', 'hipaa']
        }
        
        for tag, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def search(self, query: str, top_k: int = 10, score_threshold: float = 0.3, 
               filter_category: Optional[str] = None) -> List[Dict]:
        """Enhanced search with query expansion and filtering"""
        try:
            if not query or not query.strip():
                logger.warning("⚠️ Empty query")
                return []
            
            # Expand query for better retrieval
            expanded_query = self._expand_query(query)
            logger.info(f"🔍 Original: '{query}'")
            if expanded_query != query:
                logger.info(f"   Expanded: '{expanded_query}'")
            
            # Generate embedding
            query_embedding = self.generate_embedding(expanded_query)
            
            # Build filter if category specified
            query_filter = None
            if filter_category:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=filter_category)
                        )
                    ]
                )
            
            # Search with enhanced parameters
            search_result = self.qdrant_client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=query_embedding,
                limit=top_k * 2,  # Get more results for re-ranking
                score_threshold=score_threshold * 0.8,  # Lower threshold initially
                with_payload=True,
                with_vectors=False,
                query_filter=query_filter,
                search_params=models.SearchParams(
                    hnsw_ef=128,
                    exact=False
                )
            ).points
            
            # Process and re-rank results
            results = self._process_search_results(search_result, query, score_threshold)
            
            # Deduplicate by content similarity
            results = self._deduplicate_results(results)
            
            # Limit to top_k
            results = results[:top_k]
            
            logger.info(f"✅ Found {len(results)} results (threshold: {score_threshold})")
            
            # Log top results
            for i, result in enumerate(results[:3]):
                logger.info(f"   {i+1}. {result['metadata']['title']} (score: {result['score']:.3f})")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms for better retrieval"""
        query_lower = query.lower()
        expanded_terms = [query]
        
        for term, expansions in self.query_expansions.items():
            if term in query_lower:
                # Add expansion terms that aren't already in the query
                for expansion in expansions:
                    if expansion not in query_lower:
                        expanded_terms.append(expansion)
                        break  # Add just one expansion per term
        
        return ' '.join(expanded_terms)
    
    def _process_search_results(self, hits: List, query: str, threshold: float) -> List[Dict]:
        """Process and enhance search results"""
        results = []
        query_lower = query.lower()
        
        for hit in hits:
            # Base score
            score = hit.score
            
            # Boost score if query terms appear in content
            content_lower = hit.payload.get('content', '').lower()
            query_terms = query_lower.split()
            term_matches = sum(1 for term in query_terms if term in content_lower)
            if term_matches > 0:
                score *= (1 + 0.1 * term_matches)  # Boost by 10% per matched term
            
            # Boost if query terms in title
            title_lower = hit.payload.get('title', '').lower()
            if any(term in title_lower for term in query_terms):
                score *= 1.2
            
            # Apply final threshold
            if score < threshold:
                continue
            
            result = {
                'content': hit.payload.get('content', ''),
                'metadata': {
                    'title': hit.payload.get('title', 'Unknown'),
                    'category': hit.payload.get('category', 'general'),
                    'type': hit.payload.get('type', 'general'),
                    'source': hit.payload.get('source', 'unknown'),
                    'filename': hit.payload.get('filename', 'unknown'),
                    'chunk_index': hit.payload.get('chunk_index', 0),
                    'tags': hit.payload.get('tags', [])
                },
                'score': min(score, 1.0),  # Cap at 1.0
                'source': hit.payload.get('source', 'Unknown'),
                'category': hit.payload.get('category', 'general')
            }
            results.append(result)
        
        # Sort by enhanced score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar results"""
        unique_results = []
        seen_content = set()
        
        for result in results:
            # Create content signature (first 200 chars)
            content_sig = result['content'][:200].strip().lower()
            content_hash = hash(content_sig)
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def generate_answer(self, query: str, context: List[Dict], max_length: int = 2000) -> str:
        """Generate comprehensive answer from search results"""
        if not context:
            return self._no_results_response(query)
        
        logger.info(f"🤖 Generating answer for: '{query}'")
        logger.info(f"   Using {len(context)} context chunks")
        
        # Group results by document
        grouped = self._group_results_by_document(context)
        
        # Build answer
        answer_parts = []
        
        # Add context-aware introduction
        intro = self._generate_intro(query)
        if intro:
            answer_parts.append(intro)
        
        # Add content from each document
        for title, results in list(grouped.items())[:3]:  # Max 3 documents
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Add document title
            answer_parts.append(f"\n**{title}:**")
            
            # Add best chunks (max 2 per document)
            for result in results[:2]:
                content = self._clean_content(result['content'])
                if content:
                    answer_parts.append(f"• {content}")
        
        # Combine answer
        answer = '\n'.join(answer_parts)
        
        # Truncate if too long
        if len(answer) > max_length:
            answer = answer[:max_length-100] + "\n\n*[Truncated for brevity]*"
        
        # Add helpful closing
        answer += self._generate_closing(query)
        
        logger.info(f"✅ Generated answer: {len(answer)} chars")
        return answer
    
    def _group_results_by_document(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group results by source document"""
        grouped = {}
        for result in results:
            title = result['metadata']['title']
            if title not in grouped:
                grouped[title] = []
            grouped[title].append(result)
        return grouped
    
    def _generate_intro(self, query: str) -> str:
        """Generate contextual introduction"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['price', 'cost', 'pricing']):
            return "Here's our pricing information:\n"
        elif any(word in query_lower for word in ['product', 'service', 'solution']):
            return "Here's information about our products:\n"
        elif any(word in query_lower for word in ['support', 'help']):
            return "Here's our support information:\n"
        elif any(word in query_lower for word in ['feature', 'capability']):
            return "Here are the key features:\n"
        
        return "Here's what I found:\n"
    
    def _generate_closing(self, query: str) -> str:
        """Generate helpful closing"""
        return "\n\n*Would you like more details about any specific aspect?*"
    
    def _clean_content(self, content: str) -> str:
        """Clean and format content for display"""
        # Remove multiple spaces/newlines
        content = re.sub(r'\s+', ' ', content)
        
        # Remove markdown headers
        content = re.sub(r'#{1,6}\s+', '', content)
        
        # Preserve important formatting
        content = content.strip()
        
        return content
    
    def _no_results_response(self, query: str) -> str:
        """Generate helpful response when no results found"""
        return (
            "I couldn't find specific information about that in our knowledge base. "
            "Could you rephrase your question or ask about:\n"
            "• Our products and services\n"
            "• Pricing and plans\n"
            "• Technical support\n"
            "• Scheduling an appointment"
        )
    
    def get_collection_info(self) -> Dict:
        """Get collection statistics - compatible with different Qdrant versions."""
        try:
            info = self.qdrant_client.get_collection(settings.QDRANT_COLLECTION)
            
            # Extract available attributes safely
            result = {
                'points_count': getattr(info, 'points_count', 0),
                'status': getattr(info, 'status', 'unknown'),
                'collection_name': settings.QDRANT_COLLECTION
            }
            
            # Try different attribute names for vectors count
            vectors_count = 0
            if hasattr(info, 'vectors_count'):
                vectors_count = info.vectors_count
            elif hasattr(info, 'vectors'):
                vectors_count = info.vectors
            elif hasattr(info, 'config') and hasattr(info.config, 'params'):
                # Try to get from config
                vectors_count = getattr(info.config.params, 'vectors', 0)
            
            result['vectors_count'] = vectors_count
            
            # Add config info if available
            if hasattr(info, 'config'):
                config_dict = {}
                if hasattr(info.config, 'params'):
                    config_dict['params'] = str(info.config.params)
                if hasattr(info.config, 'optimizer_config'):
                    config_dict['optimizer_config'] = str(info.config.optimizer_config)
                result['config'] = config_dict
            
            logger.info(f"📊 Collection info: {result['points_count']} points, {vectors_count} vectors")
            return result
            
        except Exception as e:
            logger.error(f"❌ Collection info error: {e}")
            return {
                'error': str(e), 
                'points_count': 0, 
                'vectors_count': 0,
                'status': 'error',
                'collection_name': settings.QDRANT_COLLECTION
            }
        
    def clear_collection(self):
        """Clear all data from collection"""
        try:
            self.qdrant_client.delete_collection(settings.QDRANT_COLLECTION)
            self._init_collection()
            logger.info("✅ Collection cleared and recreated")
        except Exception as e:
            logger.error(f"❌ Clear error: {e}")