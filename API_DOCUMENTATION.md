# DocuManage API Documentation

Complete reference for the DocuManage REST API.

## Base URL

```
Development: http://localhost:5000/api
Production: https://your-domain.com/api
```

## Authentication

Most endpoints require authentication via JWT Bearer token.

### Getting a Token

```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@documanage.com",
  "password": "admin123"
}
```

Response:
```json
{
  "success": true,
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer"
  },
  "user": {
    "id": 1,
    "email": "admin@documanage.com",
    "role": "admin"
  }
}
```

### Using the Token

Include the token in the Authorization header:

```http
GET /users/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## Response Format

All API responses follow this format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error information"
}
```

---

## Endpoints

### Authentication

#### Register
```http
POST /auth/register
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "password": "password123",
  "role": "editor",
  "department": "IT"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "password123"
}
```

#### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer <access_token>
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>
```

#### Change Password (Admin only)
```http
POST /auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

---

### Users (Admin only)

#### List Users
```http
GET /users/?page=1&per_page=20&role=editor&search=john
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "role": "editor",
      "is_active": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 100
  }
}
```

#### Get User
```http
GET /users/1
Authorization: Bearer <access_token>
```

#### Update User
```http
PUT /users/1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890"
}
```

#### Delete User
```http
DELETE /users/1
Authorization: Bearer <access_token>
```

#### Reset User Password
```http
POST /users/1/reset-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "new_password": "newpassword123"
}
```

#### User Statistics
```http
GET /users/stats
Authorization: Bearer <access_token>
```

---

### Files

#### List Files
```http
GET /files/?page=1&per_page=20&type=pdf&search=report
Authorization: Bearer <access_token>
```

#### Get File Details
```http
GET /files/1
Authorization: Bearer <access_token>
```

#### Upload File
```http
POST /files/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <binary_file_data>
description: "Annual report 2024"
tags: "finance,annual,report"
```

Response:
```json
{
  "success": true,
  "file": {
    "id": 1,
    "name": "report.pdf",
    "size": "2.5 MB",
    "type": "pdf",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

#### Download File
```http
GET /files/1/download
Authorization: Bearer <access_token>
```

Returns: Binary file data with appropriate headers

#### Delete File
```http
DELETE /files/1
Authorization: Bearer <access_token>
```

#### Share File
```http
POST /files/1/share
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_ids": [2, 3],
  "message": "Please review this document"
}
```

#### Unshare File
```http
POST /files/1/unshare
Authorization: Bearer <access_token>
```

#### File Statistics
```http
GET /files/stats
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "stats": {
    "total_files": 128,
    "by_type": {
      "pdf": 45,
      "doc": 30,
      "img": 35,
      "xls": 18
    },
    "total_size_formatted": "2.5 GB"
  }
}
```

---

### Audit Log

#### Get Audit Logs
```http
GET /audit/?page=1&per_page=50&user_id=1&action=file_upload&days=7
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "action": "file_upload",
      "description": "Uploaded file: report.pdf",
      "user": {
        "id": 1,
        "name": "John Doe"
      },
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### Get Activity Statistics
```http
GET /audit/stats?days=30
Authorization: Bearer <access_token>
```

#### Get My Activity
```http
GET /audit/my-activity?limit=50
Authorization: Bearer <access_token>
```

---

### Notifications

#### Get Notifications
```http
GET /notifications/notifications?limit=20&include_read=true
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "notifications": [
    {
      "id": 1,
      "title": "File Shared",
      "message": "John shared a file with you",
      "type": "share",
      "is_read": false,
      "created_at": "2024-01-15T10:30:00",
      "time_ago": "2 minutes ago"
    }
  ],
  "unread_count": 5
}
```

#### Mark Notification Read
```http
POST /notifications/notifications/1/read
Authorization: Bearer <access_token>
```

#### Mark All Notifications Read
```http
POST /notifications/notifications/read-all
Authorization: Bearer <access_token>
```

#### Get Unread Count
```http
GET /notifications/notifications/unread-count
Authorization: Bearer <access_token>
```

---

### Messages

#### Get Messages
```http
GET /notifications/messages?box=inbox&limit=20
Authorization: Bearer <access_token>
```

#### Send Message
```http
POST /notifications/messages
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "recipient_id": 2,
  "subject": "Review Request",
  "content": "Can you please review the attached document?"
}
```

#### Get Message
```http
GET /notifications/messages/1
Authorization: Bearer <access_token>
```

#### Mark Message Read
```http
POST /notifications/messages/1/read
Authorization: Bearer <access_token>
```

#### Mark All Messages Read
```http
POST /notifications/messages/read-all
Authorization: Bearer <access_token>
```

---

### Dashboard

#### Get Dashboard Data
```http
GET /dashboard/
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "data": {
    "user": { ... },
    "stats": {
      "files": {
        "total_files": 128,
        "by_type": { ... },
        "total_size_formatted": "2.5 GB"
      },
      "unread_notifications": 5,
      "unread_messages": 2
    },
    "recent_files": [ ... ],
    "recent_activities": [ ... ],
    "admin_stats": { ... }  // Admin only
  }
}
```

#### Get Dashboard Statistics
```http
GET /dashboard/stats
Authorization: Bearer <access_token>
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

---

## Rate Limiting

API requests are rate-limited:
- 200 requests per day
- 50 requests per hour

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 49
X-RateLimit-Reset: 1640995200
```

---

## File Upload Limits

- Maximum file size: 100MB (development) / 50MB (production)
- Allowed types: pdf, doc, docx, xls, xlsx, ppt, pptx, jpg, jpeg, png, gif, txt, csv, zip, rar

---

## Pagination

List endpoints support pagination with these query parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| page | 1 | Page number |
| per_page | 20 | Items per page (max 100) |

Response includes pagination info:
```json
{
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Filtering & Search

Many endpoints support filtering:

```http
# Filter by role
GET /users/?role=admin

# Search by name/email
GET /users/?search=john

# Filter by file type
GET /files/?type=pdf

# Filter by date range
GET /audit/?days=7
```

---

## WebSocket Support (Future)

Real-time updates will be available via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New notification:', data);
};
```
