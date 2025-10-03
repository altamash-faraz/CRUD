"""
Professional CRUD Web Application with MongoDB
Features: Advanced search, analytics, audit logging, data validation, bulk operations
Author: Showcasing Database & Python Skills
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration - hardcoded to avoid environment issues
MONGO_URI = 'mongodb://localhost:27017'
DATABASE_NAME = 'professional_crud_db'
ITEMS_PER_PAGE = 10

print(f"🔗 Connecting to: {MONGO_URI}")
print(f"📊 Database: {DATABASE_NAME}")

# MongoDB Connection with error handling
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client[DATABASE_NAME]
    
    # Collections
    products_collection = db.products
    categories_collection = db.categories
    audit_collection = db.audit_logs
    analytics_collection = db.analytics
    
    # Create indexes for performance
    products_collection.create_index([("name", "text"), ("description", "text"), ("tags", "text")])
    products_collection.create_index([("category_id", ASCENDING)])
    products_collection.create_index([("created_at", DESCENDING)])
    products_collection.create_index([("price", ASCENDING)])
    
    audit_collection.create_index([("timestamp", DESCENDING)])
    audit_collection.create_index([("action", ASCENDING)])
    
    print("✅ Connected to MongoDB successfully")
    mongo_connected = True
    
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongo_connected = False

# Enums for better data validation
class ProductStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"

class AuditAction(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"

# Data validation schemas
@dataclass
class ProductSchema:
    name: str
    description: str
    category_id: str
    price: float
    quantity: int
    tags: List[str]
    status: str = ProductStatus.ACTIVE.value
    
    def validate(self) -> Dict[str, Any]:
        errors = {}
        
        if not self.name or len(self.name.strip()) < 2:
            errors['name'] = 'Name must be at least 2 characters long'
            
        if not self.description or len(self.description.strip()) < 10:
            errors['description'] = 'Description must be at least 10 characters long'
            
        if self.price <= 0:
            errors['price'] = 'Price must be greater than 0'
            
        if self.quantity < 0:
            errors['quantity'] = 'Quantity cannot be negative'
            
        if self.status not in [status.value for status in ProductStatus]:
            errors['status'] = 'Invalid status'
            
        return errors

def log_audit(action: AuditAction, resource_type: str, resource_id: str = None, 
              details: Dict = None, user_ip: str = None):
    """Log all database operations for audit trail"""
    if not mongo_connected:
        return
        
    try:
        audit_log = {
            "timestamp": datetime.now(timezone.utc),
            "action": action.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "user_ip": user_ip or request.remote_addr,
            "user_agent": request.headers.get('User-Agent', '')
        }
        audit_collection.insert_one(audit_log)
    except Exception as e:
        print(f"Audit logging failed: {e}")

def update_analytics(action: str, data: Dict = None):
    """Update analytics data for dashboard"""
    if not mongo_connected:
        return
        
    try:
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")  # Use string instead of date object
        analytics_collection.update_one(
            {"date": today_str, "action": action},
            {
                "$inc": {"count": 1},
                "$set": {"last_updated": now},
                "$push": {"data": data} if data else {}
            },
            upsert=True
        )
    except Exception as e:
        print(f"Analytics update failed: {e}")

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error", "status": 500}), 500

# Routes
@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "mongodb_connected": mongo_connected,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# Category Management
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories with product counts"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        # Aggregation pipeline to get categories with product counts
        pipeline = [
            {
                "$lookup": {
                    "from": "products",
                    "localField": "_id",
                    "foreignField": "category_id",
                    "as": "products"
                }
            },
            {
                "$addFields": {
                    "product_count": {"$size": "$products"}
                }
            },
            {
                "$project": {
                    "products": 0
                }
            },
            {
                "$sort": {"name": 1}
            }
        ]
        
        categories = list(categories_collection.aggregate(pipeline))
        for category in categories:
            category['_id'] = str(category['_id'])
            
        log_audit(AuditAction.READ, "categories")
        return jsonify(categories)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create a new category"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('name') or len(data['name'].strip()) < 2:
            return jsonify({"error": "Category name must be at least 2 characters"}), 400
            
        # Check if category already exists
        existing = categories_collection.find_one({"name": {"$regex": f"^{data['name']}$", "$options": "i"}})
        if existing:
            return jsonify({"error": "Category already exists"}), 409
        
        now = datetime.now(timezone.utc)
        category = {
            "name": data['name'].strip(),
            "description": data.get('description', '').strip(),
            "color": data.get('color', '#007bff'),
            "icon": data.get('icon', 'fas fa-box'),
            "created_at": now,
            "updated_at": now
        }
        
        result = categories_collection.insert_one(category)
        category['_id'] = str(result.inserted_id)
        
        log_audit(AuditAction.CREATE, "category", str(result.inserted_id), category)
        update_analytics("category_created")
        
        return jsonify(category), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Product Management
@app.route('/api/products', methods=['GET'])
def get_products():
    """Get products with advanced filtering, searching, and pagination"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        # Query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', ITEMS_PER_PAGE))
        search = request.args.get('search', '').strip()
        category_id = request.args.get('category_id', '')
        status = request.args.get('status', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        price_min = request.args.get('price_min', type=float)
        price_max = request.args.get('price_max', type=float)
        
        # Build query
        query = {}
        
        # Search in name, description, and tags
        if search:
            query["$text"] = {"$search": search}
        
        # Filter by category
        if category_id:
            try:
                query["category_id"] = ObjectId(category_id)
            except:
                pass
        
        # Filter by status
        if status:
            query["status"] = status
            
        # Price range filter
        if price_min is not None or price_max is not None:
            price_query = {}
            if price_min is not None:
                price_query["$gte"] = price_min
            if price_max is not None:
                price_query["$lte"] = price_max
            query["price"] = price_query
        
        # Sorting
        sort_direction = DESCENDING if sort_order == 'desc' else ASCENDING
        sort_field = [(sort_by, sort_direction)]
        
        # Execute query with pagination
        skip = (page - 1) * limit
        products = list(products_collection.find(query).sort(sort_field).skip(skip).limit(limit))
        total_count = products_collection.count_documents(query)
        
        # Convert ObjectId to string and add category information
        for product in products:
            product['_id'] = str(product['_id'])
            product['category_id'] = str(product['category_id'])
            
            # Get category info
            category = categories_collection.find_one({"_id": ObjectId(product['category_id'])})
            if category:
                product['category'] = {
                    "_id": str(category['_id']),
                    "name": category['name'],
                    "color": category.get('color', '#007bff'),
                    "icon": category.get('icon', 'fas fa-box')
                }
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        log_audit(AuditAction.READ, "products", details={"query": query, "count": len(products)})
        
        return jsonify({
            "products": products,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "filters": {
                "search": search,
                "category_id": category_id,
                "status": status,
                "price_min": price_min,
                "price_max": price_max
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    """Create a new product with validation"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'category_id', 'price', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create and validate product schema
        product_data = ProductSchema(
            name=data['name'],
            description=data['description'],
            category_id=data['category_id'],
            price=float(data['price']),
            quantity=int(data['quantity']),
            tags=data.get('tags', []),
            status=data.get('status', ProductStatus.ACTIVE.value)
        )
        
        validation_errors = product_data.validate()
        if validation_errors:
            print(f"Product validation errors: {validation_errors}")
            return jsonify({"error": "Validation failed", "details": validation_errors}), 400
        
        # Verify category exists
        try:
            category_obj_id = ObjectId(data['category_id'])
            category = categories_collection.find_one({"_id": category_obj_id})
            if not category:
                return jsonify({"error": "Category not found"}), 404
        except:
            return jsonify({"error": "Invalid category ID"}), 400
        
        # Create product document
        now = datetime.now(timezone.utc)
        product = {
            "name": product_data.name.strip(),
            "description": product_data.description.strip(),
            "category_id": category_obj_id,
            "price": product_data.price,
            "quantity": product_data.quantity,
            "tags": [tag.strip() for tag in product_data.tags if tag.strip()],
            "status": product_data.status,
            "created_at": now,
            "updated_at": now,
            "views": 0,
            "last_viewed": None
        }
        
        result = products_collection.insert_one(product)
        product['_id'] = str(result.inserted_id)
        product['category_id'] = str(product['category_id'])
        
        # Add category info to response
        product['category'] = {
            "_id": str(category['_id']),
            "name": category['name'],
            "color": category.get('color', '#007bff'),
            "icon": category.get('icon', 'fas fa-box')
        }
        
        log_audit(AuditAction.CREATE, "product", str(result.inserted_id), product)
        update_analytics("product_created", {"category": category['name'], "price": product_data.price})
        
        return jsonify(product), 201
        
    except ValueError as e:
        print(f"Product creation ValueError: {e}")
        return jsonify({"error": f"Invalid data type: {str(e)}"}), 400
    except Exception as e:
        print(f"Product creation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by ID"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Update view count
        products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"views": 1}, "$set": {"last_viewed": datetime.now(timezone.utc)}}
        )
        
        product['_id'] = str(product['_id'])
        product['category_id'] = str(product['category_id'])
        
        # Get category info
        category = categories_collection.find_one({"_id": ObjectId(product['category_id'])})
        if category:
            product['category'] = {
                "_id": str(category['_id']),
                "name": category['name'],
                "color": category.get('color', '#007bff'),
                "icon": category.get('icon', 'fas fa-box')
            }
        
        log_audit(AuditAction.READ, "product", product_id)
        return jsonify(product)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """Update a product"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        data = request.get_json()
        
        # Check if product exists
        existing_product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not existing_product:
            return jsonify({"error": "Product not found"}), 404
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        
        # Update only provided fields
        if 'name' in data:
            if not data['name'] or len(data['name'].strip()) < 2:
                return jsonify({"error": "Name must be at least 2 characters"}), 400
            update_data['name'] = data['name'].strip()
        
        if 'description' in data:
            if not data['description'] or len(data['description'].strip()) < 10:
                return jsonify({"error": "Description must be at least 10 characters"}), 400
            update_data['description'] = data['description'].strip()
        
        if 'category_id' in data:
            try:
                category_obj_id = ObjectId(data['category_id'])
                category = categories_collection.find_one({"_id": category_obj_id})
                if not category:
                    return jsonify({"error": "Category not found"}), 404
                update_data['category_id'] = category_obj_id
            except:
                return jsonify({"error": "Invalid category ID"}), 400
        
        if 'price' in data:
            try:
                price = float(data['price'])
                if price <= 0:
                    return jsonify({"error": "Price must be greater than 0"}), 400
                update_data['price'] = price
            except ValueError:
                return jsonify({"error": "Invalid price format"}), 400
        
        if 'quantity' in data:
            try:
                quantity = int(data['quantity'])
                if quantity < 0:
                    return jsonify({"error": "Quantity cannot be negative"}), 400
                update_data['quantity'] = quantity
            except ValueError:
                return jsonify({"error": "Invalid quantity format"}), 400
        
        if 'tags' in data:
            update_data['tags'] = [tag.strip() for tag in data['tags'] if tag.strip()]
        
        if 'status' in data:
            if data['status'] not in [status.value for status in ProductStatus]:
                return jsonify({"error": "Invalid status"}), 400
            update_data['status'] = data['status']
        
        # Update product
        products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        
        # Get updated product
        updated_product = products_collection.find_one({"_id": ObjectId(product_id)})
        updated_product['_id'] = str(updated_product['_id'])
        updated_product['category_id'] = str(updated_product['category_id'])
        
        # Add category info
        category = categories_collection.find_one({"_id": ObjectId(updated_product['category_id'])})
        if category:
            updated_product['category'] = {
                "_id": str(category['_id']),
                "name": category['name'],
                "color": category.get('color', '#007bff'),
                "icon": category.get('icon', 'fas fa-box')
            }
        
        log_audit(AuditAction.UPDATE, "product", product_id, update_data)
        update_analytics("product_updated")
        
        return jsonify(updated_product)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        # Check if product exists
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Delete product
        products_collection.delete_one({"_id": ObjectId(product_id)})
        
        log_audit(AuditAction.DELETE, "product", product_id, {"name": product.get('name')})
        update_analytics("product_deleted")
        
        return jsonify({"message": "Product deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Bulk Operations
@app.route('/api/products/bulk', methods=['POST'])
def bulk_create_products():
    """Bulk create products"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        data = request.get_json()
        products_data = data.get('products', [])
        
        if not products_data:
            return jsonify({"error": "No products provided"}), 400
        
        if len(products_data) > 100:
            return jsonify({"error": "Maximum 100 products allowed per bulk operation"}), 400
        
        valid_products = []
        errors = []
        
        for i, product_data in enumerate(products_data):
            try:
                # Validate product
                product_schema = ProductSchema(
                    name=product_data['name'],
                    description=product_data['description'],
                    category_id=product_data['category_id'],
                    price=float(product_data['price']),
                    quantity=int(product_data['quantity']),
                    tags=product_data.get('tags', []),
                    status=product_data.get('status', ProductStatus.ACTIVE.value)
                )
                
                validation_errors = product_schema.validate()
                if validation_errors:
                    errors.append({"index": i, "errors": validation_errors})
                    continue
                
                # Verify category exists
                category_obj_id = ObjectId(product_data['category_id'])
                category = categories_collection.find_one({"_id": category_obj_id})
                if not category:
                    errors.append({"index": i, "errors": {"category_id": "Category not found"}})
                    continue
                
                now = datetime.now(timezone.utc)
                product = {
                    "name": product_schema.name.strip(),
                    "description": product_schema.description.strip(),
                    "category_id": category_obj_id,
                    "price": product_schema.price,
                    "quantity": product_schema.quantity,
                    "tags": [tag.strip() for tag in product_schema.tags if tag.strip()],
                    "status": product_schema.status,
                    "created_at": now,
                    "updated_at": now,
                    "views": 0,
                    "last_viewed": None
                }
                
                valid_products.append(product)
                
            except Exception as e:
                errors.append({"index": i, "errors": {"general": str(e)}})
        
        # Insert valid products
        inserted_count = 0
        if valid_products:
            result = products_collection.insert_many(valid_products)
            inserted_count = len(result.inserted_ids)
        
        log_audit(AuditAction.BULK_CREATE, "products", details={
            "total_attempted": len(products_data),
            "successful": inserted_count,
            "errors": len(errors)
        })
        update_analytics("bulk_products_created", {"count": inserted_count})
        
        return jsonify({
            "message": f"Bulk operation completed",
            "successful": inserted_count,
            "errors": errors,
            "total_attempted": len(products_data)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Analytics Dashboard
@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get analytics data for dashboard"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        # Product statistics
        total_products = products_collection.count_documents({})
        active_products = products_collection.count_documents({"status": "active"})
        total_categories = categories_collection.count_documents({})
        
        # Products by category
        category_pipeline = [
            {
                "$group": {
                    "_id": "$category_id",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": {"$multiply": ["$price", "$quantity"]}}
                }
            },
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "category"
                }
            },
            {
                "$unwind": "$category"
            },
            {
                "$project": {
                    "category_name": "$category.name",
                    "count": 1,
                    "total_value": 1
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        products_by_category = list(products_collection.aggregate(category_pipeline))
        
        # Convert ObjectIds to strings for JSON serialization
        for item in products_by_category:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        
        # Recent activity (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_products = products_collection.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })
        
        # Top viewed products
        top_viewed = list(products_collection.find(
            {"views": {"$gt": 0}},
            {"name": 1, "views": 1, "price": 1}
        ).sort("views", -1).limit(5))
        
        for product in top_viewed:
            product['_id'] = str(product['_id'])
        
        # Price statistics
        price_stats = list(products_collection.aggregate([
            {
                "$group": {
                    "_id": None,
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "total_inventory_value": {"$sum": {"$multiply": ["$price", "$quantity"]}}
                }
            }
        ]))
        
        price_data = price_stats[0] if price_stats else {}
        
        # Status distribution
        status_pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        status_distribution = list(products_collection.aggregate(status_pipeline))
        
        # Convert ObjectIds to strings in status distribution
        for item in status_distribution:
            if '_id' in item and item['_id'] is not None:
                item['_id'] = str(item['_id']) if hasattr(item['_id'], '__str__') else item['_id']
        
        log_audit(AuditAction.READ, "analytics")
        
        return jsonify({
            "summary": {
                "total_products": total_products,
                "active_products": active_products,
                "total_categories": total_categories,
                "recent_products": recent_products,
                "avg_price": round(price_data.get('avg_price', 0), 2),
                "total_inventory_value": round(price_data.get('total_inventory_value', 0), 2)
            },
            "charts": {
                "products_by_category": products_by_category,
                "status_distribution": status_distribution,
                "top_viewed_products": top_viewed
            },
            "price_stats": {
                "average": round(price_data.get('avg_price', 0), 2),
                "minimum": price_data.get('min_price', 0),
                "maximum": price_data.get('max_price', 0)
            }
        })
        
    except Exception as e:
        print(f"Analytics dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Data Export
@app.route('/api/export/products', methods=['GET'])
def export_products():
    """Export products data"""
    if not mongo_connected:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        format_type = request.args.get('format', 'json')
        
        # Get all products with category info
        pipeline = [
            {
                "$lookup": {
                    "from": "categories",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category"
                }
            },
            {
                "$unwind": "$category"
            },
            {
                "$project": {
                    "name": 1,
                    "description": 1,
                    "category_name": "$category.name",
                    "price": 1,
                    "quantity": 1,
                    "status": 1,
                    "tags": 1,
                    "created_at": 1,
                    "views": 1
                }
            }
        ]
        
        products = list(products_collection.aggregate(pipeline))
        
        for product in products:
            product['_id'] = str(product['_id'])
            product['created_at'] = product['created_at'].isoformat()
        
        log_audit(AuditAction.READ, "export", details={"format": format_type, "count": len(products)})
        
        if format_type == 'csv':
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            if products:
                fieldnames = products[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(products)
            
            now = datetime.now(timezone.utc)
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=products_{now.strftime("%Y%m%d_%H%M%S")}.csv'
            }
        
        return jsonify({
            "data": products,
            "count": len(products),
            "exported_at": now.isoformat(),
            "format": format_type
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Professional CRUD Application...")
    print(f"📊 Database: {DATABASE_NAME}")
    print(f"🔗 MongoDB: {'Connected' if mongo_connected else 'Disconnected'}")
    app.run(debug=False, host='0.0.0.0', port=5000)