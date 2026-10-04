import * as cdk from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { KiekkokeskusStack } from '../lib/kiekkokeskus-stack';

function synth(): Template {
  const app = new cdk.App();
  const stack = new KiekkokeskusStack(app, 'TestStack', {
    env: { account: '490004610151', region: 'us-east-1' },
  });
  return Template.fromStack(stack);
}

describe('KiekkokeskusStack', () => {
  const t = synth();

  test('we own nothing that belongs to the main site', () => {
    t.resourceCountIs('AWS::S3::Bucket', 0);
    t.resourceCountIs('AWS::CloudFront::Distribution', 0);
    t.resourceCountIs('AWS::S3::BucketPolicy', 0);
  });

  test('schedule is in America/New_York with flexible window OFF', () => {
    t.hasResourceProperties('AWS::Scheduler::Schedule', {
      ScheduleExpressionTimezone: 'America/New_York',
      FlexibleTimeWindow: { Mode: 'OFF' },
      ScheduleExpression: 'cron(0 10 * * ? *)',
    });
  });

  test('lambda is python 3.13 on arm64', () => {
    t.hasResourceProperties('AWS::Lambda::Function', Match.objectLike({
      Runtime: 'python3.13',
      Architectures: ['arm64'],
      FunctionName: 'kiekkokeskus-collector',
    }));
  });

  test('async retries are disabled (ADR-032)', () => {
    t.hasResourceProperties('AWS::Lambda::EventInvokeConfig', {
      MaximumRetryAttempts: 0,
    });
  });

  test('log group has 14-day retention', () => {
    t.hasResourceProperties('AWS::Logs::LogGroup', {
      LogGroupName: '/aws/lambda/kiekkokeskus-collector',
      RetentionInDays: 14,
    });
  });

  test('SNS email subscription to greggjuri@gmail.com', () => {
    t.hasResourceProperties('AWS::SNS::Subscription', Match.objectLike({
      Protocol: 'email',
      Endpoint: 'greggjuri@gmail.com',
    }));
  });

  test('errors alarm on AWS/Lambda Errors', () => {
    t.hasResourceProperties('AWS::CloudWatch::Alarm', Match.objectLike({
      MetricName: 'Errors',
      Namespace: 'AWS/Lambda',
      Threshold: 1,
    }));
  });

  test('collector role has s3:PutObject scoped to data/kiekkokeskus/*, nothing else', () => {
    t.hasResourceProperties('AWS::IAM::Policy', Match.objectLike({
      PolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: 's3:PutObject',
            Effect: 'Allow',
            Resource: 'arn:aws:s3:::jurigregg-static-site/data/kiekkokeskus/*',
          }),
        ]),
      }),
    }));
  });
});
