# SuomiSF API Documentation

This directory contains comprehensive API documentation for the SuomiSF (Finnish Science Fiction Bibliography) project. The documentation has been automatically generated from the Flask route definitions in the `app/api_*.py` files.

## 📁 Documentation Files

### 1. `api_documentation.html`
**Interactive HTML Documentation**
- Beautiful, responsive web interface
- Statistics and overview of the API
- Links to all documentation formats
- Sample endpoint previews
- Open this file in your browser for the best viewing experience

### 2. `API_DOCUMENTATION.md`
**Complete Manual Documentation**
- Comprehensive Markdown documentation
- Detailed endpoint descriptions
- Request/response examples
- Authentication information
- Error handling guidelines
- Human-readable and well-structured

### 3. `API_ROUTES_GENERATED.md`
**Auto-Generated Route Documentation**
- Machine-generated from source code analysis
- Contains all 122 discovered API endpoints
- Organized by functional categories
- Includes function names and docstrings where available
- Automatically updated when routes change

### 4. `openapi.yaml`
**OpenAPI 3.0 Specification**
- Machine-readable API specification
- Compatible with Swagger UI, Postman, and other API tools
- Includes schema definitions for common data types
- Can be used to generate client libraries
- Industry-standard format for API documentation

### 5. `api_routes_summary.json`
**JSON Route Inventory**
- Complete machine-readable route listing
- Statistics and categorization
- Useful for programmatic access to API metadata
- Contains all discovered routes with methods and file locations

### 6. `generate_api_docs.py`
**Documentation Generator Script**
- Python script that analyzes the Flask application
- Extracts route definitions from `api_*.py` files
- Generates the auto-generated documentation files
- Can be re-run to update documentation when code changes

## 🚀 Getting Started

### For Developers
1. **Start with** `api_documentation.html` - Open in your browser for an overview
2. **Refer to** `API_DOCUMENTATION.md` - For detailed implementation guidance
3. **Use** `openapi.yaml` - Import into Swagger UI or Postman for testing

### For API Consumers
1. **Read** `API_DOCUMENTATION.md` - Complete API reference
2. **Import** `openapi.yaml` - Into your favorite API client
3. **Browse** `api_documentation.html` - For a visual overview

### For System Integrators
1. **Use** `api_routes_summary.json` - For programmatic route discovery
2. **Reference** `openapi.yaml` - For automated client generation
3. **Check** `API_ROUTES_GENERATED.md` - For the most up-to-date route list

## 📊 API Statistics

- **Total Endpoints**: 122
- **API Files**: 22
- **Categories**: 38
- **Authentication**: JWT-based
- **Base URL**: `http://www.sf-bibliografia.fi/api`

## 🔄 Regenerating Documentation

To update the documentation when the API changes:

```bash
cd /path/to/suomisf
python3 generate_api_docs.py
```

This will:
- Scan all `app/api_*.py` files
- Extract route definitions and docstrings
- Update `API_ROUTES_GENERATED.md`
- Update `api_routes_summary.json`

## 📝 Main API Categories

The API is organized into the following main categories:

- **Authentication** (`/api/login`, `/api/register`, `/api/refresh`)
- **Works** (`/api/works/*`) - Books, novels, collections
- **People** (`/api/people/*`) - Authors, editors, translators
- **Editions** (`/api/editions/*`) - Book editions and publications
- **Short Stories** (`/api/shorts/*`) - Short fiction
- **Articles** (`/api/articles/*`) - Non-fiction articles
- **Awards** (`/api/awards/*`) - Literary awards and nominations
- **Publishers** (`/api/publishers/*`) - Publishing companies
- **Magazines** (`/api/magazines/*`) - Periodical publications
- **Issues** (`/api/issues/*`) - Magazine issues
- **Tags** (`/api/tags/*`) - Classification tags
- **Search** (`/api/search*`) - Search functionality
- **Latest** (`/api/latest/*`) - Recently added content
- **Filters** (`/api/filter/*`) - Data filtering endpoints

## 🔐 Authentication

Most write operations require JWT authentication:

1. Login with `/api/login` to get tokens
2. Include `Authorization: Bearer <token>` header in subsequent requests
3. Refresh tokens using `/api/refresh` when needed

## 🌐 Response Format

All API responses follow this structure:

```json
{
  "response": <data>,
  "status": <http_status_code>
}
```

## 📄 License

This documentation is part of the SuomiSF project. Please refer to the main project license for usage terms.

---

*Last updated: July 1, 2025*
*Generated from Flask application route analysis*
