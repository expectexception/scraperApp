# Scraper Manager API Documentation

## Base URL
```
/api/scrapers/
```

## Authentication
Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Health Check
**GET** `/api/scrapers/health/`

Check if the scraper service is running.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "scrapers_available": 7,
  "total_jobs": 150,
  "total_urls": 1200
}
```

---

### 2. List Available Scrapers
**GET** `/api/scrapers/list/`

Get a list of all available scrapers with their configurations.

**Authentication:** Not required

**Response:**
```json
{
  "scrapers": [
    {
      "name": "signature",
      "display_name": "Signature Aviation",
      "description": "Aviation job board scraper",
      "enabled": true,
      "base_url": "https://signature.com/careers",
      "max_jobs": 100,
      "max_pages": 10
    }
  ]
}
```

---

### 3. Start Scraper
**POST** `/api/scrapers/start/`

Start a single scraper job.

**Authentication:** Required

**Request Body:**
```json
{
  "scraper_name": "signature",
  "max_jobs": 50,
  "max_pages": 5
}
```

**Response:**
```json
{
  "job_id": 123,
  "scraper_name": "signature",
  "status": "pending",
  "message": "Scraper job started"
}
```

---

### 4. Start All Scrapers
**POST** `/api/scrapers/start-all/`

Start all enabled scrapers.

**Authentication:** Required

**Request Body:**
```json
{
  "max_jobs": 50,
  "max_pages": 5
}
```

**Response:**
```json
{
  "job_id": 124,
  "message": "All scrapers started",
  "status": "pending"
}
```

---

### 5. Get Job Status
**GET** `/api/scrapers/status/<job_id>/`

Get the status of a specific scraper job.

**Authentication:** Required

**Response:**
```json
{
  "job_id": 123,
  "scraper_name": "signature",
  "status": "completed",
  "started_at": "2025-11-25T10:30:00Z",
  "completed_at": "2025-11-25T10:32:15Z",
  "execution_time": 135.2,
  "jobs_found": 50,
  "jobs_new": 10,
  "jobs_updated": 35,
  "jobs_duplicate": 5,
  "error_message": null,
  "output_file": "signature_jobs_20251125_103000.json"
}
```

---

### 6. Cancel Job
**DELETE** `/api/scrapers/cancel/<job_id>/`

Cancel a running scraper job.

**Authentication:** Required

**Response:**
```json
{
  "message": "Job cancelled successfully",
  "job_id": 123,
  "status": "cancelled"
}
```

---

### 7. Get Active Jobs
**GET** `/api/scrapers/active/`

Get list of currently running jobs.

**Authentication:** Required

**Response:**
```json
{
  "active_jobs": [
    {
      "id": 123,
      "scraper_name": "signature",
      "status": "running",
      "started_at": "2025-11-25T10:30:00Z",
      "parameters": {"max_jobs": 50},
      "triggered_by": "admin"
    }
  ],
  "count": 1
}
```

---

### 8. Get Statistics
**GET** `/api/scrapers/stats/`

Get overall scraper statistics.

**Authentication:** Required

**Response:**
```json
{
  "total_runs": 150,
  "completed_runs": 140,
  "failed_runs": 10,
  "success_rate": 93.3,
  "total_jobs_scraped": 1200,
  "jobs_by_source": {
    "signature": 300,
    "flygosh": 250,
    "aap": 200
  },
  "avg_execution_time": 145.5,
  "recent_jobs": [...]
}
```

---

### 9. Get History
**GET** `/api/scrapers/history/`

Get scraper execution history.

**Authentication:** Required

**Query Parameters:**
- `scraper` (optional): Filter by scraper name
- `limit` (optional): Number of results (default: 20)

**Example:**
```
GET /api/scrapers/history/?scraper=signature&limit=10
```

**Response:**
```json
{
  "jobs": [
    {
      "id": 123,
      "scraper_name": "signature",
      "status": "completed",
      "started_at": "2025-11-25T10:30:00Z",
      "completed_at": "2025-11-25T10:32:15Z",
      "execution_time": 135.2,
      "jobs_found": 50,
      "jobs_new": 10,
      "jobs_updated": 35,
      "jobs_duplicate": 5,
      "triggered_by": "admin"
    }
  ]
}
```

---

### 10. Get Recent Jobs
**GET** `/api/scrapers/recent-jobs/`

Get recently scraped jobs.

**Authentication:** Required

**Query Parameters:**
- `source` (optional): Filter by source
- `limit` (optional): Number of results (default: 50)

**Example:**
```
GET /api/scrapers/recent-jobs/?source=signature&limit=20
```

**Response:**
```json
{
  "jobs": [
    {
      "id": 1,
      "job_id": "12345",
      "url": "https://example.com/job/12345",
      "source": "signature",
      "title": "Aircraft Mechanic",
      "company": "Signature Aviation",
      "scrape_count": 3,
      "first_scraped": "2025-11-20T10:00:00Z",
      "last_scraped": "2025-11-25T10:30:00Z"
    }
  ],
  "count": 20
}
```

---

### 11. Get Scraper Config
**GET** `/api/scrapers/config/<scraper_name>/`

Get configuration for a specific scraper.

**Authentication:** Required

**Example:**
```
GET /api/scrapers/config/signature/
```

**Response:**
```json
{
  "name": "signature",
  "display_name": "Signature Aviation",
  "description": "Aviation job board scraper",
  "enabled": true,
  "base_url": "https://signature.com/careers",
  "max_jobs": 100,
  "max_pages": 10,
  "schedule": "0 */6 * * *",
  "last_run": "2025-11-25T10:30:00Z",
  "total_runs": 50,
  "successful_runs": 48,
  "failed_runs": 2,
  "total_jobs_found": 1500
}
```

---

### 12. Update Scraper Config
**PUT/PATCH** `/api/scrapers/config/<scraper_name>/update/`

Update configuration for a specific scraper.

**Authentication:** Required

**Request Body:**
```json
{
  "enabled": true,
  "max_jobs": 150,
  "max_pages": 15,
  "schedule": "0 */4 * * *"
}
```

**Response:**
```json
{
  "message": "Configuration updated successfully",
  "scraper_name": "signature",
  "enabled": true,
  "max_jobs": 150,
  "max_pages": 15,
  "schedule": "0 */4 * * *"
}
```

---

## Status Codes

- `200 OK` - Request successful
- `202 Accepted` - Job started (async operation)
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service unhealthy

---

## Job Status Values

- `pending` - Job created, waiting to start
- `running` - Job currently executing
- `completed` - Job finished successfully
- `failed` - Job failed with error
- `cancelled` - Job cancelled by user

---

## Frontend Integration Examples

### React/Axios Example

```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/scrapers/';

// Get all scrapers
const getScrapers = async () => {
  const response = await axios.get(`${API_BASE}list/`);
  return response.data.scrapers;
};

// Start a scraper
const startScraper = async (scraperName, token) => {
  const response = await axios.post(
    `${API_BASE}start/`,
    { scraper_name: scraperName, max_jobs: 50 },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};

// Check job status
const checkStatus = async (jobId, token) => {
  const response = await axios.get(
    `${API_BASE}status/${jobId}/`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};

// Get statistics
const getStats = async (token) => {
  const response = await axios.get(
    `${API_BASE}stats/`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};
```

### Vue Example

```javascript
// In your Vue component or composable
const scraperService = {
  async listScrapers() {
    const res = await fetch('/api/scrapers/list/');
    return await res.json();
  },
  
  async startScraper(scraperName, token) {
    const res = await fetch('/api/scrapers/start/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ scraper_name: scraperName })
    });
    return await res.json();
  },
  
  async getHistory(scraperName, token) {
    const url = scraperName 
      ? `/api/scrapers/history/?scraper=${scraperName}`
      : '/api/scrapers/history/';
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return await res.json();
  }
};
```

---

## WebSocket Support (Future Enhancement)

For real-time updates, consider implementing WebSocket connections for:
- Live job progress updates
- Real-time status changes
- Scraper completion notifications

---

## Rate Limiting

Recommended rate limits:
- `/start/` endpoint: 10 requests per minute per user
- Other endpoints: 100 requests per minute per user

---

## Error Handling

All error responses follow this format:
```json
{
  "error": "Error message description"
}
```

---

## Notes

1. Jobs run asynchronously - use the status endpoint to check progress
2. Large scraping operations may take several minutes
3. Configure scraper limits to avoid overloading target sites
4. Monitor the health endpoint for service availability
