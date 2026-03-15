#!/bin/bash

# Phase 2.1 JOIN API Test Script

BASE_URL="http://localhost:8000/api/v1"
PROJECT_ID=5

echo "=== Phase 2.1 JOIN API Test ==="
echo ""

# Step 1: Login
echo "Step 1: Login..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser2","password":"test12345"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi
echo "✅ Login successful"
echo ""

# Step 2: Get relationships
echo "Step 2: Get relationships for Product..."
RELATIONSHIPS=$(curl -s -X GET "$BASE_URL/query/$PROJECT_ID/relationships/Product" \
  -H "Authorization: Bearer $TOKEN")

echo "$RELATIONSHIPS" | python3 -m json.tool
echo ""

# Step 3: Query with JOIN
echo "Step 3: Execute JOIN query..."
QUERY_RESULT=$(curl -s -X POST "$BASE_URL/query/$PROJECT_ID/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Product",
    "selected_columns": ["Product.sku_id", "Product.product_name", "GoodsMallMapping.platform_name"],
    "joins": [
      {
        "relationship_name": "product_to_platform_mapping",
        "join_type": "LEFT"
      }
    ],
    "limit": 5
  }')

echo "$QUERY_RESULT" | python3 -m json.tool
echo ""

# Check if query was successful
SUCCESS=$(echo "$QUERY_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")

if [ "$SUCCESS" = "True" ]; then
  echo "✅ JOIN query executed successfully"
else
  echo "❌ JOIN query failed"
fi

echo ""
echo "=== Test Complete ==="
