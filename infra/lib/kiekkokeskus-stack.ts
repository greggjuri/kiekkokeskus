import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subs from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cwActions from 'aws-cdk-lib/aws-cloudwatch-actions';

const BUCKET_NAME = 'jurigregg-static-site';
const PREFIX = 'data/kiekkokeskus/';
const ALERT_EMAIL = 'greggjuri@gmail.com';
const LOG_GROUP_NAME = '/aws/lambda/kiekkokeskus-collector';

export class KiekkokeskusStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Imported, never owned (ADR-020, ADR-026)
    const siteBucket = s3.Bucket.fromBucketName(this, 'SiteBucket', BUCKET_NAME);

    // Explicit log group retention (ADR-032) with RETAIN so logs survive stack teardown
    const logGroup = new logs.LogGroup(this, 'LogGroup', {
      logGroupName: LOG_GROUP_NAME,
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const collectorRole = new iam.Role(this, 'CollectorRole', {
      roleName: 'kiekkokeskus-collector-role',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });
    // Exact scope: PutObject on data/kiekkokeskus/* only (CLAUDE.md Rule 1)
    collectorRole.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:PutObject'],
      resources: [`arn:aws:s3:::${BUCKET_NAME}/${PREFIX}*`],
    }));

    const collector = new lambda.Function(this, 'Collector', {
      functionName: 'kiekkokeskus-collector',
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'kiekkokeskus.handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'src'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo'],
      }),
      timeout: cdk.Duration.minutes(3),
      memorySize: 256,
      role: collectorRole,
      logGroup,
      environment: {
        BUCKET: BUCKET_NAME,
        PREFIX,
      },
    });

    // ADR-032: collector owns its own retries; disable Lambda's async retry multiplication
    new lambda.CfnEventInvokeConfig(this, 'CollectorInvokeConfig', {
      functionName: collector.functionName,
      qualifier: '$LATEST',
      maximumRetryAttempts: 0,
    });

    // Scheduler L1 (ADR-005). L2 is still alpha at CDK 2.272; CfnSchedule is well-trodden.
    const schedulerRole = new iam.Role(this, 'SchedulerRole', {
      roleName: 'kiekkokeskus-scheduler-role',
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });
    collector.grantInvoke(schedulerRole);
    new scheduler.CfnSchedule(this, 'DailySchedule', {
      name: 'kiekkokeskus-daily',
      flexibleTimeWindow: { mode: 'OFF' },
      scheduleExpression: 'cron(0 10 * * ? *)',
      scheduleExpressionTimezone: 'America/New_York',
      target: {
        arn: collector.functionArn,
        roleArn: schedulerRole.roleArn,
        input: '{"source":"scheduled"}',
      },
    });

    const alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: 'kiekkokeskus-alerts',
    });
    alertTopic.addSubscription(new subs.EmailSubscription(ALERT_EMAIL));

    const errorsAlarm = new cloudwatch.Alarm(this, 'CollectorErrorsAlarm', {
      alarmName: 'kiekkokeskus-collector-errors',
      metric: collector.metricErrors({ period: cdk.Duration.minutes(5), statistic: 'Sum' }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    errorsAlarm.addAlarmAction(new cwActions.SnsAction(alertTopic));

    // Missed-run alarm (ADR-032): fires when the schedule stops firing or the Lambda
    // stops being invoked. Invocations metric is only emitted when > 0, so we treat
    // missing data as breaching and evaluate over a 24h window.
    const missedAlarm = new cloudwatch.Alarm(this, 'CollectorMissedAlarm', {
      alarmName: 'kiekkokeskus-collector-missed',
      metric: collector.metricInvocations({ period: cdk.Duration.hours(24), statistic: 'Sum' }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    });
    missedAlarm.addAlarmAction(new cwActions.SnsAction(alertTopic));

    // Suppress "unused" warnings for the imported bucket; it's intentionally not referenced
    // further — IAM is scoped by ARN above, not by passing the Bucket construct around.
    void siteBucket;

    cdk.Tags.of(this).add('project', 'kiekkokeskus');
  }
}
