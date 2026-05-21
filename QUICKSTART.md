# DocuManage Backend - Quick Start Guide

This guide will help you get the DocuManage backend running in PyCharm with MySQL Workbench in under 10 minutes.

## Prerequisites

- Python 3.8 or higher
- PyCharm (Community or Professional)
- MySQL Workbench
- MySQL Server 5.7+ (or use Docker)

---

## Step 1: Import Project into PyCharm

1. Open PyCharm
2. Click **File → Open**
3. Select the `docmgmt-backend` folder
4. Click **OK**
5. Wait for PyCharm to index the project

---

## Step 2: Set Up Virtual Environment

### Option A: Using PyCharm (Recommended)

1. Open **File → Settings → Project → Python Interpreter**
2. Click the gear icon ⚙️ → **Add**
3. Select **Virtualenv Environment** → **New**
4. Choose location: `<project_root>/venv`
5. Click **OK**

### Option B: Using Terminal

```bash
# In PyCharm Terminal (bottom panel)
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

---

## Step 3: Install Dependencies

### Using PyCharm Terminal:

```bash
pip install -r requirements.txt
```

### Or using PyCharm GUI:

1. Right-click on `requirements.txt`
2. Click **Install Requirements**

---

## Step 4: Set Up MySQL Database

### Option A: Using Setup Script

```bash
python setup_database.py
```

Follow the prompts to:
- Enter MySQL root credentials
- Create database and user
- Generate `.env` file

### Option B: Using MySQL Workbench

1. Open MySQL Workbench
2. Connect to your local MySQL server
3. Open a new query tab
4. Execute the following SQL:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS documanage_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS 'documanage_user'@'localhost' 
IDENTIFIED BY 'documanage_pass';

-- Grant privileges
GRANT ALL PRIVILEGES ON documanage_db.* 
TO 'documanage_user'@'localhost';

FLUSH PRIVILEGES;
```

5. Create `.env` file in project root:

```env
FLASK_ENV=development
FLASK_APP=run.py
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=mysql+pymysql://documanage_user:documanage_pass@localhost:3306/documanage_db
MAX_CONTENT_LENGTH=104857600
UPLOAD_FOLDER=uploads
CORS_ORIGINS=*
```

---

## Step 5: Initialize Database

```bash
# Create database tables
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create demo data
flask init-db
```

---

## Step 6: Run the Application

### Using PyCharm Run Configuration (Recommended)

1. Click **Run → Edit Configurations**
2. Click **+** → **Python**
3. Name: `Flask Server`
4. Script path: Select `run.py`
5. Working directory: Project root
6. Click **OK**
7. Click **Run** button (▶️)

### Using Terminal

```bash
python run.py
```

The API will be available at: **http://localhost:5000**

---

## Step 7: Test the API

### Using Browser:

Open: http://localhost:5000/

You should see:
```json
{
  "name": "DocuManage API",
  "version": "1.0.0",
  "status": "running"
}
```

### Using Postman or curl:

```bash
# Health check
curl http://localhost:5000/health

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@documanage.com", "password": "admin123"}'
```

---

## Default Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@documanage.com | admin123 |
| Editor | editor@documanage.com | editor123 |
| Viewer | viewer@documanage.com | viewer123 |

---

## Using Docker (Alternative)

If you prefer Docker over local MySQL:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

Access:
- API: http://localhost:5000
- phpMyAdmin: http://localhost:8080

---

## PyCharm Tips

### Enable Auto-reload

Add to your Run Configuration:
- **Environment variables**: `FLASK_DEBUG=1`

### Database Integration

1. Click **View → Tool Windows → Database**
2. Click **+** → **Data Source** → **MySQL**
3. Enter credentials:
   - Host: `localhost`
   - Port: `3306`
   - User: `documanage_user`
   - Password: `documanage_pass`
   - Database: `documanage_db`
4. Click **Test Connection**
5. Click **OK**

### Code Completion

PyCharm should automatically detect Flask and provide:
- Code completion
- Error highlighting
- Refactoring support

---

## Troubleshooting

### "Module not found" errors

```bash
# Make sure virtual environment is activated
pip install -r requirements.txt
```

### MySQL connection errors

```bash
# Check if MySQL is running
# Windows:
net start mysql

# macOS:
brew services start mysql

# Linux:
sudo systemctl start mysql
```

### Database migration errors

```bash
# Reset migrations
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

---

## Next Steps

1. **Connect Frontend**: Update your frontend API base URL to `http://localhost:5000/api`
2. **Customize**: Modify models, routes, and configuration as needed
3. **Deploy**: Use Docker or Gunicorn for production deployment

---

## Useful Commands

```bash
# Run tests
pytest

# Create admin user
flask create-admin

# View routes
flask routes

# Database shell
flask shell
```

---

## Support

For detailed documentation, see `README.md`
