# Phase 1 Implementation Plan: Core Infrastructure

**Target:** Week 1 - Foundation for Advanced Optimization  
**Goal:** Replace hardcoded output management with intelligent cache-based system  
**Status:** Ready to implement immediately  

---

## 🎯 **IMMEDIATE PRIORITIES**

### **Priority 1: Cache Manager Foundation**
Replace the current chaotic output system with a structured cache manager that eliminates hardcoded folder names and provides the foundation for all future optimizations.

### **Priority 2: Flexible Output System**
Transform the rigid output utilities into a modular system that supports multiple formats and prevents data loss.

---

## 📋 **DETAILED IMPLEMENTATION TASKS**

### **Task 1: Create Cache Manager Infrastructure**

**File:** `src/core/cache_manager.py`

```python
"""
Cache Manager for Lexi Owl Research System
Handles all output organization, deduplication, and session management.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import hashlib
import json
import uuid
from dataclasses import dataclass, asdict
from .config import AgentConfig

@dataclass
class RunMetadata:
    """Metadata for a research run"""
    run_id: str
    user_question: str
    created_at: datetime
    status: str  # 'running', 'completed', 'error'
    config: Dict
    iterations_count: int = 0
    sources_count: int = 0
    total_duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RunMetadata':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

@dataclass
class CachedSource:
    """Cached source content with metadata"""
    url: str
    content: str
    method: str
    scraped_at: datetime
    url_hash: str
    
    def is_stale(self, ttl_hours: int = 24) -> bool:
        """Check if cached content is stale"""
        age_hours = (datetime.now() - self.scraped_at).total_seconds() / 3600
        return age_hours > ttl_hours
    
    def save(self, source_path: Path) -> None:
        """Save cached source to disk"""
        # Save content
        content_file = source_path / "content.md"
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(self.content)
        
        # Save metadata
        metadata = {
            'url': self.url,
            'method': self.method,
            'scraped_at': self.scraped_at.isoformat(),
            'url_hash': self.url_hash
        }
        metadata_file = source_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    @classmethod
    def load(cls, source_path: Path) -> Optional['CachedSource']:
        """Load cached source from disk"""
        try:
            # Load metadata
            metadata_file = source_path / "metadata.json"
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load content
            content_file = source_path / "content.md"
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return cls(
                url=metadata['url'],
                content=content,
                method=metadata['method'],
                scraped_at=datetime.fromisoformat(metadata['scraped_at']),
                url_hash=metadata['url_hash']
            )
        except Exception:
            return None

class CacheManager:
    """Central cache management for all research operations"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.runs_dir = self.cache_dir / "runs"
        self.sources_dir = self.cache_dir / "sources"
        self.index_dir = self.cache_dir / "index"
        
        # Ensure directories exist
        self.cache_dir.mkdir(exist_ok=True)
        self.runs_dir.mkdir(exist_ok=True)
        self.sources_dir.mkdir(exist_ok=True)
        self.index_dir.mkdir(exist_ok=True)
    
    def create_run(self, user_question: str, config: AgentConfig) -> 'RunSession':
        """Create a new research run with unique identifier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = self._generate_slug(user_question)
        run_id = f"{timestamp}_{slug}"
        
        # Ensure uniqueness
        run_path = self.runs_dir / run_id
        counter = 1
        while run_path.exists():
            run_id = f"{timestamp}_{slug}_{counter}"
            run_path = self.runs_dir / run_id
            counter += 1
        
        run_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (run_path / "iterations").mkdir(exist_ok=True)
        (run_path / "sources").mkdir(exist_ok=True)
        
        # Create metadata
        metadata = RunMetadata(
            run_id=run_id,
            user_question=user_question,
            created_at=datetime.now(),
            status="initialized",
            config=asdict(config)
        )
        
        return RunSession(run_id, run_path, metadata, self)
    
    def get_cached_source(self, url: str) -> Optional[CachedSource]:
        """Retrieve cached content for a URL"""
        url_hash = self._hash_url(url)
        source_path = self.sources_dir / url_hash
        
        if source_path.exists():
            return CachedSource.load(source_path)
        return None
    
    def cache_source(self, url: str, content: str, method: str) -> CachedSource:
        """Cache scraped content with metadata"""
        url_hash = self._hash_url(url)
        source_path = self.sources_dir / url_hash
        source_path.mkdir(parents=True, exist_ok=True)
        
        cached_source = CachedSource(
            url=url,
            content=content,
            method=method,
            scraped_at=datetime.now(),
            url_hash=url_hash
        )
        cached_source.save(source_path)
        return cached_source
    
    def _generate_slug(self, user_question: str) -> str:
        """Generate a clean slug from user question"""
        # Use existing slug generation logic from agent.py
        from ..llm.providers import simple_agentic_prompt
        from .prompts import SYSTEM_PROMPT_SLUG
        
        try:
            base_slug = simple_agentic_prompt(
                user_prompt=f"User question: {user_question}",
                model_name="llama-3.3-70b-versatile",
                temperature=0.0,
                system_prompt=SYSTEM_PROMPT_SLUG
            ).strip().replace("/", "_")
            
            # Cleanup slug
            import re
            base_slug = re.sub(r'[^a-z0-9_]', '', base_slug.lower().replace(' ', '_'))
            base_slug = re.sub(r'_+', '_', base_slug).strip('_')
            base_slug = base_slug[:40]  # Shorter for timestamp prefix
            
            if not base_slug:
                base_slug = "research_query"
                
            return base_slug
        except Exception:
            # Fallback to simple hash-based slug
            return hashlib.sha256(user_question.encode()).hexdigest()[:16]
    
    def _hash_url(self, url: str) -> str:
        """Generate consistent hash for URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

class RunSession:
    """Represents an active research session"""
    
    def __init__(self, run_id: str, run_path: Path, metadata: RunMetadata, cache_manager: CacheManager):
        self.run_id = run_id
        self.run_path = run_path
        self.metadata = metadata
        self.cache_manager = cache_manager
        self.iterations = []
        self.sources = {}
        
    def save_metadata(self) -> None:
        """Save current metadata to disk"""
        metadata_file = self.run_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata.to_dict(), f, indent=2)
    
    def add_iteration(self, iteration_num: int, query: str, results: List[Dict], answer: str) -> None:
        """Add iteration data to the session"""
        iteration_dir = self.run_path / "iterations" / f"{iteration_num:02d}"
        iteration_dir.mkdir(exist_ok=True)
        
        # Save query
        query_file = iteration_dir / "query.md"
        with open(query_file, 'w', encoding='utf-8') as f:
            f.write(f"# Search Query {iteration_num}\n\n{query}\n")
        
        # Save search results
        results_file = iteration_dir / "results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Save answer
        answer_file = iteration_dir / "answer.md"
        with open(answer_file, 'w', encoding='utf-8') as f:
            f.write(f"# Answer for Query {iteration_num}\n\n{answer}\n")
        
        self.iterations.append({
            'iteration': iteration_num,
            'query': query,
            'results_count': len(results),
            'answer_length': len(answer)
        })
        
        self.metadata.iterations_count = len(self.iterations)
        self.save_metadata()
    
    def save_final_answer(self, final_answer: str) -> None:
        """Save the final synthesized answer"""
        final_file = self.run_path / "final_answer.md"
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(f"# Research Results: {self.metadata.user_question}\n\n")
            f.write(f"**Generated:** {self.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Run ID:** {self.run_id}\n")
            f.write(f"**Iterations:** {self.metadata.iterations_count}\n")
            f.write(f"**Sources:** {self.metadata.sources_count}\n\n")
            f.write("---\n\n")
            f.write(final_answer)
    
    def complete(self, final_answer: str) -> None:
        """Mark session as completed and save final results"""
        self.save_final_answer(final_answer)
        self.metadata.status = "completed"
        self.metadata.total_duration_seconds = (datetime.now() - self.metadata.created_at).total_seconds()
        self.save_metadata()
        
        print(f"✅ Research completed! Results saved to: {self.run_path}")
        print(f"📊 Run ID: {self.run_id}")
        print(f"⏱️  Duration: {self.metadata.total_duration_seconds:.1f} seconds")
        print(f"🔍 Iterations: {self.metadata.iterations_count}")
        print(f"📄 Sources: {self.metadata.sources_count}")
```

### **Task 2: Update Agent to Use Cache Manager**

**File:** `src/core/agent.py` (modifications)

```python
# Add imports at the top
from .cache_manager import CacheManager, RunSession

# Modify research_workflow function
def research_workflow(user_question: str, config: AgentConfig = None) -> str:
    """
    Main entry point for multi-iteration research workflow.
    Now uses intelligent cache management instead of hardcoded folders.
    """
    if config is None:
        from .config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
    
    # Initialize cache manager
    cache_manager = CacheManager()
    
    # Create new research session
    session = cache_manager.create_run(user_question, config)
    
    print(f"🚀 Starting research session: {session.run_id}")
    print(f"📁 Output location: {session.run_path}")
    
    try:
        # Generate search queries
        queries = _generate_search_queries(user_question, config)
        
        # Execute iterations with cache-aware processing
        answers = []
        already_scraped_urls = set()
        
        for i in range(config.num_iterations):
            print(f"\n--- Iteration {i+1} ---")
            query = queries[i]
            
            # Execute iteration with caching
            answer, search_results, urls_this_iter, warnings = _execute_iteration_with_cache(
                query=query,
                session=session,
                already_scraped_urls=already_scraped_urls,
                config=config
            )
            
            # Save iteration data
            session.add_iteration(i+1, query, search_results, answer)
            
            answers.append(answer)
            already_scraped_urls.update(urls_this_iter)
            
            print(f"\nAnswer preview: {answer[:200]}...")
            if warnings:
                for warning in warnings:
                    print(f"⚠️  {warning}")
        
        # Synthesize final answer
        final_answer = _synthesis_step(user_question, answers, config)
        
        # Complete session
        session.complete(final_answer)
        
        return final_answer
        
    except Exception as e:
        session.metadata.status = "error"
        session.save_metadata()
        print(f"❌ Research failed: {e}")
        raise

def _execute_iteration_with_cache(
    query: str,
    session: RunSession,
    already_scraped_urls: set,
    config: AgentConfig
) -> tuple:
    """Execute iteration with intelligent caching"""
    
    # Search step
    search_results = _search_step(query, config)
    if not search_results:
        return "No search results found.", [], [], ["No search results found."]
    
    # Cache-aware scraping
    sources, urls_this_iter, warnings = _scrape_step_with_cache(
        search_results, already_scraped_urls, session, config
    )
    
    if not sources:
        return "No content could be scraped.", search_results, urls_this_iter, warnings
    
    # Generate answer
    answer = _llm_answer_step(query, sources, config)
    
    return answer, search_results, urls_this_iter, warnings

def _scrape_step_with_cache(
    search_results: List[Dict], 
    already_scraped_urls: set, 
    session: RunSession, 
    config: AgentConfig
) -> tuple:
    """Scrape with intelligent caching to avoid redundant work"""
    
    warnings = []
    aggregated_content = []
    urls_this_iter = []
    
    # Filter already scraped URLs
    filtered_results = [
        item for item in search_results 
        if item.get('url') and item.get('url') not in already_scraped_urls
    ]
    
    if not filtered_results:
        return "", [], ["All search results already scraped."]
    
    for item in filtered_results:
        url = item.get('url')
        title = item.get('title', 'Untitled')
        
        if not url:
            continue
            
        urls_this_iter.append(url)
        
        # Check cache first
        cached_source = session.cache_manager.get_cached_source(url)
        
        if cached_source and not cached_source.is_stale(24):  # 24 hour TTL
            print(f"✅ Using cached content for: {title}")
            content = cached_source.content
            method = f"{cached_source.method} (cached)"
        else:
            print(f"🔄 Scraping fresh content for: {title}")
            try:
                # Use existing scraping logic but save to cache
                from ..utils.scraper import scrape_single_url_content
                content = scrape_single_url_content(
                    url, 
                    method="llm-reader",
                    jina_api_key=config.jina_api_key,
                    delay=config.delay
                )
                
                if content:
                    # Cache the content
                    session.cache_manager.cache_source(url, content, "llm-reader")
                    method = "llm-reader (fresh)"
                else:
                    warnings.append(f"Failed to scrape content from {url}")
                    continue
                    
            except Exception as e:
                warnings.append(f"Error scraping {url}: {e}")
                continue
        
        # Add to aggregated content
        header = f"# {title}\n\n**Source:** {url}\n**Method:** {method}\n\n---\n\n"
        aggregated_content.append(header + content)
        
        # Update session source count
        session.metadata.sources_count += 1
    
    if not aggregated_content:
        return "", urls_this_iter, ["No content could be scraped from any source."]
    
    sources_text = "\n\n---\n\n".join(aggregated_content)
    return sources_text, urls_this_iter, warnings
```

### **Task 3: Update Configuration for Cache Settings**

**File:** `src/core/config.py` (additions)

```python
@dataclass
class AgentConfig:
    """
    Central configuration for the agentic workflows.
    """
    model_name: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    temperature: float = 0.2
    num_iterations: int = 3
    num_search_results_per_iteration: int = 3
    output_dir: Optional[str] = None  # DEPRECATED - now handled by cache manager
    jina_api_key: Optional[str] = None
    youtube_transcript_languages: List[str] = field(default_factory=lambda: ['en', 'pt'])
    delay: float = 1.0
    
    # NEW: Cache settings
    cache_dir: str = ".cache"
    cache_ttl_hours: int = 24
    enable_caching: bool = True
    
    def __post_init__(self):
        """Validate configuration and show deprecation warnings"""
        if self.output_dir is not None:
            print("⚠️  WARNING: output_dir is deprecated. Using intelligent cache management instead.")
```

### **Task 4: Update Main Entry Point**

**File:** `main.py` (modifications)

```python
from src.core.agent import research_workflow
from src.core.config import AgentConfig
import os

if __name__ == "__main__":
    print("🦉 Lexi Owl Research System - Advanced Cache Edition")
    
    # User query
    USER_QUERY = '''
        Preciso de investigar a aplicação móvel Citymapper para um projeto académico...
    '''
    
    # Configuration - NO MORE HARDCODED OUTPUT FOLDERS!
    config = AgentConfig(
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.1,
        num_iterations=15,
        num_search_results_per_iteration=5,
        # output_dir=OUTPUT_DIR_NAME,  # REMOVED - now automatic!
        jina_api_key=os.environ.get("JINA_API_KEY", "YOUR_JINA_API_KEY"),
        youtube_transcript_languages=['en', 'pt'],
        delay=1.0,
        cache_ttl_hours=24,  # Cache content for 24 hours
        enable_caching=True
    )
    
    # Check for required API keys
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY is not set in your environment.")
        exit(1)
    
    # Execute research workflow
    try:
        print(f"🔍 Research Question: {USER_QUERY[:100]}...")
        result = research_workflow(user_question=USER_QUERY, config=config)
        print("\n🎉 Research completed successfully!")
        print("📁 Check the .cache/runs/ directory for detailed results.")
        
    except Exception as e:
        print(f"❌ Research failed: {e}")
```

---

## 🧪 **TESTING STRATEGY**

### **Test 1: Basic Cache Functionality**
```bash
# Run the system twice with the same query
python main.py

# Verify:
# 1. .cache directory is created
# 2. Unique run folders are generated
# 3. Second run uses cached sources
```

### **Test 2: Cache Hit Verification**
```python
# Test script to verify caching works
from src.core.cache_manager import CacheManager

cache_manager = CacheManager()

# Test URL caching
test_url = "https://example.com"
cached = cache_manager.get_cached_source(test_url)
print(f"Cache hit: {cached is not None}")
```

### **Test 3: Output Structure Validation**
```bash
# Verify the new output structure
ls -la .cache/runs/
ls -la .cache/sources/
ls -la .cache/index/
```

---

## 📊 **SUCCESS CRITERIA**

### **Immediate Goals (End of Week 1)**
- ✅ No more hardcoded folder names in main.py
- ✅ Automatic unique run ID generation
- ✅ Basic source content caching working
- ✅ Clean .cache directory structure
- ✅ Backward compatibility maintained

### **Quality Metrics**
- **Zero overwrites**: Each run gets unique folder
- **Cache hits**: 50%+ for repeated URLs within TTL
- **Clean structure**: All outputs organized in .cache
- **Error handling**: Graceful fallbacks for cache failures

---

## 🚀 **NEXT STEPS AFTER PHASE 1**

Once Phase 1 is complete, we'll have:
1. **Solid foundation** for all future optimizations
2. **Elimination** of hardcoded output chaos
3. **Basic caching** infrastructure in place
4. **Clean separation** between runs and sources

**Phase 2 Preview:**
- Query similarity detection
- Advanced deduplication
- Performance monitoring
- Incremental research capabilities

---

## 💡 **IMPLEMENTATION NOTES**

### **Backward Compatibility**
- Existing code continues to work
- Deprecation warnings for old patterns
- Gradual migration path

### **Error Handling**
- Cache failures fall back to normal operation
- Corrupted cache entries are automatically cleaned
- Session recovery for interrupted runs

### **Performance**
- Minimal overhead for cache operations
- Async-friendly design
- Memory-efficient for large content

**Ready to implement immediately!** 🚀 