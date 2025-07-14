@echo off
echo Deploying Fantasy Sports Predictor...
sam deploy --stack-name fantasy-sports-predictor --region us-east-1 --capabilities CAPABILITY_IAM --confirm-changeset --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-tnalpue67ga7
pause 