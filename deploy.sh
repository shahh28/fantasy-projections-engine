#!/bin/bash

# Fantasy Sports Prediction API Deployment Script

set -e

echo "🚀 Starting Fantasy Sports Prediction API deployment..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is running (for local testing)
if ! docker info &> /dev/null; then
    echo "⚠️  Docker is not running. Local testing may not work."
fi

# Build the application
echo "📦 Building application..."
sam build

# Deploy the application
echo "🚀 Deploying to AWS..."
sam deploy --guided

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Note the API Gateway URL from the deployment output"
echo "2. Test the health endpoint: curl <api-url>/health"
echo "3. Scrape data: curl -X POST <api-url>/scrape-data"
echo "4. Train model: curl -X POST <api-url>/train-model"
echo "5. Get predictions: curl <api-url>/predictions"
echo ""
echo "📚 See README.md for detailed usage instructions" 