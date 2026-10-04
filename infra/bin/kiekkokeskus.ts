#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { KiekkokeskusStack } from '../lib/kiekkokeskus-stack';

const app = new cdk.App();

new KiekkokeskusStack(app, 'KiekkokeskusStack', {
  env: { account: '490004610151', region: 'us-east-1' },
  tags: { project: 'kiekkokeskus' },
});
