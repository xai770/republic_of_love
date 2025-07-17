# TY System Architecture
## Complete Technical Specification v1.0

**Vision:** Amazon-scale career management platform powered by local AI  
**Motto:** "Enterprise-grade AI on gaming hardware"  

---

## System Overview

### Core Philosophy
- **Local AI First**: Gaming laptops outperform enterprise cloud solutions
- **Multi-User, Multi-Site**: Federated deployment across regions/organizations
- **Feedback-Driven**: User interactions improve matching algorithms
- **Cost-Optimized**: Human→AI→Automation progression based on confidence

---

## Data Architecture

### Database Design (PostgreSQL + Redis)

#### Core Tables (PostgreSQL)
```sql
-- Multi-site deployment support
CREATE TABLE sites (
    site_id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User management with site affiliation
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    primary_site_id UUID REFERENCES sites(site_id),
    profile JSONB,
    cv_data JSONB, -- Structured CV with 5D skills
    preferences JSONB, -- Blacklists, preferences, filters
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Job storage with extracted intelligence
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(site_id),
    external_id VARCHAR(100), -- Original job board ID
    company VARCHAR(200) NOT NULL,
    title VARCHAR(500) NOT NULL,
    location JSONB,
    raw_content TEXT,
    extracted_skills JSONB, -- 5D skill structure
    processing_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(company, site_id, created_at),
    INDEX(title, company)
);

-- User feedback and learning system
CREATE TABLE user_feedback (
    feedback_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    job_id UUID REFERENCES jobs(job_id),
    feedback_type VARCHAR(50), -- 'blacklist', 'applied', 'rejected', 'outcome'
    feedback_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(user_id, created_at),
    INDEX(job_id, feedback_type)
);

-- Match history and outcomes
CREATE TABLE match_history (
    match_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    job_id UUID REFERENCES jobs(job_id),
    match_score DECIMAL(4,3), -- 0.000 to 1.000
    bucket_scores JSONB, -- Individual bucket scores
    user_action VARCHAR(50), -- 'applied', 'rejected', 'ignored'
    outcome VARCHAR(50), -- 'hired', 'rejected', 'no_response'
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(user_id, match_score DESC),
    INDEX(job_id, match_score DESC)
);

-- Application tracking
CREATE TABLE applications (
    application_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    job_id UUID REFERENCES jobs(job_id),
    cover_letter TEXT,
    application_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50), -- 'sent', 'viewed', 'interview', 'offer', 'rejected'
    notes TEXT,
    INDEX(user_id, application_date DESC)
);
```

#### Caching Layer (Redis)
```python
# Hot data patterns
REDIS_PATTERNS = {
    # User data (TTL: 1 hour)
    "user:{user_id}:preferences": "JSONB user preferences",
    "user:{user_id}:cv": "Structured CV data",
    "user:{user_id}:blacklist": "Set of blacklisted companies",
    
    # Job data (TTL: 24 hours)  
    "job:{job_id}:skills": "Extracted 5D skills",
    "job:{job_id}:metadata": "Processing metadata",
    
    # Matching cache (TTL: 6 hours)
    "matches:{user_id}:recent": "Recent match scores",
    "matches:{user_id}:applied": "Set of applied job_ids",
    
    # System performance (TTL: 1 hour)
    "stats:site:{site_id}:daily": "Daily processing stats",
    "pipeline:status": "Current pipeline status"
}
```

---

## Skill Extraction Pipeline

### Enhanced 5D Framework
```json
{
  "technical_skills": [
    {
      "skill": "Python Programming",
      "competency": "Advanced", // Beginner|Basic|Intermediate|Advanced|Expert
      "experience": "5+ years",  // Entry-level|2-5 years|5+|Required
      "criticality": "HIGH",     // MANDATORY|HIGH|MEDIUM|LOW
      "synonyms": ["Python3", "Py", "Python Development"]
    }
  ],
  "domain_expertise": [...],
  "methodology_frameworks": [...], 
  "collaboration_communication": [...],
  "experience_qualifications": [...]
}
```

### Processing Workflow
```python
# Job processing pipeline
class JobProcessor:
    def process_job(self, raw_job_text):
        # Phase 1: Content extraction
        structured_data = self.extract_metadata(raw_job_text)
        
        # Phase 2: AI-powered skill extraction  
        skills = self.extract_skills_5d(raw_job_text)
        
        # Phase 3: Validation and enhancement
        validated_skills = self.validate_skills(skills)
        
        # Phase 4: Storage and indexing
        job_id = self.store_job(structured_data, validated_skills)
        
        return job_id
```

---

## CV-Job Matching Algorithm

### Core Matching Logic
```python
class MatchingEngine:
    def __init__(self):
        self.bucket_weights = {
            'technical_skills': 0.30,
            'domain_expertise': 0.25, 
            'methodology_frameworks': 0.20,
            'collaboration_communication': 0.15,
            'experience_qualifications': 0.10
        }
        
        self.criticality_weights = {
            'MANDATORY': 5,
            'HIGH': 3,
            'MEDIUM': 2, 
            'LOW': 1
        }
    
    def calculate_match(self, job_skills, cv_skills, user_preferences):
        # Apply pre-filtering
        if self.is_filtered_out(job, user_preferences):
            return None
            
        bucket_scores = {}
        for bucket in self.bucket_weights.keys():
            bucket_scores[bucket] = self.score_bucket(
                job_skills[bucket], 
                cv_skills[bucket]
            )
        
        overall_score = self.calculate_weighted_score(bucket_scores)
        
        return {
            'overall_score': overall_score,
            'bucket_scores': bucket_scores,
            'recommendation': self.get_recommendation(overall_score),
            'missing_skills': self.identify_gaps(job_skills, cv_skills)
        }
```

### Skill Matching Rules
```python
def match_skills(job_skill, cv_skill):
    """Multi-level skill matching with synonym support"""
    
    # Level 1: Exact match
    if job_skill['skill'].lower() == cv_skill['skill'].lower():
        return {'type': 'exact', 'confidence': 1.0}
    
    # Level 2: Synonym matching
    job_terms = [job_skill['skill']] + job_skill['synonyms']
    cv_terms = [cv_skill['skill']] + cv_skill['synonyms']
    
    for j_term in job_terms:
        for c_term in cv_terms:
            if j_term.lower() == c_term.lower():
                return {'type': 'synonym', 'confidence': 0.9}
    
    # Level 3: Fuzzy matching (future enhancement)
    # similarity = fuzzy_match(job_skill['skill'], cv_skill['skill'])
    # if similarity > 0.8:
    #     return {'type': 'fuzzy', 'confidence': similarity}
    
    return None
```

---

## User Feedback Integration

### Feedback Types
```python
FEEDBACK_TYPES = {
    'company_blacklist': {
        'description': 'User never wants jobs from this company',
        'effect': 'Pre-filter jobs before matching',
        'persistence': 'Permanent until user removes'
    },
    
    'role_preference': {
        'description': 'User prefers/avoids certain role types',
        'effect': 'Boost/penalty in matching score',
        'persistence': 'Learning over time'
    },
    
    'application_outcome': {
        'description': 'Result of job application',
        'effect': 'ML training data for future matching',
        'persistence': 'Historical data for analysis'
    },
    
    'location_constraint': {
        'description': 'Geographic or remote work preferences',
        'effect': 'Hard filter in job selection',
        'persistence': 'User-controlled'
    }
}
```

### Learning System
```python
class FeedbackProcessor:
    def process_feedback(self, user_id, job_id, feedback_type, data):
        # Store feedback
        self.store_feedback(user_id, job_id, feedback_type, data)
        
        # Update user profile
        if feedback_type == 'company_blacklist':
            self.update_blacklist(user_id, data['company'])
        
        # Trigger ML retraining (future)
        if feedback_type == 'application_outcome':
            self.queue_model_update(user_id, job_id, data)
        
        # Update Redis cache
        self.invalidate_user_cache(user_id)
```

---

## Multi-Site Architecture

### Site Management
```python
class SiteManager:
    def __init__(self):
        self.sites = {
            'ty-eu': {'region': 'Europe', 'languages': ['en', 'de', 'fr']},
            'ty-us': {'region': 'North America', 'languages': ['en', 'es']},
            'ty-asia': {'region': 'Asia Pacific', 'languages': ['en', 'ja', 'zh']}
        }
    
    def route_user(self, user_location):
        """Route users to optimal site based on location"""
        # Geographic routing logic
        pass
    
    def sync_user_data(self, user_id, source_site, target_site):
        """Sync user preferences across sites"""
        # Cross-site data synchronization
        pass
```

### Data Federation
```python
# Cross-site user preferences sharing
class UserDataFederation:
    def get_user_preferences(self, user_id):
        # Check local cache first
        local_prefs = self.get_local_preferences(user_id)
        
        # Sync from other sites if needed
        if self.needs_sync(user_id):
            remote_prefs = self.fetch_remote_preferences(user_id)
            merged_prefs = self.merge_preferences(local_prefs, remote_prefs)
            self.cache_preferences(user_id, merged_prefs)
            return merged_prefs
        
        return local_prefs
```

---

## API Design

### Core Endpoints
```python
# Job Management
POST /api/v1/jobs                    # Submit new job for processing
GET  /api/v1/jobs/{job_id}          # Get job details
GET  /api/v1/jobs/search            # Search jobs with filters

# User Management  
POST /api/v1/users                   # Create user account
GET  /api/v1/users/{user_id}        # Get user profile
PUT  /api/v1/users/{user_id}/cv     # Update CV data
PUT  /api/v1/users/{user_id}/prefs  # Update preferences

# Matching Engine
POST /api/v1/match                   # Get job matches for user
GET  /api/v1/match/{user_id}/recent # Get recent matches
POST /api/v1/feedback               # Submit user feedback

# Applications
POST /api/v1/applications           # Submit job application
GET  /api/v1/applications/{user_id} # Get user's applications
PUT  /api/v1/applications/{app_id}  # Update application status
```

### Example API Response
```json
{
  "matches": [
    {
      "job_id": "uuid",
      "company": "Deutsche Bank", 
      "title": "Senior Python Developer",
      "overall_score": 0.87,
      "recommendation": "EXCELLENT",
      "bucket_scores": {
        "technical_skills": 0.92,
        "domain_expertise": 0.78,
        "methodology_frameworks": 0.85,
        "collaboration_communication": 0.90,
        "experience_qualifications": 0.80
      },
      "key_matches": [
        {"skill": "Python", "cv_skill": "Python Development", "score": 1.0},
        {"skill": "AWS", "cv_skill": "Cloud Computing", "score": 0.8}
      ],
      "missing_skills": [
        {"skill": "Docker", "criticality": "MEDIUM", "impact": "Minor gap"}
      ]
    }
  ],
  "metadata": {
    "total_jobs_analyzed": 1247,
    "processing_time_ms": 450,
    "cache_hit_rate": 0.78
  }
}
```

---

## Deployment Architecture

### Infrastructure Stack
```yaml
# docker-compose.yml for single-site deployment
version: '3.8'
services:
  # Core application
  ty-app:
    build: ./app
    environment:
      - DATABASE_URL=postgresql://ty:pass@postgres:5432/ty_db
      - REDIS_URL=redis://redis:6379
    depends_on: [postgres, redis]
  
  # Database services
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ty_db
      POSTGRES_USER: ty
      POSTGRES_PASSWORD: pass
    volumes:
      - pg_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  # AI services (local LLMs)
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Scaling Strategy
```python
# Horizontal scaling by site
SCALING_STRATEGY = {
    'database': 'PostgreSQL read replicas per region',
    'cache': 'Redis cluster with consistent hashing', 
    'ai_processing': 'Local LLM instances per site',
    'web_tier': 'Load-balanced application servers',
    'cdn': 'Regional edge caching for static assets'
}
```

---

## Performance Targets

### Response Time Goals
- **Job matching**: < 2 seconds for 1000 jobs
- **Skill extraction**: < 30 seconds per job
- **User preference updates**: < 100ms
- **API responses**: < 500ms (95th percentile)

### Throughput Targets
- **Job processing**: 10,000 jobs/day per site
- **User matching**: 100,000 matches/day per site
- **Concurrent users**: 1,000 active users per site
- **Database**: 10,000 queries/second sustained

### Storage Estimates
```python
STORAGE_ESTIMATES = {
    'job_content': '1KB average per job',
    'extracted_skills': '2KB average per job', 
    'user_cv': '5KB average per user',
    'match_history': '100 bytes per match',
    'feedback_data': '200 bytes per feedback',
    
    # Annual projections (100K jobs, 10K users)
    'total_storage': '~2GB per year per site',
    'database_size': '~500MB working set',
    'cache_size': '~100MB hot data'
}
```

---

## Security & Privacy

### Data Protection
```python
SECURITY_MEASURES = {
    'encryption': {
        'at_rest': 'AES-256 for PII data',
        'in_transit': 'TLS 1.3 for all connections',
        'application': 'bcrypt for passwords'
    },
    
    'access_control': {
        'authentication': 'JWT tokens with refresh',
        'authorization': 'RBAC with site-level permissions',
        'api_security': 'Rate limiting + API keys'
    },
    
    'privacy': {
        'data_retention': '7 years application history',
        'user_deletion': 'Hard delete on request',
        'anonymization': 'Remove PII from analytics'
    }
}
```

### GDPR Compliance
- **Right to access**: API endpoint for user data export
- **Right to rectification**: User profile management interface
- **Right to erasure**: Complete data deletion workflow
- **Data portability**: JSON export of all user data
- **Consent management**: Granular privacy controls

---

## Monitoring & Analytics

### Key Metrics
```python
MONITORING_DASHBOARD = {
    'business_metrics': [
        'Daily active users',
        'Job applications submitted', 
        'Match quality scores',
        'User satisfaction ratings'
    ],
    
    'technical_metrics': [
        'API response times',
        'Database query performance',
        'AI processing latency',
        'Cache hit rates'
    ],
    
    'quality_metrics': [
        'Skill extraction accuracy',
        'False positive/negative rates',
        'User feedback trends',
        'Application success rates'
    ]
}
```

### Alerting System
```python
ALERTS = {
    'critical': [
        'Site downtime > 30 seconds',
        'Database connection failures',
        'AI service unavailable'
    ],
    
    'warning': [
        'Response time > 2 seconds',
        'Match quality score < 0.5 average',
        'High user feedback negativity'
    ],
    
    'info': [
        'Daily processing summary',
        'New user registrations',
        'Feature usage statistics'
    ]
}
```

---

## Development Roadmap

### Phase 1: MVP (Months 1-3)
- [ ] Core database schema implementation
- [ ] Basic skill extraction pipeline
- [ ] Simple bucket-to-bucket matching
- [ ] User registration and CV upload
- [ ] Single-site deployment

### Phase 2: Enhancement (Months 4-6)
- [ ] Advanced matching algorithms
- [ ] User feedback integration
- [ ] Cover letter generation
- [ ] Application tracking
- [ ] Performance optimization

### Phase 3: Scale (Months 7-12) 
- [ ] Multi-site architecture
- [ ] Machine learning improvements
- [ ] Advanced analytics dashboard
- [ ] Enterprise customer features
- [ ] Mobile application

### Future Enhancements
- [ ] AI-powered interview preparation
- [ ] Salary negotiation guidance  
- [ ] Career path recommendations
- [ ] Skills gap analysis
- [ ] Industry trend predictions

---

## Conclusion

This architecture provides a scalable, federated platform for career management powered by local AI. The system emphasizes user privacy, feedback-driven improvement, and cost-effective scaling from gaming hardware to enterprise deployment.

**Key innovations:**
- Local AI outperforming cloud solutions
- 5D skill extraction framework
- Multi-site user preference federation
- Feedback-driven matching improvement
- Gaming laptop to enterprise scalability

**Next steps:**
1. Database schema implementation
2. Core matching algorithm development
3. User interface design
4. Initial deployment testing
5. User feedback collection and iteration

---

*Architecture designed by Zara, Queen of Strategic Extraction*  
*"Enterprise-grade AI on gaming hardware"*