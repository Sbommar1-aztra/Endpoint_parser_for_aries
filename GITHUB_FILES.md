# Files Required for Swagger Import Feature

This document lists all files needed to upload to GitHub for the Swagger/OpenAPI import feature.

## ✅ Essential Backend Files (REQUIRED)

These files are **required** for the feature to work:

1. **`swagger_parser.py`** - Core parser service for Swagger 2.0 and OpenAPI 3.0
2. **`swagger_import_controller.py`** - FastAPI router with import endpoints
3. **`models.py`** - SQLAlchemy database models for API requirements
4. **`database.py`** - Database connection and session management
5. **`main.py`** - Main FastAPI application (must include the router)

## ✅ Essential Configuration Files (REQUIRED)

6. **`requirements_swagger.txt`** - Python dependencies for the feature
   - OR update your main `requirements.txt` to include:
     ```
     PyYAML>=6.0
     requests>=2.32.0
     sqlalchemy>=2.0.0
     ```

## ✅ Documentation Files (RECOMMENDED)

7. **`SWAGGER_IMPORT_README.md`** - Complete feature documentation
8. **`ANGULAR_SETUP.md`** - Frontend setup guide (if using Angular)

## ✅ Frontend Files (OPTIONAL - if using Angular)

If you're using the Angular component:

9. **`swagger-import.component.ts`** - Angular TypeScript component
10. **`swagger-import.component.html`** - Angular HTML template
11. **`swagger-import.component.css`** - Angular styles

## 📝 Example/Test Files (OPTIONAL but helpful)

12. **`sample_swagger.yaml`** - Sample Swagger file for testing
13. **`test_swagger_import.py`** - Test script for the feature

## ❌ Files to EXCLUDE (DO NOT UPLOAD)

- `*.db` or `*.sqlite` - Database files
- `__pycache__/` - Python cache directories
- `*.pyc` - Compiled Python files
- `venv/` or `env/` - Virtual environments
- `node_modules/` - Node.js dependencies
- `.env` - Environment variables with secrets
- `*.xlsx`, `*.xls` - Excel files (unless needed)
- Any files with API keys or credentials

## 📋 Quick Checklist

Before uploading to GitHub, ensure you have:

- [ ] `swagger_parser.py`
- [ ] `swagger_import_controller.py`
- [ ] `models.py`
- [ ] `database.py`
- [ ] `main.py` (updated with router)
- [ ] `requirements_swagger.txt` or updated `requirements.txt`
- [ ] `SWAGGER_IMPORT_README.md`
- [ ] `.gitignore` file (see below)

## 🔧 Integration Steps for Others

1. **Install dependencies:**
   ```bash
   pip install -r requirements_swagger.txt
   ```

2. **Update `main.py`** to include:
   ```python
   from database import init_db
   from swagger_import_controller import router as swagger_import_router
   
   app.include_router(swagger_import_router)
   init_db()
   ```

3. **Configure database** in `database.py`:
   ```python
   DATABASE_URL = "sqlite:///./api_requirements.db"  # or your DB URL
   ```

4. **Start server:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Test the feature:**
   - Visit `http://localhost:8000/docs`
   - Find `/api/swagger-import/parse-file` endpoint
   - Upload a Swagger file to test

## 📦 Minimal File Set

If you want to share only the core feature (minimum files):

1. `swagger_parser.py`
2. `swagger_import_controller.py`
3. `models.py`
4. `database.py`
5. `requirements_swagger.txt`
6. `SWAGGER_IMPORT_README.md`

Plus instructions on how to integrate into `main.py`.
