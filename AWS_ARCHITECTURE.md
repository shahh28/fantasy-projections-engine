# AWS Architecture for Fantasy Sports Prediction API

## Overview

This document describes the AWS serverless architecture for the Fantasy Sports Prediction API, which transforms the original local Python script into a scalable, cloud-based solution.

## Architecture Components

### 1. AWS Lambda Functions

#### Data Scraper Function (`data_scraper.py`)
- **Purpose**: Scrapes NFL fantasy stats from Pro Football Reference
- **Triggers**: 
  - API Gateway POST request (`/scrape-data`)
  - EventBridge scheduled event (daily at 6 AM UTC)
- **Features**:
  - Multi-year data scraping
  - Error handling and retry logic
  - Data validation and cleaning
  - S3 storage with organized folder structure

#### Model Trainer Function (`model_trainer.py`)
- **Purpose**: Trains machine learning models using historical data
- **Triggers**: API Gateway POST request (`/train-model`)
- **Features**:
  - Random Forest model training
  - Feature engineering and data preparation
  - Model evaluation and metrics
  - Model serialization and S3 storage
  - Metadata tracking

#### Predictor Function (`predictor.py`)
- **Purpose**: Makes predictions using trained models
- **Triggers**: API Gateway GET requests
  - `/predictions` - Get top predictions
  - `/predictions/{player}` - Get specific player prediction
- **Features**:
  - Model loading from S3
  - Real-time predictions
  - Position-specific filtering
  - Confidence scoring

#### Analyzer Function (`analyzer.py`)
- **Purpose**: Provides data analysis and insights
- **Triggers**: API Gateway GET request (`/analysis`)
- **Features**:
  - Statistical analysis of predictions
  - Historical trend analysis
  - Insight generation
  - Multiple analysis types

#### Health Check Function (`health_check.py`)
- **Purpose**: API health monitoring
- **Triggers**: API Gateway GET request (`/health`)
- **Features**:
  - Environment variable validation
  - Lambda function status
  - Resource monitoring

### 2. Amazon S3 Storage

#### Data Bucket (`fantasy-sports-data-{account-id}-{env}`)
```
fantasy-sports-data-{account-id}-{env}/
├── raw_data/
│   └── fantasy_stats_YYYYMMDD_HHMMSS.json
├── current_year/
│   └── fantasy_stats_YYYY.json
├── predictions/
│   └── fantasy_predictions_YYYY.json
└── summaries/
    └── scrape_summary_YYYYMMDD_HHMMSS.json
```

#### Model Bucket (`fantasy-sports-models-{account-id}-{env}`)
```
fantasy-sports-models-{account-id}-{env}/
├── models/
│   └── fantasy_predictor_YYYYMMDD_HHMMSS.joblib
├── metadata/
│   └── model_metadata_YYYYMMDD_HHMMSS.json
└── latest_model.json
```

### 3. API Gateway

#### REST API Endpoints
- `POST /scrape-data` - Trigger data scraping
- `POST /train-model` - Train ML model
- `GET /predictions` - Get predictions (with query params)
- `GET /predictions/{player}` - Get specific player prediction
- `GET /analysis` - Get analysis (with query params)
- `GET /health` - Health check

#### Features
- CORS enabled for web access
- Request/response validation
- Rate limiting
- CloudWatch integration
- HTTPS enforcement

### 4. EventBridge (CloudWatch Events)

#### Scheduled Events
- **Daily Data Scrape**: Runs at 6 AM UTC daily
- **Purpose**: Keep data fresh and up-to-date
- **Target**: Data Scraper Lambda function

## Data Flow

### 1. Data Ingestion Flow
```
EventBridge → Data Scraper Lambda → S3 Data Bucket
     ↓
API Gateway → Data Scraper Lambda → S3 Data Bucket
```

### 2. Model Training Flow
```
API Gateway → Model Trainer Lambda → S3 Data Bucket (read)
     ↓
Model Trainer Lambda → S3 Model Bucket (write)
```

### 3. Prediction Flow
```
API Gateway → Predictor Lambda → S3 Model Bucket (read)
     ↓
Predictor Lambda → S3 Data Bucket (read)
     ↓
Predictor Lambda → API Response
```

### 4. Analysis Flow
```
API Gateway → Analyzer Lambda → S3 Data Bucket (read)
     ↓
Analyzer Lambda → S3 Model Bucket (read)
     ↓
Analyzer Lambda → API Response
```

## Security Architecture

### 1. IAM Roles and Policies
- **Lambda Execution Role**: Minimal permissions for S3 access
- **S3 Bucket Policies**: Private access, no public read/write
- **API Gateway**: HTTPS only, no API key required (can be added)

### 2. Data Protection
- **Encryption**: S3 server-side encryption (SSE-S3)
- **Access Control**: IAM-based access control
- **Network Security**: VPC isolation (optional)

### 3. Monitoring and Logging
- **CloudWatch Logs**: All Lambda function logs
- **CloudWatch Metrics**: API Gateway and Lambda metrics
- **CloudTrail**: API calls and AWS service usage

## Scalability Features

### 1. Auto-scaling
- **Lambda**: Automatic scaling based on request volume
- **API Gateway**: Handles concurrent requests
- **S3**: Unlimited storage and bandwidth

### 2. Performance Optimization
- **Lambda Memory**: 1024MB allocation for ML workloads
- **Timeout**: 5-minute timeout for long-running operations
- **Caching**: S3 caching for frequently accessed data

### 3. Cost Optimization
- **Pay-per-use**: Only pay for actual usage
- **S3 Lifecycle**: Automatic deletion of old data
- **Lambda Optimization**: Efficient memory allocation

## Deployment Architecture

### 1. Infrastructure as Code
- **AWS SAM**: Serverless Application Model
- **CloudFormation**: Automated resource provisioning
- **Version Control**: Git-based deployment

### 2. Environment Management
- **Dev/Prod**: Separate environments
- **Parameter Store**: Environment-specific configuration
- **Rollback**: Easy rollback to previous versions

### 3. CI/CD Pipeline
```
Code Commit → Build → Test → Deploy → Monitor
```

## Monitoring and Observability

### 1. Application Monitoring
- **Health Checks**: Regular API health monitoring
- **Error Tracking**: Lambda error logs and metrics
- **Performance**: Response time and throughput metrics

### 2. Business Metrics
- **Data Quality**: Scraping success rates
- **Model Performance**: Prediction accuracy metrics
- **API Usage**: Endpoint usage statistics

### 3. Alerting
- **CloudWatch Alarms**: Error rate and latency alerts
- **SNS Notifications**: Critical failure notifications
- **Dashboard**: Real-time monitoring dashboard

## Cost Analysis

### 1. Lambda Costs
- **Data Scraper**: ~$0.10 per 1000 requests
- **Model Trainer**: ~$0.50 per training run
- **Predictor**: ~$0.05 per 1000 predictions
- **Analyzer**: ~$0.05 per 1000 analysis requests

### 2. S3 Costs
- **Storage**: ~$0.023 per GB per month
- **Requests**: ~$0.0004 per 1000 requests
- **Data Transfer**: Free within same region

### 3. API Gateway Costs
- **Requests**: ~$3.50 per million requests
- **Data Transfer**: ~$0.09 per GB

### 4. Estimated Monthly Cost
- **Low Usage** (< 1000 requests/day): ~$5-10/month
- **Medium Usage** (1000-10000 requests/day): ~$20-50/month
- **High Usage** (> 10000 requests/day): ~$100+/month

## Benefits of AWS Architecture

### 1. Scalability
- **Automatic Scaling**: Handles traffic spikes
- **Global Reach**: Multi-region deployment possible
- **Unlimited Resources**: No infrastructure limits

### 2. Reliability
- **High Availability**: 99.9%+ uptime
- **Fault Tolerance**: Automatic failover
- **Data Durability**: S3 99.999999999% durability

### 3. Cost Efficiency
- **Pay-per-use**: No idle resource costs
- **Optimization**: Automatic resource optimization
- **Reserved Capacity**: Discounts for predictable usage

### 4. Security
- **Enterprise Security**: AWS security best practices
- **Compliance**: SOC, PCI, HIPAA compliance
- **Encryption**: End-to-end encryption

### 5. Developer Experience
- **Serverless**: No server management
- **Managed Services**: AWS handles infrastructure
- **Easy Deployment**: One-command deployment

## Migration from Local Script

### 1. Code Changes
- **Modular Design**: Split into Lambda functions
- **Error Handling**: Enhanced error handling
- **Logging**: Structured logging for monitoring
- **Configuration**: Environment-based configuration

### 2. Data Management
- **S3 Storage**: Replace local file storage
- **Data Pipeline**: Automated data ingestion
- **Versioning**: S3 versioning for data history

### 3. API Interface
- **REST API**: Replace command-line interface
- **Web Interface**: User-friendly web UI
- **Documentation**: OpenAPI/Swagger documentation

## Future Enhancements

### 1. Advanced Features
- **Real-time Updates**: WebSocket connections
- **User Authentication**: Cognito integration
- **Advanced Analytics**: QuickSight dashboards
- **Mobile App**: React Native application

### 2. Machine Learning
- **Model Versioning**: SageMaker integration
- **A/B Testing**: Model comparison
- **AutoML**: Automated model selection
- **Feature Store**: Centralized feature management

### 3. Infrastructure
- **CDN**: CloudFront for global distribution
- **Database**: DynamoDB for user data
- **Caching**: ElastiCache for performance
- **Load Balancing**: Application Load Balancer

This AWS architecture transforms the original local script into a production-ready, scalable, and maintainable system that can handle real-world usage patterns while providing excellent developer and user experiences. 