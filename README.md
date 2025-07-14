# Fantasy Sports Prediction API with AWS

A serverless fantasy sports prediction system built with AWS Lambda, S3, and API Gateway. This project scrapes NFL fantasy football data, trains machine learning models, and provides predictions for the upcoming season.

## Architecture

- **AWS Lambda**: Serverless functions for data scraping, model training, predictions, and analysis
- **Amazon S3**: Data storage for raw fantasy stats, trained models, and predictions
- **API Gateway**: RESTful API endpoints for accessing predictions and analysis
- **EventBridge**: Scheduled data scraping (daily at 6 AM UTC)

## Features

- **Data Scraping**: Automated scraping of NFL fantasy stats from Pro Football Reference
- **ML Model Training**: Random Forest model for predicting next-year fantasy performance
- **Predictions API**: Get predictions for all players or specific players
- **Data Analysis**: Comprehensive analysis of predictions and historical trends
- **Scheduled Updates**: Daily data scraping and model retraining
- **Health Monitoring**: API health check endpoint

## Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.9+
- Docker (for local testing)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fantasy-sports
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS credentials**:
   ```bash
   aws configure
   ```

## Deployment

1. **Build the application**:
   ```bash
   sam build
   ```

2. **Deploy to AWS**:
   ```bash
   sam deploy --guided
   ```

3. **Note the API Gateway URL** from the deployment output.

## API Endpoints

### Data Management

- `POST /scrape-data` - Scrape fantasy sports data
  ```json
  {
    "years": [2024, 2023, 2022, 2021, 2020]
  }
  ```

- `POST /train-model` - Train prediction model
  ```json
  {
    "data_source": "latest"
  }
  ```

### Predictions

- `GET /predictions` - Get top predictions
  - Query params: `top_n` (default: 50), `position` (QB/RB/WR/TE)

- `GET /predictions/{player}` - Get prediction for specific player

### Analysis

- `GET /analysis` - Get comprehensive analysis
  - Query params: `type` (all/predictions/historical/insights)

### Health Check

- `GET /health` - API health status

## Usage Examples

### 1. Scrape Data
```bash
curl -X POST https://your-api-gateway-url/Prod/scrape-data \
  -H "Content-Type: application/json" \
  -d '{"years": [2024, 2023, 2022]}'
```

### 2. Train Model
```bash
curl -X POST https://your-api-gateway-url/Prod/train-model \
  -H "Content-Type: application/json" \
  -d '{"data_source": "latest"}'
```

### 3. Get Predictions
```bash
# Get top 25 predictions
curl "https://your-api-gateway-url/Prod/predictions?top_n=25"

# Get predictions for QBs only
curl "https://your-api-gateway-url/Prod/predictions?position=QB"

# Get prediction for specific player
curl "https://your-api-gateway-url/Prod/predictions/Patrick%20Mahomes"
```

### 4. Get Analysis
```bash
# Get all analysis
curl "https://your-api-gateway-url/Prod/analysis"

# Get only insights
curl "https://your-api-gateway-url/Prod/analysis?type=insights"
```

## Local Development

1. **Start local API**:
   ```bash
   sam local start-api
   ```

2. **Test endpoints locally**:
   ```bash
   curl http://localhost:3000/health
   ```

## S3 Bucket Structure

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

fantasy-sports-models-{account-id}-{env}/
├── models/
│   └── fantasy_predictor_YYYYMMDD_HHMMSS.joblib
├── metadata/
│   └── model_metadata_YYYYMMDD_HHMMSS.json
└── latest_model.json
```

## Model Features

The prediction model uses the following features:
- Current year fantasy points
- Position (QB/RB/WR/TE)
- Estimated age and experience
- Position-specific age factors
- Team consistency
- Historical performance trends

## Monitoring and Logs

- **CloudWatch Logs**: Each Lambda function logs to CloudWatch
- **CloudWatch Metrics**: API Gateway and Lambda metrics
- **Health Check**: Monitor API health via `/health` endpoint

## Cost Optimization

- Lambda functions use 1024MB memory and 5-minute timeout
- S3 lifecycle policies delete old data after 1 year
- Scheduled scraping runs once daily
- Model training only when triggered

## Security

- S3 buckets are private with no public access
- API Gateway uses HTTPS
- Lambda functions have minimal IAM permissions
- CORS headers configured for web access

## Troubleshooting

### Common Issues

1. **Model not found**: Ensure model training has been completed
2. **Data not found**: Check if data scraping has been run
3. **Timeout errors**: Increase Lambda timeout in template.yaml
4. **Memory errors**: Increase Lambda memory allocation

### Debugging

1. **Check CloudWatch Logs** for each Lambda function
2. **Verify S3 bucket contents** using AWS Console
3. **Test health endpoint** to verify API connectivity
4. **Check IAM permissions** for Lambda functions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open an issue on GitHub 